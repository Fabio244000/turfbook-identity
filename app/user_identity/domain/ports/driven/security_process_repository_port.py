from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)


class SecurityProcessRepositoryPort(ABC):
    """Stores each process with its codes: a code removed from the process is
    deleted."""

    @abstractmethod
    async def add(self, process: SecurityProcess) -> None: ...

    @abstractmethod
    async def update(self, process: SecurityProcess) -> None: ...

    @abstractmethod
    async def get_by_uuid_for_update(
        self, process_uuid: UUID
    ) -> SecurityProcess | None:
        """The process, locked until the unit of work ends, so concurrent attempts
        on its code are counted one by one."""

    @abstractmethod
    async def get_open_for_update(
        self, user_uuid: UUID, type: SecurityProcessType
    ) -> SecurityProcess | None:
        """The user's process of that type still in progress or validated, locked
        until the unit of work ends."""

    @abstractmethod
    async def has_failed_since(
        self, user_uuid: UUID, type: SecurityProcessType, since: datetime
    ) -> bool: ...

    @abstractmethod
    async def delete(self, process_uuid: UUID) -> None: ...

    @abstractmethod
    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None: ...
