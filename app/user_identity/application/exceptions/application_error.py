from app.user_identity.application.messages import ACCOUNT_NOT_FOUND


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
