from app.user_identity.domain.exceptions.domain_error import DomainError


class InvalidUsernameError(DomainError):
    pass


class InvalidPasswordError(DomainError):
    pass


class InvalidCellphoneError(DomainError):
    pass


class InvalidEmailError(DomainError):
    pass


class InvalidNameError(DomainError):
    pass


class MissingRequiredFieldsError(DomainError):
    pass


class UserAlreadyExistsError(DomainError):
    pass
