from abc import ABC, abstractmethod
from uuid import UUID


class ValidateEmailVerificationPort(ABC):
    @abstractmethod
    async def execute(self, user_uuid: UUID, process_uuid: UUID, code: str) -> None:
        """Verifies the user's email with the code of the process.

        Raises ProcessNotFoundError, SecurityCodeIncorrectError,
        SecurityCodeExpiredError, SecurityCodeExhaustedError or ProcessFailedError."""
