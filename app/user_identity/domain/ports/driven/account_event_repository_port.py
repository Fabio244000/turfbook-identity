from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.user_identity.domain.entities.account_event import AccountEvent


class AccountEventRepositoryPort(ABC):
    @abstractmethod
    async def add(self, event: AccountEvent) -> None: ...

    @abstractmethod
    async def update(self, event: AccountEvent) -> None: ...

    @abstractmethod
    async def get_pending_notices(self) -> list[AccountEvent]:
        """The events whose notice is not published yet, oldest first."""

    @abstractmethod
    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None: ...
