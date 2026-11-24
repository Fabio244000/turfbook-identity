from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class RequestPasswordUpdatePort(ABC):
    @abstractmethod
    async def execute(
        self, user_uuid: UUID, cellphone: str, email: str
    ) -> tuple[UUID, datetime]:
        """Sends a security code to update the password of the account of the
        session, identified by its cellphone and email; returns the process and when
        the code expires.

        Raises ProcessNotAllowedError, SecurityCodeLimitError,
        SecurityCodeAlreadyValidatedError, PasswordUpdateIntervalError,
        ProcessFailedError or SecurityCodeNotSentError."""
