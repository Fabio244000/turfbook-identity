from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.user import User

StoredUser = tuple[Any, ...] | None
StoredRefreshToken = tuple[Any, ...] | None


REGISTERED_AT = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
REFRESH_TOKEN_TTL = timedelta(days=7)


@pytest.fixture
def new_user() -> Callable[..., User]:
    """Builds a valid User whose unique fields collide with no existing row."""

    def _new_user(**overrides: Any) -> User:
        suffix = uuid4().hex[:8]
        data: dict[str, Any] = {
            'first_name': 'fabio',
            'last_name': 'nunez',
            'cellphone': f'+51 9{uuid4().int % 10**8:08d}',
            'username': f'user{suffix}',
            'password': 'hashedsecret123',
            'email': f'user{suffix}@mail.com',
            'created_at': REGISTERED_AT,
            'updated_at': REGISTERED_AT,
        }
        data.update(overrides)
        return User(**data)

    return _new_user


@pytest.fixture
def insert_user(connection: AsyncConnection) -> Callable[[User], Awaitable[None]]:
    async def _insert_user(user: User) -> None:
        await connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone,'
                ' username, password, email, created_at, updated_at)'
                ' VALUES (:uuid, :first_name, :last_name, :cellphone,'
                ' :username, :password, :email, :created_at, :updated_at)'
            ),
            {
                'uuid': user.uuid,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'cellphone': user.cellphone,
                'username': user.username,
                'password': user.password,
                'email': user.email,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            },
        )

    return _insert_user


@pytest_asyncio.fixture
async def existing_user(
    new_user: Callable[..., User], insert_user: Callable[[User], Awaitable[None]]
) -> User:
    """A user already in the database, for rows that reference one."""
    user = new_user()
    await insert_user(user)
    return user


@pytest.fixture
def stored_user(connection: AsyncConnection) -> Callable[[UUID], Awaitable[StoredUser]]:
    async def _stored_user(uuid: UUID) -> StoredUser:
        result = await connection.execute(
            text(
                'SELECT username, cellphone, email, password'
                ' FROM users WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_user


@pytest.fixture
def new_refresh_token() -> Callable[..., RefreshToken]:
    """Builds a valid RefreshToken of `user` whose hash collides with no existing row."""

    def _new_refresh_token(user: User, **overrides: Any) -> RefreshToken:
        data: dict[str, Any] = {
            'user_uuid': user.uuid,
            'session_uuid': uuid4(),
            'token_hash': uuid4().hex + uuid4().hex,
            'created_at': REGISTERED_AT,
            'expires_at': REGISTERED_AT + REFRESH_TOKEN_TTL,
        }
        data.update(overrides)
        return RefreshToken(**data)

    return _new_refresh_token


@pytest.fixture
def insert_refresh_token(
    connection: AsyncConnection,
) -> Callable[[RefreshToken], Awaitable[None]]:
    async def _insert_refresh_token(token: RefreshToken) -> None:
        await connection.execute(
            text(
                'INSERT INTO refresh_tokens (uuid, user_uuid, session_uuid,'
                ' token_hash, created_at, expires_at, used_at, revoked_at)'
                ' VALUES (:uuid, :user_uuid, :session_uuid, :token_hash,'
                ' :created_at, :expires_at, :used_at, :revoked_at)'
            ),
            {
                'uuid': token.uuid,
                'user_uuid': token.user_uuid,
                'session_uuid': token.session_uuid,
                'token_hash': token.token_hash,
                'created_at': token.created_at,
                'expires_at': token.expires_at,
                'used_at': token.used_at,
                'revoked_at': token.revoked_at,
            },
        )

    return _insert_refresh_token


@pytest.fixture
def stored_refresh_token(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[StoredRefreshToken]]:
    async def _stored_refresh_token(uuid: UUID) -> StoredRefreshToken:
        result = await connection.execute(
            text(
                'SELECT user_uuid, session_uuid, token_hash, created_at,'
                ' expires_at, used_at, revoked_at'
                ' FROM refresh_tokens WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_refresh_token
