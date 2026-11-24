from app.user_identity.application.messages import (
    ACCOUNT_NOT_FOUND,
    NO_PROCESS_IN_PROGRESS,
    PASSWORD_DEADLINE_EXPIRED,
    PROCESS_NOT_ALLOWED,
    PROCESS_NOT_FOUND,
    RECOVERY_LIMIT,
    SECURITY_CODE_NOT_SENT,
    SUPPORT_PROCESS_VALIDATED,
    USER_NOT_FOUND,
)


class ApplicationError(Exception):
    """What a use case tells its caller when an operation fails; the caller (the API,
    a queue consumer) presents it to its client. `causes` holds (field, message) pairs
    when several rules break at once."""

    def __init__(self, message: str, causes: tuple[tuple[str, str], ...] = ()) -> None:
        super().__init__(message)
        self.message = message
        self.causes = causes


class AccountNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(ACCOUNT_NOT_FOUND)


class AccountClosedError(ApplicationError):
    pass


class AccountAlreadyBlockedError(ApplicationError):
    pass


class AccountNotBlockedError(ApplicationError):
    pass


class ProcessNotAllowedError(ApplicationError):
    def __init__(self, message: str = PROCESS_NOT_ALLOWED) -> None:
        super().__init__(message)


class EmailAlreadyVerifiedError(ApplicationError):
    pass


class SecurityCodeLimitError(ApplicationError):
    pass


class ProcessFailedError(ApplicationError):
    pass


class SecurityCodeNotSentError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(SECURITY_CODE_NOT_SENT)


class ProcessNotFoundError(ApplicationError):
    def __init__(self, message: str = PROCESS_NOT_FOUND) -> None:
        super().__init__(message)


class SecurityCodeIncorrectError(ApplicationError):
    pass


class SecurityCodeExpiredError(ApplicationError):
    pass


class SecurityCodeExhaustedError(ApplicationError):
    pass


class UserNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(USER_NOT_FOUND)


class NoProcessInProgressError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(NO_PROCESS_IN_PROGRESS)


class SupportCodeLimitError(ApplicationError):
    pass


class SecurityCodeDeliveredError(ApplicationError):
    pass


class SecurityCodeAlreadyValidatedError(ApplicationError):
    pass


class SupportProcessValidatedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(SUPPORT_PROCESS_VALIDATED)


class PasswordUpdateIntervalError(ApplicationError):
    pass


class RecoveryLimitError(ApplicationError):
    def __init__(self, phone: str, email: str) -> None:
        super().__init__(RECOVERY_LIMIT.format(phone=phone, email=email))


class SecurityCodeNotValidatedError(ApplicationError):
    pass


class PasswordDeadlineExpiredError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(PASSWORD_DEADLINE_EXPIRED)


class PasswordAttemptsExceededError(ApplicationError):
    pass


class PasswordRejectedError(ApplicationError):
    """A business rule of the new password: it counts as an attempt."""


class InvalidNewPasswordError(ApplicationError):
    """The format of the new password, by field: it does not count as an attempt."""
