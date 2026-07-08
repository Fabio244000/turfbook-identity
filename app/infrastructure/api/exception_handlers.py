from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.exceptions.user_exceptions import (
    DomainError,
    InvalidCellphoneError,
    InvalidEmailError,
    InvalidNameError,
    InvalidPasswordError,
    InvalidUsernameError,
    MissingRequiredFieldsError,
    UserAlreadyExistsError,
)
from app.infrastructure.api.schemas.api_response import ApiResponse

STATUS_MAP: dict[type[DomainError], int] = {
    MissingRequiredFieldsError: 422,
    UserAlreadyExistsError: 409,
    InvalidCellphoneError: 400,
    InvalidEmailError: 400,
    InvalidNameError: 400,
    InvalidUsernameError: 400,
    InvalidPasswordError: 400,
}


async def domain_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    domain_exc = exc if isinstance(exc, DomainError) else DomainError(str(exc))
    status_code = STATUS_MAP.get(type(domain_exc), 500)
    response: ApiResponse[None] = ApiResponse(
        success=False,
        message=str(domain_exc),
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )
