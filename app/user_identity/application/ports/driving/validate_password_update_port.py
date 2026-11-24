from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class ValidatePasswordUpdatePort(ABC):
    @abstractmethod
    async def execute(self, user_uuid: UUID, process_uuid: UUID, code: str) -> datetime:
        """Validates the code of the user's password update; returns the deadline to
        set the new password.

        Raises ProcessNotFoundError, SecurityCodeIncorrectError,
        SecurityCodeExpiredError, SecurityCodeExhaustedError or ProcessFailedError."""
