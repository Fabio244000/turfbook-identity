from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.infrastructure.api.api_docs.users import (
    REGISTER_USER_DOCS,
    REGISTER_USER_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_access_token_lifetime,
    get_register_user_use_case,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.user_schema import (
    RegisterUserData,
    UserRequest,
    UserResponse,
)

router = APIRouter()


@router.post(
    '/users',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[RegisterUserData],
    **REGISTER_USER_DOCS,
)
async def register_user(
    request: Annotated[
        UserRequest, Body(openapi_examples=REGISTER_USER_REQUEST_EXAMPLES)
    ],
    use_case: RegisterUserPort = Depends(get_register_user_use_case),
    access_token_lifetime: timedelta = Depends(get_access_token_lifetime),
) -> ApiResponse[RegisterUserData]:
    """Registers a player or owner account with its email, and starts its session:
    it answers the user, an access token and a refresh token."""
    user, tokens = await use_case.execute(
        first_name=request.first_name,
        last_name=request.last_name,
        cellphone=request.cellphone,
        username=request.username,
        password=request.password,
        email=request.email,
    )
    data = RegisterUserData.from_session(
        tokens, access_token_lifetime, user=UserResponse.model_validate(user)
    )
    return ApiResponse(success=True, data=data)
