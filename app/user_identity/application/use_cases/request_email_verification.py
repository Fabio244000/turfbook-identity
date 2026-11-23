from datetime import datetime, tzinfo
from functools import partial
from uuid import UUID

from app.user_identity.application.exceptions import (
    ProcessNotAllowedError,
    ProcessNotFoundError,
    SecurityCodeNotSentError,
)
from app.user_identity.application.notices import email_verification_notice
from app.user_identity.application.ports.driving.request_email_verification_port import (
    RequestEmailVerificationPort,
)
from app.user_identity.application.security_processes import (
    apply_rule,
    open_process_of_day,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityCode,
    SecurityProcess,
    SecurityProcessType,
    start_of_day,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
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
            process, code = await self._issue_code(user.uuid, now)
            await self._uow.commit()
        await self._send(user, process.uuid, code)
        return process.uuid, code.expires_at

    async def _user_that_may_verify(self, user_uuid: UUID) -> User:
        user = await self._uow.users.get_by_uuid_for_update(user_uuid)
        if user is None:
            raise ProcessNotAllowedError()
        apply_rule(user.ensure_can_verify_email)
        return user

    async def _issue_code(
        self, user_uuid: UUID, now: datetime
    ) -> tuple[SecurityProcess, SecurityCode]:
        """A pending code in the process of the day, or in a new one."""
        process, is_new = await self._process_of_day(user_uuid, now)
        issue = partial(
            process.issue_user_code, self._code_generator.generate(), now, self._rules
        )
        code = apply_rule(issue)
        if is_new:
            await self._uow.security_processes.add(process)
        else:
            await self._uow.security_processes.update(process)
        return process, code

    async def _process_of_day(
        self, user_uuid: UUID, now: datetime
    ) -> tuple[SecurityProcess, bool]:
        """The process of the day, or a new one (says whether it is new)."""
        process = await open_process_of_day(
            self._uow, user_uuid, _TYPE, now, self._business_timezone
        )
        if process is not None:
            return process, False
        failed_today = await self._uow.security_processes.has_failed_since(
            user_uuid, _TYPE, start_of_day(now, self._business_timezone)
        )
        start = partial(SecurityProcess.start, user_uuid, _TYPE, now, failed_today)
        return apply_rule(start), True

    async def _send(self, user: User, process_uuid: UUID, code: SecurityCode) -> None:
        """After the pending code is committed: sent, it becomes the active code; not
        sent, it is deleted, so it never counts (and a new process without codes
        goes with it)."""
        notice = email_verification_notice(user, code, self._rules.code_minutes)
        try:
            await self._notice_publisher.publish(notice)
        except DomainError as error:
            if error.code is not DomainErrorCode.NOTICE_NOT_PUBLISHED:
                raise
            await self._settle(process_uuid, code.uuid, sent=False)
            raise SecurityCodeNotSentError() from error
        await self._settle(process_uuid, code.uuid, sent=True)

    async def _settle(self, process_uuid: UUID, code_uuid: UUID, sent: bool) -> None:
        async with self._uow:
            repository = self._uow.security_processes
            process = await repository.get_by_uuid_for_update(process_uuid)
            if process is None:
                raise ProcessNotFoundError()
            if sent:
                process.activate_code(code_uuid)
            else:
                process.discard_code(code_uuid)
            if process.has_codes:
                await repository.update(process)
            else:
                await repository.delete(process.uuid)
            await self._uow.commit()


_TYPE = SecurityProcessType.EMAIL_VERIFICATION
