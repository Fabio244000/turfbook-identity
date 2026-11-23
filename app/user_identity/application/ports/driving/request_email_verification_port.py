from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class RequestEmailVerificationPort(ABC):
    @abstractmethod
    async def execute(self, user_uuid: UUID) -> tuple[UUID, datetime]:
        """Sends a security code to the user's email, in the process of the day or
        in a new one; returns the process and when the code expires.

        Raises ProcessNotAllowedError, EmailAlreadyVerifiedError,
        SecurityCodeLimitError, ProcessFailedError or SecurityCodeNotSentError."""
