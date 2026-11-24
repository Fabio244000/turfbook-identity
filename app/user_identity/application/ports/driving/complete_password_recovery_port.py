from abc import ABC, abstractmethod
from uuid import UUID


class CompletePasswordRecoveryPort(ABC):
    @abstractmethod
    async def execute(
        self, process_uuid: UUID, new_password: str, new_password_confirmation: str
    ) -> None:
        """Sets the new password of the validated recovery and closes the user's
        session.

        Raises InvalidNewPasswordError, ProcessNotFoundError,
        SecurityCodeNotValidatedError, PasswordDeadlineExpiredError,
        PasswordRejectedError, PasswordAttemptsExceededError or ProcessFailedError."""
