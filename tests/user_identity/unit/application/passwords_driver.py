"""The security codes driver plus the use cases of the password processes, run with
primitives."""

from contextlib import suppress
from datetime import datetime
from uuid import UUID

from app.user_identity.application.dtos.inputs import PasswordChange
from app.user_identity.application.exceptions import (
    PasswordRejectedError,
    SecurityCodeIncorrectError,
)
from app.user_identity.application.use_cases.complete_password_recovery import (
    CompletePasswordRecoveryUseCase,
)
from app.user_identity.application.use_cases.complete_password_update import (
    CompletePasswordUpdateUseCase,
)
from app.user_identity.application.use_cases.request_password_recovery import (
    RequestPasswordRecoveryUseCase,
)
from app.user_identity.application.use_cases.request_password_update import (
    RequestPasswordUpdateUseCase,
)
from app.user_identity.application.use_cases.validate_password_recovery import (
    ValidatePasswordRecoveryUseCase,
)
from app.user_identity.application.use_cases.validate_password_update import (
    ValidatePasswordUpdateUseCase,
)
from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from tests.fakes.user_identity import FakeHasher, FakeMinimumDuration
from tests.user_identity.unit.application.accounts_driver import CONTACT, PASSWORD
from tests.user_identity.unit.application.security_codes_driver import (
    LIMA,
    RULES,
    WRONG_CODE,
    SecurityCodesDriver,
)

PASSWORD_RULES = PasswordProcessRules(
    update_interval_minutes=30 * 24 * 60,
    max_failed_recoveries_per_week=4,
    max_password_attempts=5,
    min_difference=3,
)
REQUEST_CODE_MIN_SECONDS = 1.0
NEW_PASSWORD = 'CanchaVerde#Lima7'
# Differs in one character from PASSWORD: too similar to update, not equal to recover.
SIMILAR_PASSWORD = 'GrassElSol2026!!'


class PasswordsDriver(SecurityCodesDriver):
    def __init__(self) -> None:
        super().__init__()
        self.duration = FakeMinimumDuration()
        self.emails: dict[UUID, str] = {}

    async def register(self, username: str, first_name: str = 'luis') -> UUID:
        user = await super().register(username, first_name)
        self.emails[user] = f'{username}@mail.com'
        return user

    async def request_update(
        self, user_uuid: UUID, cellphone: str | None = None, email: str | None = None
    ) -> tuple[UUID, datetime]:
        return await RequestPasswordUpdateUseCase(
            uow=self.uow,
            clock=self.clock,
            code_generator=self._codes,
            notice_publisher=self.publisher,
            code_rules=RULES,
            password_rules=PASSWORD_RULES,
            business_timezone=LIMA,
            minimum_duration=self.duration,
            request_code_min_seconds=REQUEST_CODE_MIN_SECONDS,
        ).execute(
            user_uuid,
            cellphone or self.cellphones[user_uuid],
            email or self.emails[user_uuid],
        )

    async def request_recovery(
        self, cellphone: str, email: str
    ) -> tuple[UUID, datetime]:
        return await RequestPasswordRecoveryUseCase(
            uow=self.uow,
            clock=self.clock,
            code_generator=self._codes,
            notice_publisher=self.publisher,
            code_rules=RULES,
            password_rules=PASSWORD_RULES,
            business_timezone=LIMA,
            minimum_duration=self.duration,
            request_code_min_seconds=REQUEST_CODE_MIN_SECONDS,
            contact=CONTACT,
        ).execute(cellphone, email)

    async def request_recovery_of(self, user_uuid: UUID) -> UUID:
        process, _ = await self.request_recovery(
            self.cellphones[user_uuid], self.emails[user_uuid]
        )
        return process

    async def validate_update(
        self, user_uuid: UUID, process_uuid: UUID, code: str
    ) -> datetime:
        return await ValidatePasswordUpdateUseCase(
            uow=self.uow, clock=self.clock, rules=RULES, business_timezone=LIMA
        ).execute(user_uuid, process_uuid, code)

    async def validate_recovery(self, process_uuid: UUID, code: str) -> datetime:
        return await ValidatePasswordRecoveryUseCase(
            uow=self.uow, clock=self.clock, rules=RULES, business_timezone=LIMA
        ).execute(process_uuid, code)

    async def complete_update(
        self,
        user_uuid: UUID,
        process_uuid: UUID,
        new_password: str = NEW_PASSWORD,
        confirmation: str | None = None,
        current_password: str = PASSWORD,
    ) -> None:
        change = PasswordChange(
            new_password=new_password,
            new_password_confirmation=confirmation or new_password,
            current_password=current_password,
        )
        await CompletePasswordUpdateUseCase(
            uow=self.uow,
            clock=self.clock,
            hasher=FakeHasher(),
            code_rules=RULES,
            password_rules=PASSWORD_RULES,
            business_timezone=LIMA,
        ).execute(user_uuid, process_uuid, change)

    async def complete_recovery(
        self,
        process_uuid: UUID,
        new_password: str = NEW_PASSWORD,
        confirmation: str | None = None,
    ) -> None:
        await CompletePasswordRecoveryUseCase(
            uow=self.uow,
            clock=self.clock,
            hasher=FakeHasher(),
            code_rules=RULES,
            password_rules=PASSWORD_RULES,
            business_timezone=LIMA,
        ).execute(process_uuid, new_password, confirmation or new_password)

    async def validated_update(self, user_uuid: UUID) -> UUID:
        process, _ = await self.request_update(user_uuid)
        await self.validate_update(user_uuid, process, self.sent_code())
        return process

    async def validated_recovery(self, user_uuid: UUID) -> UUID:
        process = await self.request_recovery_of(user_uuid)
        await self.validate_recovery(process, self.sent_code())
        return process

    async def updated(self, user_uuid: UUID) -> UUID:
        process = await self.validated_update(user_uuid)
        await self.complete_update(user_uuid, process)
        return process

    async def recovered(self, user_uuid: UUID) -> UUID:
        process = await self.validated_recovery(user_uuid)
        await self.complete_recovery(process)
        return process

    async def failed_update(self, user_uuid: UUID) -> UUID:
        """The user's codes of an update, each with its attempts spent."""
        for _ in range(RULES.max_user_codes):
            process, _ = await self.request_update(user_uuid)
            for _ in range(RULES.max_attempts):
                with suppress(SecurityCodeIncorrectError):
                    await self.validate_update(user_uuid, process, WRONG_CODE)
        return process

    async def failed_recovery(self, user_uuid: UUID) -> UUID:
        """The user's codes of a recovery, each with its attempts spent."""
        for _ in range(RULES.max_user_codes):
            process = await self.request_recovery_of(user_uuid)
            for _ in range(RULES.max_attempts):
                with suppress(SecurityCodeIncorrectError):
                    await self.validate_recovery(process, WRONG_CODE)
        return process

    async def reject_recoveries(self, process_uuid: UUID, times: int) -> None:
        """Business rejections of the new password: the two entries differ."""
        for _ in range(times):
            with suppress(PasswordRejectedError):
                await self.complete_recovery(
                    process_uuid, NEW_PASSWORD, confirmation='Otra#Contrasena2026'
                )
