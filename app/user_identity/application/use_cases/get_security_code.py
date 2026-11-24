from datetime import datetime, tzinfo
from functools import partial

from app.user_identity.application.dtos.outputs import SupportSecurityCode
from app.user_identity.application.exceptions import (
    NoProcessInProgressError,
    SecurityCodeAlreadyValidatedError,
    SupportProcessValidatedError,
    UserNotFoundError,
)
from app.user_identity.application.ports.driving.get_security_code_port import (
    GetSecurityCodePort,
)
from app.user_identity.application.security_processes import (
    apply_rule,
    open_process,
)
from app.user_identity.domain.entities.account_event import (
    AccountEvent,
    AccountEventType,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityCode,
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.domain.ports.driven.security_code_generator_port import (
    SecurityCodeGeneratorPort,
)
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


class GetSecurityCodeUseCase(GetSecurityCodePort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        code_generator: SecurityCodeGeneratorPort,
        rules: SecurityCodeRules,
        business_timezone: tzinfo,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._code_generator = code_generator
        self._rules = rules
        self._business_timezone = business_timezone

    async def execute(self, cellphone: str, process_type: str) -> SupportSecurityCode:
        now = self._clock.now()
        async with self._uow:
            # Locked until the commit, as when the user requests a code.
            user = await self._uow.users.get_by_cellphone_for_update(cellphone)
            if user is None:
                raise UserNotFoundError()
            process = await open_process(
                self._uow,
                user.uuid,
                SecurityProcessType(process_type),
                now,
                self._business_timezone,
                self._rules,
            )
            if process is None:
                raise NoProcessInProgressError()
            code, event = self._code_for_support(process, now)
            await self._uow.security_processes.update(process)
            await self._uow.account_events.add(event)
            await self._uow.commit()
        return _to_support_security_code(code, event)

    def _code_for_support(
        self, process: SecurityProcess, now: datetime
    ) -> tuple[SecurityCode, AccountEvent]:
        """The code in force, or a new one when the rules allow it; the event records
        which of the two support got."""
        code = process.current_code(now)
        if code is not None:
            shown = AccountEvent.support_code_shown(
                process.user_uuid, process.uuid, now
            )
            return code, shown
        try:
            code = apply_rule(
                partial(
                    process.issue_support_code,
                    self._code_generator.generate(),
                    now,
                    self._rules,
                )
            )
        except SecurityCodeAlreadyValidatedError as error:
            # Support has its own text: the user, not support, sets the password.
            raise SupportProcessValidatedError() from error
        generated = AccountEvent.support_code_generated(
            process.user_uuid, process.uuid, now
        )
        return code, generated


def _to_support_security_code(
    code: SecurityCode, event: AccountEvent
) -> SupportSecurityCode:
    return SupportSecurityCode(
        process_uuid=code.process_uuid,
        code=code.code,
        code_expires_at=code.expires_at,
        generated=event.type is AccountEventType.SUPPORT_CODE_GENERATED,
    )
