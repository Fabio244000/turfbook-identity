from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class ValidatePasswordRecoveryPort(ABC):
    @abstractmethod
    async def execute(self, process_uuid: UUID, code: str) -> datetime:
        """Validates the code of a password recovery; returns the deadline to set the
        new password.

        Raises ProcessNotFoundError, SecurityCodeIncorrectError,
        SecurityCodeExpiredError, SecurityCodeExhaustedError or ProcessFailedError."""
