from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.application.ports.driving.complete_password_recovery_port import (
    CompletePasswordRecoveryPort,
)
from app.user_identity.application.ports.driving.request_password_recovery_port import (
    RequestPasswordRecoveryPort,
)
from app.user_identity.application.ports.driving.validate_password_recovery_port import (
    ValidatePasswordRecoveryPort,
)
from app.user_identity.infrastructure.api.api_docs.password_recoveries import (
    REQUEST_PASSWORD_RECOVERY_DOCS,
    REQUEST_PASSWORD_RECOVERY_REQUEST_EXAMPLES,
    SET_RECOVERED_PASSWORD_DOCS,
    SET_RECOVERED_PASSWORD_REQUEST_EXAMPLES,
    VALIDATE_PASSWORD_RECOVERY_DOCS,
    VALIDATE_PASSWORD_RECOVERY_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_complete_password_recovery_use_case,
    get_request_password_recovery_use_case,
    get_validate_password_recovery_use_case,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.password_schema import (
    PasswordCodeData,
    PasswordCodeRequest,
    PasswordDeadlineData,
    PasswordRecoveryRequest,
)
from app.user_identity.infrastructure.api.schemas.security_code_schema import (
    CodeValidationRequest,
)

router = APIRouter()


@router.post(
    '/password-recoveries',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[PasswordCodeData],
    **REQUEST_PASSWORD_RECOVERY_DOCS,
)
async def request_password_recovery(
    request: Annotated[
        PasswordCodeRequest,
        Body(openapi_examples=REQUEST_PASSWORD_RECOVERY_REQUEST_EXAMPLES),
    ],
    use_case: RequestPasswordRecoveryPort = Depends(
        get_request_password_recovery_use_case
    ),
) -> ApiResponse[PasswordCodeData]:
    """Sends a security code by email and SMS to recover the password of the account
    identified by its cellphone and email, without a session. The code expires in 5
    minutes; at most 3 codes within the first 60 minutes of the process. At most 4
    failed recoveries a week."""
    process_uuid, code_expires_at = await use_case.execute(
        request.cellphone, request.email
    )
    data = PasswordCodeData(process_uuid=process_uuid, code_expires_at=code_expires_at)
    return ApiResponse(success=True, data=data)


@router.post(
    '/password-recoveries/{process_uuid}/validation',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[PasswordDeadlineData],
    **VALIDATE_PASSWORD_RECOVERY_DOCS,
)
async def validate_password_recovery(
    process_uuid: UUID,
    request: Annotated[
        CodeValidationRequest,
        Body(openapi_examples=VALIDATE_PASSWORD_RECOVERY_REQUEST_EXAMPLES),
    ],
    use_case: ValidatePasswordRecoveryPort = Depends(
        get_validate_password_recovery_use_case
    ),
) -> ApiResponse[PasswordDeadlineData]:
    """Validates the code of the recovery; the new password is set within 5 minutes.
    Each code allows 3 attempts."""
    deadline = await use_case.execute(process_uuid, request.code)
    return ApiResponse(
        success=True, data=PasswordDeadlineData(password_deadline=deadline)
    )


@router.put(
    '/password-recoveries/{process_uuid}/password',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[None],
    **SET_RECOVERED_PASSWORD_DOCS,
)
async def set_recovered_password(
    process_uuid: UUID,
    request: Annotated[
        PasswordRecoveryRequest,
        Body(openapi_examples=SET_RECOVERED_PASSWORD_REQUEST_EXAMPLES),
    ],
    use_case: CompletePasswordRecoveryPort = Depends(
        get_complete_password_recovery_use_case
    ),
) -> ApiResponse[None]:
    """Sets the new password: twice, 15 to 64 characters, and not the current one.
    It closes the session of the user. Up to 5 rejections; the fifth fails the
    process."""
    await use_case.execute(
        process_uuid, request.new_password, request.new_password_confirmation
    )
    return ApiResponse(success=True)
