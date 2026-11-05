from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.domain.ports.input.start_session_port import StartSessionPort
from app.user_identity.infrastructure.api.api_docs.sessions import (
    START_SESSION_DOCS,
    START_SESSION_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_access_token_lifetime,
    get_start_session_use_case,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse
from app.user_identity.infrastructure.api.schemas.session_schema import (
    SessionRequest,
)
from app.user_identity.infrastructure.api.schemas.token_schema import (
    SessionTokensData,
)

router = APIRouter()


@router.post(
    '/sessions',
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[SessionTokensData],
    **START_SESSION_DOCS,
)
async def start_session(
    request: Annotated[
        SessionRequest, Body(openapi_examples=START_SESSION_REQUEST_EXAMPLES)
    ],
    use_case: StartSessionPort = Depends(get_start_session_use_case),
    access_token_lifetime: timedelta = Depends(get_access_token_lifetime),
) -> ApiResponse[SessionTokensData]:
    """Signs a player or owner in with its username and password: it answers an
    access token and a refresh token, and ends the user's sessions on other devices.
    Five failed attempts in a row on the same day (Peru time) block the account."""
    tokens = await use_case.execute(request.username, request.password)
    data = SessionTokensData.from_session(tokens, access_token_lifetime)
    return ApiResponse(success=True, data=data)
