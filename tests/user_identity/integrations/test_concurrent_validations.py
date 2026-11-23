import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.user_identity.application.exceptions import (
    SecurityCodeExhaustedError,
    SecurityCodeIncorrectError,
)
from app.user_identity.application.use_cases.request_email_verification import (
    RequestEmailVerificationUseCase,
)
from app.user_identity.application.use_cases.validate_email_verification import (
    ValidateEmailVerificationUseCase,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from config.settings import settings
from tests.fakes.user_identity import (
    FakeClock,
    FakeNoticePublisher,
    FakeSecurityCodeGenerator,
)
from tests.user_identity.integrations.conftest import RULES

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
LIMA = ZoneInfo('America/Lima')
WRONG_CODE = '999999'
VALIDATIONS = 5


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """Its own connections, outside the test transaction: concurrent validations must
    see each other's commits, as in production. What they write is deleted."""
    own_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield own_engine
    await own_engine.dispose()


def _uow(engine: AsyncEngine) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(async_sessionmaker(engine, expire_on_commit=False))


async def _request(engine: AsyncEngine, user_uuid: UUID) -> UUID:
    process_uuid, _ = await RequestEmailVerificationUseCase(
        uow=_uow(engine),
        clock=FakeClock(NOW),
        code_generator=FakeSecurityCodeGenerator(),
        notice_publisher=FakeNoticePublisher(),
        rules=RULES,
        business_timezone=LIMA,
    ).execute(user_uuid)
    return process_uuid


async def _validate(engine: AsyncEngine, user_uuid: UUID, process_uuid: UUID) -> None:
    await ValidateEmailVerificationUseCase(
        uow=_uow(engine), clock=FakeClock(NOW), rules=RULES, business_timezone=LIMA
    ).execute(user_uuid, process_uuid, WRONG_CODE)


async def _insert(engine: AsyncEngine, user: User) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone, email,'
                ' created_at, updated_at, status, failed_attempts)'
                ' VALUES (:uuid, :first_name, :last_name, :cellphone, :email,'
                " :created_at, :updated_at, 'active', 0)"
            ),
            {
                'uuid': user.uuid,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'cellphone': user.cellphone,
                'email': user.email,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            },
        )


async def _code_state(engine: AsyncEngine, process_uuid: UUID) -> tuple[Any, ...]:
    async with engine.connect() as connection:
        row = await connection.execute(
            text(
                'SELECT status, failed_attempts FROM security_codes'
                ' WHERE process_uuid = :uuid'
            ),
            {'uuid': process_uuid},
        )
        return tuple(row.one())


async def _delete(engine: AsyncEngine, user_uuid: UUID) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                'DELETE FROM security_codes WHERE process_uuid IN'
                ' (SELECT uuid FROM security_processes WHERE user_uuid = :uuid)'
            ),
            {'uuid': user_uuid},
        )
        for table in ('security_processes', 'account_events'):
            await connection.execute(
                text(f'DELETE FROM {table} WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            )
        await connection.execute(
            text('DELETE FROM users WHERE uuid = :uuid'), {'uuid': user_uuid}
        )


class TestConcurrentValidations:
    async def test_simultaneous_wrong_codes_are_all_counted(self, engine, new_user):
        user = new_user()
        await _insert(engine, user)

        try:
            process_uuid = await _request(engine, user.uuid)
            results = await asyncio.gather(
                *(
                    _validate(engine, user.uuid, process_uuid)
                    for _ in range(VALIDATIONS)
                ),
                return_exceptions=True,
            )
            state = await _code_state(engine, process_uuid)
        finally:
            await _delete(engine, user.uuid)

        rejected = [type(result) for result in results]
        assert rejected.count(SecurityCodeIncorrectError) == RULES.max_attempts
        assert rejected.count(SecurityCodeExhaustedError) == (
            VALIDATIONS - RULES.max_attempts
        )
        assert state == ('exhausted', RULES.max_attempts)
