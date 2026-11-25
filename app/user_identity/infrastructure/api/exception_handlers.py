import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.user_identity.application.exceptions import (
    AccountAlreadyBlockedError,
    AccountClosedError,
    AccountNotBlockedError,
    AccountNotFoundError,
    ApplicationError,
    EmailAlreadyVerifiedError,
    InvalidNewPasswordError,
    NoProcessInProgressError,
    PasswordAttemptsExceededError,
    PasswordDeadlineExpiredError,
    PasswordRejectedError,
    PasswordUpdateIntervalError,
    ProcessFailedError,
    ProcessNotAllowedError,
    ProcessNotFoundError,
    RecoveryLimitError,
    SecurityCodeAlreadyValidatedError,
    SecurityCodeDeliveredError,
    SecurityCodeExhaustedError,
    SecurityCodeExpiredError,
    SecurityCodeIncorrectError,
    SecurityCodeLimitError,
    SecurityCodeNotSentError,
    SecurityCodeNotValidatedError,
    SupportCodeLimitError,
    SupportProcessValidatedError,
    UserNotFoundError,
)
from app.user_identity.domain.exceptions import (
    AccountBlockedError,
    DomainError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidUserError,
    MissingRequiredFieldsError,
    UserAlreadyExistsError,
)
from app.user_identity.infrastructure.api.exceptions import (
    InvalidSessionTokenError,
    NotAuthorizedError,
)
from app.user_identity.infrastructure.api.messages import (
    BODY_NOT_JSON,
    FIELD_INVALID,
    FIELD_LABELS,
    FIELD_REQUIRED,
    NOT_AUTHORIZED,
    SESSION_TOKEN_INVALID,
    UNEXPECTED_ERROR,
    UNEXPECTED_ERROR_LOG,
    VALIDATION_FAILED,
)
from app.user_identity.infrastructure.api.schemas.api_response import (
    ApiErrorResponse,
    FieldError,
)

logger = logging.getLogger(__name__)

# What the use cases tell their callers (application errors).
APPLICATION_STATUS_MAP: dict[type[ApplicationError], int] = {
    AccountNotFoundError: 404,
    AccountClosedError: 409,
    AccountAlreadyBlockedError: 409,
    AccountNotBlockedError: 409,
    ProcessNotAllowedError: 422,
    EmailAlreadyVerifiedError: 409,
    SecurityCodeLimitError: 409,
    ProcessFailedError: 409,
    # The notice with the code did not go out: the contract answers it as a 500 with
    # its own text, so the user requests the code again.
    SecurityCodeNotSentError: 500,
    ProcessNotFoundError: 404,
    SecurityCodeIncorrectError: 422,
    SecurityCodeExpiredError: 422,
    SecurityCodeExhaustedError: 409,
    UserNotFoundError: 404,
    NoProcessInProgressError: 404,
    SupportCodeLimitError: 409,
    SecurityCodeDeliveredError: 409,
    SecurityCodeAlreadyValidatedError: 409,
    SupportProcessValidatedError: 409,
    PasswordUpdateIntervalError: 409,
    RecoveryLimitError: 409,
    SecurityCodeNotValidatedError: 409,
    PasswordDeadlineExpiredError: 409,
    PasswordAttemptsExceededError: 409,
    PasswordRejectedError: 422,
    InvalidNewPasswordError: 422,
}

# Domain errors that the use cases which do not translate them yet let through.
STATUS_MAP: dict[type[DomainError], int] = {
    InvalidUserError: 422,
    MissingRequiredFieldsError: 422,
    UserAlreadyExistsError: 409,
    InvalidRefreshTokenError: 401,
    InvalidCredentialsError: 401,
    AccountBlockedError: 403,
}

# Where a request field travels; the client knows it by its name only.
_LOCATIONS = ('body', 'path', 'query', 'header')

# Entity attribute of a rule error → its path in the request body.
FIELD_PATHS = {
    'first_name': 'first_name',
    'last_name': 'last_name',
    'cellphone': 'cellphone',
    'username': 'username',
    'password': 'password',
    'email': 'email',
}


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code = STATUS_MAP.get(type(exc), 500)
    if isinstance(exc, InvalidUserError):
        causes = [
            FieldError(field=FIELD_PATHS[e.field], error=str(e)) for e in exc.errors
        ]
        return _field_errors(status_code, causes)
    return _error(status_code, str(exc))


async def application_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    assert isinstance(exc, ApplicationError)
    status_code = APPLICATION_STATUS_MAP.get(type(exc), 500)
    if exc.causes:
        causes = [FieldError(field=field, error=text) for field, text in exc.causes]
        return _field_errors(status_code, causes)
    return _error(status_code, exc.message)


async def not_authorized_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(401, NOT_AUTHORIZED)


async def invalid_session_token_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    return _error(401, SESSION_TOKEN_INVALID)


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _field_errors(422, [_structure_error(error) for error in exc.errors()])


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(UNEXPECTED_ERROR_LOG, request.method, request.url.path)
    return _error(500, UNEXPECTED_ERROR)


def _structure_error(error: dict[str, Any]) -> FieldError:
    # The client knows a field by its name, not by where it travels.
    path = '.'.join(str(part) for part in error['loc'] if part not in _LOCATIONS)
    label = FIELD_LABELS.get(path, path)
    if error['type'] == 'json_invalid':
        return FieldError(field=path, error=BODY_NOT_JSON)
    # A field sent as `null` is as absent as a missing one.
    if error['type'] == 'missing' or error.get('input') is None:
        return FieldError(field=path, error=FIELD_REQUIRED.format(label=label))
    return FieldError(field=path, error=FIELD_INVALID.format(label=label))


def register_exception_handlers(app: FastAPI) -> None:
    """Every API of the service answers its errors with the same envelope."""
    app.add_exception_handler(ApplicationError, application_exception_handler)
    app.add_exception_handler(DomainError, domain_exception_handler)
    app.add_exception_handler(NotAuthorizedError, not_authorized_handler)
    app.add_exception_handler(InvalidSessionTokenError, invalid_session_token_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)


def _field_errors(status_code: int, causes: Sequence[FieldError]) -> JSONResponse:
    """One cause: its text is the message. Several: a generic message and each field."""
    if len(causes) == 1:
        return _error(status_code, causes[0].error)
    return _error(status_code, VALIDATION_FAILED, list(causes))


def _error(
    status_code: int, message: str, detail: list[FieldError] | None = None
) -> JSONResponse:
    body = ApiErrorResponse(message=message, detail=detail)
    return JSONResponse(status_code=status_code, content=body.model_dump())
