from abc import ABC, abstractmethod
from uuid import UUID

from app.user_identity.domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def get_by_uuid(self, user_uuid: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_username_for_update(self, username: str) -> User | None:
        """The user, locked until the unit of work ends, so concurrent sign-ins of
        the same account are handled one after the other."""

    @abstractmethod
    async def update(self, user: User) -> None: ...

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def exists_by_cellphone(self, cellphone: str) -> bool: ...
