from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.user_identity.application.use_cases.revoke_session import (
    RevokeSessionUseCase,
)
from app.user_identity.domain.entities.refresh_token import RefreshToken
from tests.fakes.user_identity import (
    FakeClock,
    FakeRefreshTokenGenerator,
    FakeUnitOfWork,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


def _token(value: str, session_uuid: UUID | None = None) -> RefreshToken:
    return RefreshToken.issue(
        user_uuid=uuid4(),
        session_uuid=session_uuid or uuid4(),
        token_hash=f'hash-{value}',
        now=NOW,
        ttl=timedelta(days=7),
    )


def _revoke_session(uow: FakeUnitOfWork, now: datetime = NOW) -> RevokeSessionUseCase:
    return RevokeSessionUseCase(
        uow=uow,
        clock=FakeClock(now),
        refresh_token_generator=FakeRefreshTokenGenerator(),
    )


class TestRevokeSession:
    async def test_revokes_every_token_of_the_session(self) -> None:
        session = uuid4()
        uow = FakeUnitOfWork(
            refresh_tokens=[_token('old', session), _token('current', session)]
        )

        await _revoke_session(uow).execute('current')

        assert uow.refresh_tokens.stored('hash-old').revoked_at == NOW
        assert uow.refresh_tokens.stored('hash-current').revoked_at == NOW
        assert uow.committed is True

    async def test_does_not_touch_other_sessions(self) -> None:
        uow = FakeUnitOfWork(refresh_tokens=[_token('mine'), _token('other')])

        await _revoke_session(uow).execute('mine')

        assert uow.refresh_tokens.stored('hash-other').is_revoked is False

    async def test_an_unknown_token_is_ignored(self) -> None:
        uow = FakeUnitOfWork()

        await _revoke_session(uow).execute('unknown')

        assert uow.committed is False
