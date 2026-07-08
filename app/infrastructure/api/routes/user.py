from fastapi import APIRouter, Depends, status

from app.application.use_cases.register_user import RegisterUserUseCase
from app.infrastructure.api.dependencies import get_register_user_use_case
from app.infrastructure.api.schemas.api_response import ApiResponse
from app.infrastructure.api.schemas.user_schema import (
    RegisterUserData,
    UserRequest,
    UserResponse,
)

router = APIRouter()


@router.post(
    '/users',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[RegisterUserData],
)
async def register_user(
    request: UserRequest,
    use_case: RegisterUserUseCase = Depends(get_register_user_use_case),
) -> ApiResponse[RegisterUserData]:
    user, token = await use_case.execute(
        first_name=request.first_name,
        last_name=request.last_name,
        cellphone=request.cellphone,
        username=request.username,
        password=request.password,
        email=request.email,
    )
    user_response = UserResponse.model_validate(user)
    data = RegisterUserData(
        user=user_response,
        token=token,
    )
    return ApiResponse(success=True, data=data)
