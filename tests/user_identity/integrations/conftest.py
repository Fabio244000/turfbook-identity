from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.user_identity.domain.entities.user import User

StoredUser = tuple[Any, ...] | None


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
