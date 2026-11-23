from datetime import datetime, tzinfo
from uuid import UUID

from app.user_identity.application.exceptions import ProcessNotFoundError
from app.user_identity.application.ports.driving.validate_email_verification_port import (
    ValidateEmailVerificationPort,
)
from app.user_identity.application.security_processes import raise_application_error
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.exceptions import DomainError
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
            # The user first, as when a code is requested, then the process: attempts
            # at once are counted one by one.
            user = await self._uow.users.get_by_uuid_for_update(user_uuid)
            process = await self._uow.security_processes.get_by_uuid_for_update(
                process_uuid
            )
            if (
                user is None
                or process is None
                or not self._is_open_to(process, user.uuid, now)
            ):
                raise ProcessNotFoundError()
            await self._validate(process, code, now)
            process.complete(now)
            user.verify_email(now)
            await self._uow.security_processes.update(process)
            await self._uow.users.update(user)
            event = AccountEvent.email_verified(user.uuid, process.uuid, now)
            await self._uow.account_events.add(event)
            await self._uow.commit()

    def _is_open_to(
        self, process: SecurityProcess, user_uuid: UUID, now: datetime
    ) -> bool:
        """Only the user's email verification of today: any other is not found, so
        nobody learns that it exists."""
        return (
            process.user_uuid == user_uuid
            and process.type is SecurityProcessType.EMAIL_VERIFICATION
            and process.is_of_day(now, self._business_timezone)
        )

    async def _validate(
        self, process: SecurityProcess, code: str, now: datetime
    ) -> None:
        """A rejected attempt is committed before its error, so it counts."""
        try:
            process.validate(code, now, self._rules)
        except DomainError as error:
            await self._uow.security_processes.update(process)
            await self._uow.commit()
            raise_application_error(error)
