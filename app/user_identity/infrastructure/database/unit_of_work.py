from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.infrastructure.database.constraint_errors import (
    to_domain_error,
)
from app.user_identity.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.user_identity.infrastructure.database.repositories.user_repository import (
    UserRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = UserRepository(self._session)
        self.refresh_tokens = RefreshTokenRepository(self._session)
        return await super().__aenter__()

    async def __aexit__(self, *args: object) -> None:
        await super().__aexit__(*args)
        await self._session.close()

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as error:
            domain_error = to_domain_error(error)
            if domain_error is None:
                raise  # no business meaning: a bug, surfaces as a 500
            raise domain_error from error

    async def rollback(self) -> None:
        await self._session.rollback()
