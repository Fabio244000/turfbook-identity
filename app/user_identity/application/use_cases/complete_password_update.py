from datetime import datetime, tzinfo
from functools import partial
from uuid import UUID

from app.user_identity.application.dtos.inputs import PasswordChange
from app.user_identity.application.password_processes import (
    ended_process_error,
    owned_process,
    rejected_password,
    save_new_password,
)
from app.user_identity.application.ports.driving.complete_password_update_port import (
    CompletePasswordUpdatePort,
)
from app.user_identity.application.security_processes import apply_rule
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.new_password import (
    ensure_new_password_format,
    update_rejection,
)
from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class CompletePasswordUpdateUseCase(CompletePasswordUpdatePort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        hasher: PasswordHasherPort,
        code_rules: SecurityCodeRules,
        password_rules: PasswordProcessRules,
        business_timezone: tzinfo,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._hasher = hasher
        self._code_rules = code_rules
        self._password_rules = password_rules
        self._business_timezone = business_timezone

    async def execute(
        self, user_uuid: UUID, process_uuid: UUID, change: PasswordChange
    ) -> None:
        # A format error is rejected before any query: it does not count.
        apply_rule(partial(ensure_new_password_format, change.new_password))
        now = self._clock.now()
        zone = self._business_timezone
        async with self._uow:
            # The user first, then the process: two changes at once go one by one.
            locked = await self._uow.users.get_by_uuid_for_update(user_uuid)
            user, process = await owned_process(
                self._uow, locked, process_uuid, _TYPE, now, zone
            )
            await self._ensure_may_set(process, now)
            await self._reject_if_broken(user, process, change, now)
            event = AccountEvent.password_updated(user.uuid, process.uuid, now)
            password_hash = self._hasher.hash(change.new_password)
            await save_new_password(self._uow, user, process, password_hash, event)
            await self._uow.commit()

    async def _ensure_may_set(self, process: SecurityProcess, now: datetime) -> None:
        """A process that just ended is stored closed before its error."""
        error = await ended_process_error(
            self._uow, process, now, self._business_timezone, self._code_rules
        )
        if error is not None:
            await self._uow.commit()
            raise error
        apply_rule(process.ensure_may_set_password)

    async def _reject_if_broken(
        self,
        user: User,
        process: SecurityProcess,
        change: PasswordChange,
        now: datetime,
    ) -> None:
        """A business rejection is stored before its error, so it counts."""
        rejection = update_rejection(
            change.new_password,
            change.new_password_confirmation,
            change.current_password,
            self._hasher.verify(change.current_password, user.password),
            self._password_rules.min_difference,
        )
        if rejection is None:
            return
        error = await rejected_password(
            self._uow, process, rejection, now, self._password_rules
        )
        await self._uow.commit()
        raise error


_TYPE = SecurityProcessType.PASSWORD_UPDATE
