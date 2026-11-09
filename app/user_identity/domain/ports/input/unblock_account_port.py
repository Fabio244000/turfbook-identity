from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class UnblockAccountPort(ABC):
    @abstractmethod
    async def execute(self, user_uuid: UUID) -> tuple[str, datetime]:
        """TurfBook unblocks the account; returns its new status and when it changed."""
