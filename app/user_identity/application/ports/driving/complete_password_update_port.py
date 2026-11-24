from abc import ABC, abstractmethod
from uuid import UUID

from app.user_identity.application.dtos.inputs import PasswordChange


class CompletePasswordUpdatePort(ABC):
    @abstractmethod
    async def execute(
        self, user_uuid: UUID, process_uuid: UUID, change: PasswordChange
    ) -> None:
        """Sets the new password of the validated update; the session goes on.

        Raises InvalidNewPasswordError, ProcessNotFoundError,
        SecurityCodeNotValidatedError, PasswordDeadlineExpiredError,
        PasswordRejectedError, PasswordAttemptsExceededError or ProcessFailedError."""
