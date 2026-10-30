from datetime import timedelta

from fastapi import APIRouter, Depends, Response, status

from app.user_identity.domain.ports.input.refresh_session_port import (
    RefreshSessionPort,
)
from app.user_identity.domain.ports.input.revoke_session_port import RevokeSessionPort
from app.user_identity.infrastructure.api.dependencies import (
    get_access_token_lifetime,
    get_refresh_session_use_case,
    get_revoke_session_use_case,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.token_schema import (
    RefreshTokenRequest,
    SessionTokensData,
)

router = APIRouter()


@router.post(
    '/tokens',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[SessionTokensData],
)
async def refresh_session(
    request: RefreshTokenRequest,
    use_case: RefreshSessionPort = Depends(get_refresh_session_use_case),
    access_token_lifetime: timedelta = Depends(get_access_token_lifetime),
) -> ApiResponse[SessionTokensData]:
    tokens = await use_case.execute(request.refresh_token)
    data = SessionTokensData.from_session(tokens, access_token_lifetime)
    return ApiResponse(success=True, data=data)


@router.post('/tokens/revoke', status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    request: RefreshTokenRequest,
    use_case: RevokeSessionPort = Depends(get_revoke_session_use_case),
) -> Response:
    await use_case.execute(request.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
