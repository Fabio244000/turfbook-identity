from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.user_identity.application.ports.driving.get_security_code_port import (
    GetSecurityCodePort,
)
from app.user_identity.infrastructure.api.api_docs.security_codes import (
    GET_SECURITY_CODE_DOCS,
    GET_SECURITY_CODE_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_get_security_code_use_case,
    require_turfbook_api_key,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.security_code_schema import (
    SupportSecurityCodeData,
    SupportSecurityCodeRequest,
)

router = APIRouter(dependencies=[Depends(require_turfbook_api_key)])


@router.post(
    '/security-codes',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[SupportSecurityCodeData],
    **GET_SECURITY_CODE_DOCS,
)
async def get_security_code(
    request: Annotated[
        SupportSecurityCodeRequest,
        Body(openapi_examples=GET_SECURITY_CODE_REQUEST_EXAMPLES),
    ],
    response: Response,
    use_case: GetSecurityCodePort = Depends(get_get_security_code_use_case),
) -> ApiResponse[SupportSecurityCodeData]:
    """TurfBook's support gets the security code of the user's process in progress,
    to help a user whose code did not arrive; the user is found by cellphone. With
    no code in force, it generates one (at most 2, within an hour of the last code)
    that is never sent to the user. The only response that carries a code. Needs
    TurfBook's API key in the X-Api-Key header."""
    code = await use_case.execute(request.cellphone, request.process_type.value)
    if code.generated:
        response.status_code = status.HTTP_201_CREATED
    data = SupportSecurityCodeData(
        process_uuid=code.process_uuid,
        code=code.code,
        code_expires_at=code.code_expires_at,
    )
    return ApiResponse(success=True, data=data)
