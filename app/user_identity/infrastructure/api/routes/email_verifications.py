from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.application.ports.driving.request_email_verification_port import (
    RequestEmailVerificationPort,
)
from app.user_identity.application.ports.driving.validate_email_verification_port import (
    ValidateEmailVerificationPort,
)
from app.user_identity.infrastructure.api.api_docs.email_verifications import (
    REQUEST_EMAIL_VERIFICATION_DOCS,
    VALIDATE_EMAIL_VERIFICATION_DOCS,
    VALIDATE_EMAIL_VERIFICATION_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_request_email_verification_use_case,
    get_validate_email_verification_use_case,
    require_session_user,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.security_code_schema import (
    CodeValidationRequest,
    EmailVerificationData,
)

router = APIRouter()


@router.post(
    '/email-verifications',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[EmailVerificationData],
    **REQUEST_EMAIL_VERIFICATION_DOCS,
)
async def request_email_verification(
    user_uuid: UUID = Depends(require_session_user),
    use_case: RequestEmailVerificationPort = Depends(
        get_request_email_verification_use_case
    ),
) -> ApiResponse[EmailVerificationData]:
    """Sends a security code to the email of the account of the session: it starts
    an email verification, or goes on with the one in progress (the new code replaces
    the previous one). The code expires in 5 minutes; at most 3 codes within the
    first 60 minutes of the process."""
    process_uuid, code_expires_at = await use_case.execute(user_uuid)
    data = EmailVerificationData(
        process_uuid=process_uuid, code_expires_at=code_expires_at
    )
    return ApiResponse(success=True, data=data)


@router.post(
    '/email-verifications/{process_uuid}/validation',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[None],
    **VALIDATE_EMAIL_VERIFICATION_DOCS,
)
async def validate_email_verification(
    process_uuid: UUID,
    request: Annotated[
        CodeValidationRequest,
        Body(openapi_examples=VALIDATE_EMAIL_VERIFICATION_REQUEST_EXAMPLES),
    ],
    user_uuid: UUID = Depends(require_session_user),
    use_case: ValidateEmailVerificationPort = Depends(
        get_validate_email_verification_use_case
    ),
) -> ApiResponse[None]:
    """Verifies the email of the account of the session with the code it received.
    Each code allows 3 attempts; when the last code spends them, the process fails
    and a new one can start the next day."""
    await use_case.execute(user_uuid, process_uuid, request.code)
    return ApiResponse(success=True)
