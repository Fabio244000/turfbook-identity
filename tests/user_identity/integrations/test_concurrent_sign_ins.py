import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.user_identity.application.use_cases.start_session import (
    StartSessionUseCase,
)
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import InvalidCredentialsError
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from config.settings import settings
from tests.fakes.user_identity import (
    FakeClock,
    FakeHasher,
    FakeNoticePublisher,
    FakeRefreshTokenGenerator,
    FakeTokenIssuer,
)

NOW = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)
ATTEMPTS = 5


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Its own connections, outside the test transaction: concurrent sign-ins must
    see each other's commits, as in production. What they write is deleted."""
    own_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield own_engine
    await own_engine.dispose()


def _start_session(engine: AsyncEngine) -> StartSessionUseCase:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return StartSessionUseCase(
        uow=SqlAlchemyUnitOfWork(session_factory),
        hasher=FakeHasher(),
        token_issuer=FakeTokenIssuer(),
        clock=FakeClock(NOW),
        refresh_token_generator=FakeRefreshTokenGenerator(),
        refresh_token_ttl=timedelta(days=7),
        notice_publisher=FakeNoticePublisher(),
        contact=TurfBookContact(phone='+51 999999998', email='turfbook@gmail.com'),
        max_failed_attempts=ATTEMPTS,
        business_timezone=ZoneInfo('America/Lima'),
    )


async def _insert(engine: AsyncEngine, user: User) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone, username,'
                ' password, email, created_at, updated_at, status, failed_attempts)'
                ' VALUES (:uuid, :first_name, :last_name, :cellphone, :username,'
                " :password, :email, :created_at, :updated_at, 'active', 0)"
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


async def _account_state(engine: AsyncEngine, user_uuid: UUID) -> tuple[Any, ...]:
    async with engine.connect() as connection:
        row = await connection.execute(
            text('SELECT status, failed_attempts FROM users WHERE uuid = :uuid'),
            {'uuid': user_uuid},
        )
        return tuple(row.one())


async def _delete(engine: AsyncEngine, user_uuid: UUID) -> None:
    async with engine.begin() as connection:
        for table in ('account_events', 'refresh_tokens'):
            await connection.execute(
                text(f'DELETE FROM {table} WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            )
        await connection.execute(
            text('DELETE FROM users WHERE uuid = :uuid'), {'uuid': user_uuid}
        )


class TestConcurrentSignIns:
    async def test_simultaneous_failed_attempts_are_all_counted_and_block(
        self, engine, new_user
    ):
        user = new_user(password='hashed-GrassElSol2026!')
        await _insert(engine, user)

        try:
            results = await asyncio.gather(
                *(
                    _start_session(engine).execute(user.username, 'wrong')
                    for _ in range(ATTEMPTS)
                ),
                return_exceptions=True,
            )
            state = await _account_state(engine, user.uuid)
        finally:
            await _delete(engine, user.uuid)

        assert all(isinstance(result, InvalidCredentialsError) for result in results)
        assert state == ('blocked', ATTEMPTS)
