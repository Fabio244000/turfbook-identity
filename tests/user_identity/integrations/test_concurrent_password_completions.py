import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.user_identity.application.exceptions import ProcessNotFoundError
from app.user_identity.application.use_cases.complete_password_recovery import (
    CompletePasswordRecoveryUseCase,
)
from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from config.settings import settings
from tests.fakes.user_identity import FakeClock, FakeHasher
from tests.user_identity.integrations.conftest import RULES

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
LIMA = ZoneInfo('America/Lima')
PASSWORD_RULES = PasswordProcessRules(
    update_interval_minutes=43200,
    max_failed_recoveries_per_week=4,
    max_password_attempts=5,
    min_difference=3,
)


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Its own connections, outside the test transaction: concurrent completions must
    see each other's commits, as in production. What they write is deleted."""
    own_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield own_engine
    await own_engine.dispose()


async def _complete(engine: AsyncEngine, process_uuid: UUID, password: str) -> None:
    uow = SqlAlchemyUnitOfWork(async_sessionmaker(engine, expire_on_commit=False))
    await CompletePasswordRecoveryUseCase(
        uow=uow,
        clock=FakeClock(NOW),
        hasher=FakeHasher(),
        code_rules=RULES,
        password_rules=PASSWORD_RULES,
        business_timezone=LIMA,
    ).execute(process_uuid, password, password)


async def _insert_validated_recovery(engine: AsyncEngine) -> tuple[UUID, UUID]:
    """Rosa, with her recovery validated a minute ago."""
    user_uuid, process_uuid = uuid4(), uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone, username,'
                ' password, email, created_at, updated_at, status, failed_attempts)'
                " VALUES (:uuid, 'rosa', 'quispe', :cellphone, :username,"
                " 'hashed-GrassElSol2026!', :email, :at, :at, 'active', 0)"
            ),
            {
                'uuid': user_uuid,
                'cellphone': f'+519{uuid4().int % 10**8:08d}',
                'username': f'rosa{uuid4().hex[:8]}',
                'email': f'{uuid4().hex}@mail.com',
                'at': NOW,
            },
        )
        await connection.execute(
            text(
                'INSERT INTO security_processes (uuid, user_uuid, type, status,'
                ' user_codes, support_codes, started_at, validated_at)'
                " VALUES (:uuid, :user_uuid, 'password_recovery', 'validated', 1, 0,"
                " :at, :at - interval '1 minute')"
            ),
            {'uuid': process_uuid, 'user_uuid': user_uuid, 'at': NOW},
        )
    return user_uuid, process_uuid


async def _stored(engine: AsyncEngine, user_uuid: UUID) -> tuple[str, int]:
    async with engine.connect() as connection:
        password = (
            await connection.execute(
                text('SELECT password FROM users WHERE uuid = :uuid'),
                {'uuid': user_uuid},
            )
        ).scalar_one()
        events = (
            await connection.execute(
                text('SELECT count(*) FROM account_events WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            )
        ).scalar_one()
    return password, events


async def _delete(engine: AsyncEngine, user_uuid: UUID) -> None:
    async with engine.begin() as connection:
        for table in ('refresh_tokens', 'account_events', 'security_processes'):
            await connection.execute(
                text(f'DELETE FROM {table} WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            )
        await connection.execute(
            text('DELETE FROM users WHERE uuid = :uuid'), {'uuid': user_uuid}
        )


class TestConcurrentPasswordCompletions:
    async def test_two_completions_at_once_change_the_password_once(self, engine):
        user_uuid, process_uuid = await _insert_validated_recovery(engine)

        try:
            results = await asyncio.gather(
                _complete(engine, process_uuid, 'CanchaVerde#Lima7'),
                _complete(engine, process_uuid, 'CanchaAzul#Cusco8'),
                return_exceptions=True,
            )
            password, events = await _stored(engine, user_uuid)
        finally:
            await _delete(engine, user_uuid)

        assert sorted(type(r).__name__ for r in results) == [
            'NoneType',
            ProcessNotFoundError.__name__,
        ]
        winner = 'CanchaVerde#Lima7' if results[0] is None else 'CanchaAzul#Cusco8'
        assert password == f'hashed-{winner}'
        assert events == 1
