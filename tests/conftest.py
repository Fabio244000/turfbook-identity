from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine

from config.settings import settings

_engine = create_async_engine(settings.test_database_url or settings.database_url)


@pytest_asyncio.fixture
async def connection() -> AsyncGenerator[AsyncConnection, None]:
    async with _engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


@pytest_asyncio.fixture
async def session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode='create_savepoint',
    ) as db_session:
        yield db_session
