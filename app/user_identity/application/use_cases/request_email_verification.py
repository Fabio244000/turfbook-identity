from datetime import datetime, tzinfo
from functools import partial
from uuid import UUID

from app.user_identity.application.exceptions import (
    ProcessNotAllowedError,
    SecurityCodeNotSentError,
)
from app.user_identity.application.notices import email_verification_notice
from app.user_identity.application.ports.driving.request_email_verification_port import (
    RequestEmailVerificationPort,
)
from app.user_identity.application.security_processes import (
    apply_rule,
    issue_code,
    publish_code,
    settle_code,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.driven.security_code_generator_port import (
    SecurityCodeGeneratorPort,
)
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class RequestEmailVerificationUseCase(RequestEmailVerificationPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        code_generator: SecurityCodeGeneratorPort,
        notice_publisher: NoticePublisherPort,
        rules: SecurityCodeRules,
        business_timezone: tzinfo,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._code_generator = code_generator
        self._notice_publisher = notice_publisher
        self._rules = rules
        self._business_timezone = business_timezone

    async def execute(self, user_uuid: UUID) -> tuple[UUID, datetime]:
        now = self._clock.now()
        async with self._uow:
            # Locked until the commit: two requests at once never open two processes
            # nor exceed the codes of one.
            user = await self._user_that_may_verify(user_uuid)
            process, code = await issue_code(
                self._uow,
                self._code_generator,
                user.uuid,
                _TYPE,
                now,
                self._business_timezone,
                self._rules,
                partial(self._start, user.uuid, now),
            )
            await self._uow.commit()
        notice = email_verification_notice(user, code, self._rules.code_minutes)
        sent = await publish_code(self._notice_publisher, notice)
        async with self._uow:
            await settle_code(self._uow, process.uuid, code.uuid, sent)
            await self._uow.commit()
        if not sent:
            raise SecurityCodeNotSentError()
        return process.uuid, code.expires_at

    async def _user_that_may_verify(self, user_uuid: UUID) -> User:
        user = await self._uow.users.get_by_uuid_for_update(user_uuid)
        if user is None:
            raise ProcessNotAllowedError()
        apply_rule(user.ensure_can_verify_email)
        return user

    async def _start(
        self, user_uuid: UUID, now: datetime, failed_today: bool
    ) -> SecurityProcess:
        return apply_rule(
            partial(SecurityProcess.start, user_uuid, _TYPE, now, failed_today)
        )


_TYPE = SecurityProcessType.EMAIL_VERIFICATION
