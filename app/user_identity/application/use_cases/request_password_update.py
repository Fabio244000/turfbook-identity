from datetime import datetime, tzinfo
from functools import partial
from uuid import UUID

from app.user_identity.application.exceptions import (
    ProcessNotAllowedError,
    SecurityCodeNotSentError,
)
from app.user_identity.application.notices import password_code_notice
from app.user_identity.application.password_processes import identified_user
from app.user_identity.application.ports.driving.request_password_update_port import (
    RequestPasswordUpdatePort,
)
from app.user_identity.application.security_processes import (
    apply_rule,
    issue_code,
    publish_code,
    settle_code,
)
from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.minimum_duration_port import (
    MinimumDurationPort,
)
from app.user_identity.domain.ports.driven.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.driven.security_code_generator_port import (
    SecurityCodeGeneratorPort,
)
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class RequestPasswordUpdateUseCase(RequestPasswordUpdatePort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        code_generator: SecurityCodeGeneratorPort,
        notice_publisher: NoticePublisherPort,
        code_rules: SecurityCodeRules,
        password_rules: PasswordProcessRules,
        business_timezone: tzinfo,
        minimum_duration: MinimumDurationPort,
        request_code_min_seconds: float,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._code_generator = code_generator
        self._notice_publisher = notice_publisher
        self._code_rules = code_rules
        self._password_rules = password_rules
        self._business_timezone = business_timezone
        self._minimum_duration = minimum_duration
        self._request_code_min_seconds = request_code_min_seconds

    async def execute(
        self, user_uuid: UUID, cellphone: str, email: str
    ) -> tuple[UUID, datetime]:
        # Every answer takes the same floor: its time reveals no account.
        async with self._minimum_duration.at_least(self._request_code_min_seconds):
            return await self._request(user_uuid, cellphone, email)

    async def _request(
        self, user_uuid: UUID, cellphone: str, email: str
    ) -> tuple[UUID, datetime]:
        now = self._clock.now()
        async with self._uow:
            # Locked until the commit: two requests at once never open two processes
            # nor exceed the codes of one.
            user = await identified_user(self._uow, cellphone, email)
            if user.uuid != user_uuid:
                raise ProcessNotAllowedError()
            process, code = await issue_code(
                self._uow,
                self._code_generator,
                user.uuid,
                _TYPE,
                now,
                self._business_timezone,
                self._code_rules,
                partial(self._start, user.uuid, now),
            )
            await self._uow.commit()
        notice = password_code_notice(user, code, self._code_rules.code_minutes, _TYPE)
        sent = await publish_code(self._notice_publisher, notice)
        async with self._uow:
            await settle_code(self._uow, process.uuid, code.uuid, sent)
            await self._uow.commit()
        if not sent:
            raise SecurityCodeNotSentError()
        return process.uuid, code.expires_at

    async def _start(
        self, user_uuid: UUID, now: datetime, failed_today: bool
    ) -> SecurityProcess:
        last_update_at = await self._uow.security_processes.last_completed_at(
            user_uuid, _TYPE
        )
        return apply_rule(
            partial(
                SecurityProcess.start_password_update,
                user_uuid,
                now,
                failed_today,
                last_update_at,
                self._password_rules,
            )
        )


_TYPE = SecurityProcessType.PASSWORD_UPDATE
