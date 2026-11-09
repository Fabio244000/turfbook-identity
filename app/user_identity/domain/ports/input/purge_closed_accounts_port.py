from abc import ABC, abstractmethod


class PurgeClosedAccountsPort(ABC):
    @abstractmethod
    async def execute(self) -> int:
        """Deletes the closed accounts with their sessions and history; returns how
        many it deleted."""
