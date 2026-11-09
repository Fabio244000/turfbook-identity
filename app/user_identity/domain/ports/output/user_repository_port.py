from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
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
    async def get_by_uuid_for_update(self, user_uuid: UUID) -> User | None:
        """The user, locked until the unit of work ends, so a change of TurfBook and a
        sign-in of the same account are handled one after the other."""

    @abstractmethod
    async def get_blocked_before(self, cutoff: datetime) -> list[User]:
        """The blocked users whose block started at `cutoff` or earlier."""

    @abstractmethod
    async def get_closed(self) -> list[User]: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...

    @abstractmethod
    async def delete(self, user_uuids: Sequence[UUID]) -> None: ...

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def exists_by_cellphone(self, cellphone: str) -> bool: ...
