from app.user_identity.application.messages import (
    ACCOUNT_NOT_FOUND,
    NO_PROCESS_IN_PROGRESS,
    PROCESS_NOT_ALLOWED,
    PROCESS_NOT_FOUND,
    SECURITY_CODE_NOT_SENT,
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


class GracePeriodEndedError(ApplicationError):
    pass
