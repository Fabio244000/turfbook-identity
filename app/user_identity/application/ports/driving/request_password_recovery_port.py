from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class RequestPasswordRecoveryPort(ABC):
    @abstractmethod
    async def execute(self, cellphone: str, email: str) -> tuple[UUID, datetime]:
        """Sends a security code to recover the password of the account identified by
        its cellphone and email; returns the process and when the code expires.

        Raises ProcessNotAllowedError, SecurityCodeLimitError,
        SecurityCodeAlreadyValidatedError, RecoveryLimitError, ProcessFailedError or
        SecurityCodeNotSentError."""
