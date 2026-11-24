"""The accounts driver plus the use cases of the security codes, run with primitives."""

from contextlib import suppress
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from app.user_identity.application.dtos.outputs import SupportSecurityCode
from app.user_identity.application.exceptions import SecurityCodeIncorrectError
from app.user_identity.application.use_cases.get_security_code import (
    GetSecurityCodeUseCase,
)
from app.user_identity.application.use_cases.request_email_verification import (
    RequestEmailVerificationUseCase,
)
from app.user_identity.application.use_cases.validate_email_verification import (
    ValidateEmailVerificationUseCase,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from tests.fakes.user_identity import FakeSecurityCodeGenerator
from tests.user_identity.unit.application.accounts_driver import AccountsDriver

RULES = SecurityCodeRules(
    code_minutes=5,
    max_user_codes=3,
    max_support_codes=2,
    max_attempts=3,
    support_grace_minutes=60,
    user_window_minutes=60,
    password_deadline_minutes=5,
)
LIMA = ZoneInfo('America/Lima')
WRONG_CODE = '999999'


class SecurityCodesDriver(AccountsDriver):
    def __init__(self) -> None:
        super().__init__()
        self._codes = FakeSecurityCodeGenerator()

    def user_without_email(self) -> UUID:
        return self.uow.with_user(cellphone='+51900000999', email=None)

    def sent_code(self) -> str:
        code: str = self.publisher.sent[-1]['code']
        return code

    async def request_verification(self, user_uuid: UUID) -> tuple[UUID, datetime]:
        return await RequestEmailVerificationUseCase(
            uow=self.uow,
            clock=self.clock,
            code_generator=self._codes,
            notice_publisher=self.publisher,
            rules=RULES,
            business_timezone=LIMA,
        ).execute(user_uuid)

    async def validate(self, user_uuid: UUID, process_uuid: UUID, code: str) -> None:
        await ValidateEmailVerificationUseCase(
            uow=self.uow, clock=self.clock, rules=RULES, business_timezone=LIMA
        ).execute(user_uuid, process_uuid, code)

    async def fail_validations(
        self, user_uuid: UUID, process_uuid: UUID, times: int = 3
    ) -> None:
        for _ in range(times):
            with suppress(SecurityCodeIncorrectError):
                await self.validate(user_uuid, process_uuid, WRONG_CODE)

    async def failed_process(self, user_uuid: UUID) -> UUID:
        """The user's codes of the process, each with its attempts spent."""
        for _ in range(RULES.max_user_codes):
            process, _ = await self.request_verification(user_uuid)
            await self.fail_validations(user_uuid, process)
        return process

    async def support_code(
        self, cellphone: str, process_type: str = 'email_verification'
    ) -> SupportSecurityCode:
        return await GetSecurityCodeUseCase(
            uow=self.uow,
            clock=self.clock,
            code_generator=self._codes,
            rules=RULES,
            business_timezone=LIMA,
        ).execute(cellphone, process_type)
