import logging
from collections.abc import Sequence
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.user_identity.domain.exceptions import (
    DomainError,
    InvalidRefreshTokenError,
    InvalidUserError,
    MissingRequiredFieldsError,
    UserAlreadyExistsError,
)
from app.user_identity.infrastructure.api.messages import (
    BODY_NOT_JSON,
    FIELD_INVALID,
    FIELD_LABELS,
    FIELD_REQUIRED,
    UNEXPECTED_ERROR,
    UNEXPECTED_ERROR_LOG,
    VALIDATION_FAILED,
)
from app.user_identity.infrastructure.api.schemas.api_response import (
    ApiErrorResponse,
    FieldError,
)

logger = logging.getLogger(__name__)

STATUS_MAP: dict[type[DomainError], int] = {
    InvalidUserError: 422,
    MissingRequiredFieldsError: 422,
    UserAlreadyExistsError: 409,
    InvalidRefreshTokenError: 401,
}

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


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return _field_errors(422, [_structure_error(error) for error in exc.errors()])


async def unexpected_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(UNEXPECTED_ERROR_LOG, request.method, request.url.path)
    return _error(500, UNEXPECTED_ERROR)


def _structure_error(error: dict[str, Any]) -> FieldError:
    path = '.'.join(str(part) for part in error['loc'] if part != 'body')
    label = FIELD_LABELS.get(path, path)
    if error['type'] == 'json_invalid':
        return FieldError(field=path, error=BODY_NOT_JSON)
    # A field sent as `null` is as absent as a missing one.
    if error['type'] == 'missing' or error.get('input') is None:
        return FieldError(field=path, error=FIELD_REQUIRED.format(label=label))
    return FieldError(field=path, error=FIELD_INVALID.format(label=label))


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
