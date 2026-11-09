from abc import ABC, abstractmethod


class CloseExpiredAccountsPort(ABC):
    @abstractmethod
    async def execute(self) -> int:
        """Closes the accounts blocked long enough; returns how many it closed."""
