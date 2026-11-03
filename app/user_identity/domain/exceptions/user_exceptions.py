from app.user_identity.domain.exceptions.domain_error import DomainError


class InvalidFieldError(DomainError):
    """A rule of one field of the input; `field` is the entity attribute it belongs to
    (the API maps it to the request's field path)."""

    def __init__(self, message: str, field: str) -> None:
        super().__init__(message)
        self.field = field


class InvalidUsernameError(InvalidFieldError):
    pass


class InvalidPasswordError(InvalidFieldError):
    pass


class InvalidCellphoneError(InvalidFieldError):
    pass


class InvalidEmailError(InvalidFieldError):
    pass


class InvalidNameError(InvalidFieldError):
    pass


class MissingRequiredFieldsError(DomainError):
    pass


class UserAlreadyExistsError(DomainError):
    pass


class InvalidUserError(DomainError):
    """The registration input breaks one or more rules; `errors` holds each cause."""

    def __init__(self, errors: list[InvalidFieldError]) -> None:
        super().__init__(' '.join(str(error) for error in errors))
        self.errors = errors
