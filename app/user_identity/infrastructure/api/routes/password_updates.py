from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.application.dtos.inputs import PasswordChange
from app.user_identity.application.ports.driving.complete_password_update_port import (
    CompletePasswordUpdatePort,
)
from app.user_identity.application.ports.driving.request_password_update_port import (
    RequestPasswordUpdatePort,
)
from app.user_identity.application.ports.driving.validate_password_update_port import (
    ValidatePasswordUpdatePort,
)
from app.user_identity.infrastructure.api.api_docs.password_updates import (
    REQUEST_PASSWORD_UPDATE_DOCS,
    REQUEST_PASSWORD_UPDATE_REQUEST_EXAMPLES,
    SET_UPDATED_PASSWORD_DOCS,
    SET_UPDATED_PASSWORD_REQUEST_EXAMPLES,
    VALIDATE_PASSWORD_UPDATE_DOCS,
    VALIDATE_PASSWORD_UPDATE_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_complete_password_update_use_case,
    get_request_password_update_use_case,
    get_validate_password_update_use_case,
    require_session_user,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.password_schema import (
    PasswordCodeData,
    PasswordCodeRequest,
    PasswordDeadlineData,
    PasswordUpdateRequest,
)
from app.user_identity.infrastructure.api.schemas.security_code_schema import (
    CodeValidationRequest,
)

router = APIRouter()


@router.post(
    '/password-updates',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[PasswordCodeData],
    **REQUEST_PASSWORD_UPDATE_DOCS,
)
async def request_password_update(
    request: Annotated[
        PasswordCodeRequest,
        Body(openapi_examples=REQUEST_PASSWORD_UPDATE_REQUEST_EXAMPLES),
    ],
    user_uuid: UUID = Depends(require_session_user),
    use_case: RequestPasswordUpdatePort = Depends(get_request_password_update_use_case),
) -> ApiResponse[PasswordCodeData]:
    """Sends a security code by email and SMS to update the password of the account
    of the session, identified by its cellphone and email. The code expires in 5
    minutes; at most 3 codes within the first 60 minutes of the process. At most one
    update every 30 days."""
    process_uuid, code_expires_at = await use_case.execute(
        user_uuid, request.cellphone, request.email
    )
    data = PasswordCodeData(process_uuid=process_uuid, code_expires_at=code_expires_at)
    return ApiResponse(success=True, data=data)


@router.post(
    '/password-updates/{process_uuid}/validation',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[PasswordDeadlineData],
    **VALIDATE_PASSWORD_UPDATE_DOCS,
)
async def validate_password_update(
    process_uuid: UUID,
    request: Annotated[
        CodeValidationRequest,
        Body(openapi_examples=VALIDATE_PASSWORD_UPDATE_REQUEST_EXAMPLES),
    ],
    user_uuid: UUID = Depends(require_session_user),
    use_case: ValidatePasswordUpdatePort = Depends(
        get_validate_password_update_use_case
    ),
) -> ApiResponse[PasswordDeadlineData]:
    """Validates the code of the update; the new password is set within 5 minutes.
    Each code allows 3 attempts."""
    deadline = await use_case.execute(user_uuid, process_uuid, request.code)
    return ApiResponse(
        success=True, data=PasswordDeadlineData(password_deadline=deadline)
    )


@router.put(
    '/password-updates/{process_uuid}/password',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[None],
    **SET_UPDATED_PASSWORD_DOCS,
)
async def set_updated_password(
    process_uuid: UUID,
    request: Annotated[
        PasswordUpdateRequest,
        Body(openapi_examples=SET_UPDATED_PASSWORD_REQUEST_EXAMPLES),
    ],
    user_uuid: UUID = Depends(require_session_user),
    use_case: CompletePasswordUpdatePort = Depends(
        get_complete_password_update_use_case
    ),
) -> ApiResponse[None]:
    """Sets the new password with the current one: twice, 15 to 64 characters, and
    3 characters or more apart from the current one. The session goes on. Up to 5
    rejections; the fifth fails the process."""
    change = PasswordChange(
        new_password=request.new_password,
        new_password_confirmation=request.new_password_confirmation,
        current_password=request.current_password,
    )
    await use_case.execute(user_uuid, process_uuid, change)
    return ApiResponse(success=True)
