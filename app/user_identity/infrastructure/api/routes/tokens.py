from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from app.user_identity.domain.ports.input.refresh_session_port import (
    RefreshSessionPort,
)
from app.user_identity.domain.ports.input.revoke_session_port import RevokeSessionPort
from app.user_identity.infrastructure.api.api_docs.tokens import (
    REFRESH_SESSION_DOCS,
    REFRESH_TOKEN_REQUEST_EXAMPLES,
    REVOKE_SESSION_DOCS,
)
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
    **REFRESH_SESSION_DOCS,
)
async def refresh_session(
    request: Annotated[
        RefreshTokenRequest, Body(openapi_examples=REFRESH_TOKEN_REQUEST_EXAMPLES)
    ],
    use_case: RefreshSessionPort = Depends(get_refresh_session_use_case),
    access_token_lifetime: timedelta = Depends(get_access_token_lifetime),
) -> ApiResponse[SessionTokensData]:
    """Renews the session of the app: a new access token and a new refresh token;
    the refresh token sent can no longer be used."""
    tokens = await use_case.execute(request.refresh_token)
    data = SessionTokensData.from_session(tokens, access_token_lifetime)
    return ApiResponse(success=True, data=data)


@router.post(
    '/tokens/revoke', status_code=status.HTTP_204_NO_CONTENT, **REVOKE_SESSION_DOCS
)
async def revoke_session(
    request: Annotated[
        RefreshTokenRequest, Body(openapi_examples=REFRESH_TOKEN_REQUEST_EXAMPLES)
    ],
    use_case: RevokeSessionPort = Depends(get_revoke_session_use_case),
) -> Response:
    """Signs the user out: closes the session of the refresh token sent. It always
    answers 204, also when the session was already closed or the token is unknown."""
    await use_case.execute(request.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
