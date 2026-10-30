from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.user_identity.application.use_cases.refresh_session import (
    RefreshSessionUseCase,
)
from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import InvalidRefreshTokenError
from tests.fakes.user_identity import (
    FakeClock,
    FakeRefreshTokenGenerator,
    FakeTokenIssuer,
    FakeUnitOfWork,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
REFRESH_TOKEN_TTL = timedelta(days=7)


def _user() -> User:
    return User(
        first_name='fabio',
        last_name='nunez',
        cellphone='+51 987654321',
        username='fabio01',
        password='hashedsecret123',
        email='fabio@mail.com',
        created_at=NOW,
        updated_at=NOW,
    )


def _token(user: User, value: str, issued_at: datetime = NOW) -> RefreshToken:
    return RefreshToken.issue(
        user_uuid=user.uuid,
        session_uuid=uuid4(),
        token_hash=f'hash-{value}',
        now=issued_at,
        ttl=REFRESH_TOKEN_TTL,
    )


def _refresh_session(uow: FakeUnitOfWork, now: datetime) -> RefreshSessionUseCase:
    return RefreshSessionUseCase(
        uow=uow,
        token_issuer=FakeTokenIssuer(),
        clock=FakeClock(now),
        refresh_token_generator=FakeRefreshTokenGenerator(),
        refresh_token_ttl=REFRESH_TOKEN_TTL,
    )


class TestRefreshSession:
    async def test_returns_a_new_access_token_and_a_new_refresh_token(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[_token(user, 'old')])

        tokens = await _refresh_session(uow, NOW).execute('old')

        assert tokens.access_token == f'token-{user.uuid}'
        assert tokens.refresh_token == 'refresh-1'
        assert uow.committed is True

    async def test_the_used_token_cannot_be_used_again(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[_token(user, 'old')])

        await _refresh_session(uow, NOW).execute('old')

        assert uow.refresh_tokens.stored('hash-old').used_at == NOW

    async def test_the_new_token_belongs_to_the_same_session_with_a_full_ttl(
        self,
    ) -> None:
        user = _user()
        old = _token(user, 'old')
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[old])
        later = NOW + timedelta(days=3)

        await _refresh_session(uow, later).execute('old')

        new = uow.refresh_tokens.stored('hash-refresh-1')
        assert new.session_uuid == old.session_uuid
        assert new.expires_at == later + REFRESH_TOKEN_TTL


class TestRefreshSessionRejections:
    async def test_rejects_an_unknown_token_without_committing(self) -> None:
        uow = FakeUnitOfWork(users=[_user()])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW).execute('unknown')

        assert uow.committed is False

    async def test_rejects_an_expired_token_without_committing(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[_token(user, 'old')])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW + REFRESH_TOKEN_TTL).execute('old')

        assert uow.committed is False

    async def test_rejects_a_revoked_token_without_committing(self) -> None:
        user = _user()
        revoked = _token(user, 'old')
        revoked.revoke(now=NOW)
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[revoked])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW).execute('old')

        assert uow.committed is False

    async def test_rejects_a_token_whose_user_no_longer_exists(self) -> None:
        uow = FakeUnitOfWork(users=[], refresh_tokens=[_token(_user(), 'old')])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW).execute('old')

        assert uow.committed is False
        assert uow.refresh_tokens.stored('hash-old').used_at is None


class TestRefreshSessionReuse:
    async def test_reusing_a_token_revokes_the_whole_session(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[_token(user, 'old')])
        await _refresh_session(uow, NOW).execute('old')

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW + timedelta(minutes=1)).execute('old')

        assert uow.refresh_tokens.stored('hash-old').is_revoked is True
        assert uow.refresh_tokens.stored('hash-refresh-1').is_revoked is True

    async def test_the_revocation_after_a_reuse_is_committed(self) -> None:
        user = _user()
        used = _token(user, 'old')
        used.use(now=NOW)
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[used])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW).execute('old')

        assert uow.committed is True

    async def test_reuse_does_not_touch_other_sessions(self) -> None:
        user = _user()
        used = _token(user, 'old')
        used.use(now=NOW)
        other = _token(user, 'other')
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[used, other])

        with pytest.raises(InvalidRefreshTokenError):
            await _refresh_session(uow, NOW).execute('old')

        assert uow.refresh_tokens.stored('hash-other').is_revoked is False
