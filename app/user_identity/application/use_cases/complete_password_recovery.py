from datetime import datetime, tzinfo
from functools import partial
from uuid import UUID

from app.user_identity.application.password_processes import (
    ended_process_error,
    owned_process,
    rejected_password,
    save_new_password,
)
from app.user_identity.application.ports.driving.complete_password_recovery_port import (
    CompletePasswordRecoveryPort,
)
from app.user_identity.application.security_processes import apply_rule
from app.user_identity.application.sessions import revoke_user_sessions
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.new_password import (
    ensure_new_password_format,
    recovery_rejection,
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


class CompletePasswordRecoveryUseCase(CompletePasswordRecoveryPort):
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
        self, process_uuid: UUID, new_password: str, new_password_confirmation: str
    ) -> None:
        # A format error is rejected before any query: it does not count.
        apply_rule(partial(ensure_new_password_format, new_password))
        now = self._clock.now()
        zone = self._business_timezone
        async with self._uow:
            # The user first, then the process: two changes at once go one by one.
            locked = await self._owner(process_uuid)
            user, process = await owned_process(
                self._uow, locked, process_uuid, _TYPE, now, zone
            )
            await self._ensure_may_set(process, now)
            await self._reject_if_broken(
                user, process, new_password, new_password_confirmation, now
            )
            event = AccountEvent.password_recovered(user.uuid, process.uuid, now)
            password_hash = self._hasher.hash(new_password)
            await save_new_password(self._uow, user, process, password_hash, event)
            await revoke_user_sessions(self._uow, user.uuid, now)
            await self._uow.commit()

    async def _owner(self, process_uuid: UUID) -> User | None:
        """Without a session, the process says whose it is."""
        process = await self._uow.security_processes.get_by_uuid(process_uuid)
        if process is None:
            return None
        return await self._uow.users.get_by_uuid_for_update(process.user_uuid)

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
        new_password: str,
        confirmation: str,
        now: datetime,
    ) -> None:
        """A business rejection is stored before its error, so it counts."""
        rejection = recovery_rejection(
            new_password,
            confirmation,
            self._hasher.verify(new_password, user.password),
        )
        if rejection is None:
            return
        error = await rejected_password(
            self._uow, process, rejection, now, self._password_rules
        )
        await self._uow.commit()
        raise error


_TYPE = SecurityProcessType.PASSWORD_RECOVERY
