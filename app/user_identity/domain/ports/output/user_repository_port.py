from abc import ABC, abstractmethod
from uuid import UUID

from app.user_identity.domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def exists_by_uuid(self, user_uuid: UUID) -> bool: ...

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def exists_by_cellphone(self, cellphone: str) -> bool: ...
