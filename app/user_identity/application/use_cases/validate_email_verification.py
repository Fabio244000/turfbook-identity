from datetime import datetime, tzinfo
from uuid import UUID

from app.user_identity.application.exceptions import ProcessNotFoundError
from app.user_identity.application.ports.driving.validate_email_verification_port import (
    ValidateEmailVerificationPort,
)
from app.user_identity.application.security_processes import (
    close_if_ended,
    validate_code,
)
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class ValidateEmailVerificationUseCase(ValidateEmailVerificationPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        rules: SecurityCodeRules,
        business_timezone: tzinfo,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._rules = rules
        self._business_timezone = business_timezone

    async def execute(self, user_uuid: UUID, process_uuid: UUID, code: str) -> None:
        now = self._clock.now()
        async with self._uow:
            user, process = await self._user_and_process(user_uuid, process_uuid, now)
            await self._ensure_not_ended(process, now)
            error = await validate_code(self._uow, process, code, now, self._rules)
            if error is not None:
                await self._uow.commit()
                raise error
            process.complete(now)
            user.verify_email(now)
            await self._uow.security_processes.update(process)
            await self._uow.users.update(user)
            event = AccountEvent.email_verified(user.uuid, process.uuid, now)
            await self._uow.account_events.add(event)
            await self._uow.commit()

    async def _user_and_process(
        self, user_uuid: UUID, process_uuid: UUID, now: datetime
    ) -> tuple[User, SecurityProcess]:
        """The user first, as when a code is requested, then the process: attempts at
        once are counted one by one."""
        user = await self._uow.users.get_by_uuid_for_update(user_uuid)
        process = await self._uow.security_processes.get_by_uuid_for_update(
            process_uuid
        )
        if user is None or process is None or not self._is_open_to(process, user, now):
            raise ProcessNotFoundError()
        return user, process

    def _is_open_to(self, process: SecurityProcess, user: User, now: datetime) -> bool:
        """Only the user's email verification of today: any other is not found, so
        nobody learns that it exists."""
        return (
            process.user_uuid == user.uuid
            and process.type is SecurityProcessType.EMAIL_VERIFICATION
            and process.is_of_day(now, self._business_timezone)
        )

    async def _ensure_not_ended(self, process: SecurityProcess, now: datetime) -> None:
        """A process whose life ended is stored closed and is no longer found."""
        if await close_if_ended(
            self._uow, process, now, self._business_timezone, self._rules
        ):
            await self._uow.commit()
            raise ProcessNotFoundError()
