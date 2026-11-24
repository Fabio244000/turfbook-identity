from datetime import datetime, tzinfo
from uuid import UUID

from app.user_identity.application.exceptions import ProcessNotFoundError
from app.user_identity.application.password_processes import owned_process
from app.user_identity.application.ports.driving.validate_password_update_port import (
    ValidatePasswordUpdatePort,
)
from app.user_identity.application.security_processes import (
    close_if_ended,
    validate_code,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import SecurityProcessType
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class ValidatePasswordUpdateUseCase(ValidatePasswordUpdatePort):
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

    async def execute(self, user_uuid: UUID, process_uuid: UUID, code: str) -> datetime:
        now = self._clock.now()
        zone = self._business_timezone
        async with self._uow:
            # The user first, as when a code is requested, then the process: attempts
            # at once are counted one by one.
            user = await self._uow.users.get_by_uuid_for_update(user_uuid)
            _, process = await owned_process(
                self._uow, user, process_uuid, _TYPE, now, zone
            )
            if await close_if_ended(self._uow, process, now, zone, self._rules):
                await self._uow.commit()
                raise ProcessNotFoundError()
            error = await validate_code(self._uow, process, code, now, self._rules)
            await self._uow.commit()
        if error is not None:
            raise error
        return process.password_deadline(self._rules)


_TYPE = SecurityProcessType.PASSWORD_UPDATE
