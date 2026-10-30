from abc import ABC, abstractmethod
from typing import Self

from app.user_identity.domain.ports.output.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
)
from app.user_identity.domain.ports.output.user_repository_port import (
    UserRepositoryPort,
)


class UnitOfWorkPort(ABC):
    users: UserRepositoryPort
    refresh_tokens: RefreshTokenRepositoryPort

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        """Leaving the block without commit() discards the work; after a commit
        there is nothing left to roll back."""
        await self.rollback()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
