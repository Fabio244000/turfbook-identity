from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.infrastructure.database.session import engine


@pytest_asyncio.fixture
async def connection() -> AsyncGenerator[AsyncConnection, None]:
    async with engine.connect() as conn:
        yield conn


@pytest_asyncio.fixture
async def session(connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    transaction = await connection.begin()
    db_session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        yield db_session
    finally:
        await db_session.close()
        await transaction.rollback()
