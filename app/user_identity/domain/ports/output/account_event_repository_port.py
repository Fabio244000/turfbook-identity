from abc import ABC, abstractmethod

from app.user_identity.domain.entities.account_event import AccountEvent


class AccountEventRepositoryPort(ABC):
    @abstractmethod
    async def add(self, event: AccountEvent) -> None: ...

    @abstractmethod
    async def update(self, event: AccountEvent) -> None: ...
