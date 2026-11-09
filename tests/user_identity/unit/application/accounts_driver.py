"""Builds identity's use cases on one set of fakes and runs them with primitives, so a
use case test arranges its state through the use cases (Architecture Patterns with
Python, ch. 5) and its body never holds an entity. Building the use cases is the only
part of these tests that knows the domain."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.user_identity.application.use_cases.block_account import BlockAccountUseCase
from app.user_identity.application.use_cases.close_expired_accounts import (
    CloseExpiredAccountsUseCase,
)
from app.user_identity.application.use_cases.publish_pending_notices import (
    PublishPendingNoticesUseCase,
)
from app.user_identity.application.use_cases.purge_closed_accounts import (
    PurgeClosedAccountsUseCase,
)
from app.user_identity.application.use_cases.refresh_session import (
    RefreshSessionUseCase,
)
from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.application.use_cases.start_session import (
    StartSessionUseCase,
)
from app.user_identity.application.use_cases.unblock_account import (
    UnblockAccountUseCase,
)
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from tests.fakes.user_identity import (
    FakeClock,
    FakeHasher,
    FakeNoticePublisher,
    FakeRefreshTokenGenerator,
    FakeTokenIssuer,
    FakeUnitOfWork,
)

# 12:00 in Lima (UTC-5) on Thursday 2026-11-05.
NOW = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)
PASSWORD = 'GrassElSol2026!'
BLOCK_DAYS_BEFORE_CLOSE = 7
MAX_FAILED_ATTEMPTS = 5
REFRESH_TOKEN_TTL = timedelta(days=30)
CONTACT = TurfBookContact(phone='+51 999999998', email='turfbook@gmail.com')


class AccountsDriver:
    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.clock = FakeClock(NOW)
        self.publisher = FakeNoticePublisher()
        self._generator = FakeRefreshTokenGenerator()
        self._registered = 0

    def later(self, **delta: float) -> None:
        self.clock.current += timedelta(**delta)

    async def register(self, username: str, first_name: str = 'luis') -> UUID:
        self._registered += 1
        user, _ = await RegisterUserUseCase(
            uow=self.uow,
            hasher=FakeHasher(),
            token_issuer=FakeTokenIssuer(),
            clock=self.clock,
            refresh_token_generator=self._generator,
            refresh_token_ttl=REFRESH_TOKEN_TTL,
        ).execute(
            first_name=first_name,
            last_name='huaman',
            cellphone=f'+519{self._registered:08d}',
            username=username,
            password=PASSWORD,
            email=f'{username}@mail.com',
        )
        return user.uuid

    async def sign_in(self, username: str, password: str = PASSWORD) -> str:
        tokens = await StartSessionUseCase(
            uow=self.uow,
            hasher=FakeHasher(),
            token_issuer=FakeTokenIssuer(),
            clock=self.clock,
            refresh_token_generator=self._generator,
            refresh_token_ttl=REFRESH_TOKEN_TTL,
            notice_publisher=self.publisher,
            contact=CONTACT,
            max_failed_attempts=MAX_FAILED_ATTEMPTS,
            business_timezone=ZoneInfo('America/Lima'),
        ).execute(username, password)
        return tokens.refresh_token

    async def refresh(self, refresh_token: str) -> str:
        tokens = await RefreshSessionUseCase(
            uow=self.uow,
            token_issuer=FakeTokenIssuer(),
            clock=self.clock,
            refresh_token_generator=self._generator,
            refresh_token_ttl=REFRESH_TOKEN_TTL,
        ).execute(refresh_token)
        return tokens.refresh_token

    async def block(self, user_uuid: UUID) -> tuple[str, datetime]:
        return await BlockAccountUseCase(
            uow=self.uow,
            clock=self.clock,
            notice_publisher=self.publisher,
            contact=CONTACT,
        ).execute(user_uuid)

    async def unblock(self, user_uuid: UUID) -> tuple[str, datetime]:
        return await UnblockAccountUseCase(
            uow=self.uow,
            clock=self.clock,
            notice_publisher=self.publisher,
            contact=CONTACT,
        ).execute(user_uuid)

    async def close_expired(self) -> int:
        return await CloseExpiredAccountsUseCase(
            uow=self.uow,
            clock=self.clock,
            notice_publisher=self.publisher,
            contact=CONTACT,
            block_days_before_close=BLOCK_DAYS_BEFORE_CLOSE,
        ).execute()

    async def publish_pending(self) -> tuple[int, int]:
        return await PublishPendingNoticesUseCase(
            uow=self.uow,
            clock=self.clock,
            notice_publisher=self.publisher,
            contact=CONTACT,
            max_failed_attempts=MAX_FAILED_ATTEMPTS,
        ).execute()

    async def purge(self) -> int:
        return await PurgeClosedAccountsUseCase(uow=self.uow).execute()
