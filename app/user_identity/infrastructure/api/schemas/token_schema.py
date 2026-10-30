from datetime import timedelta
from typing import Any, Self

from pydantic import BaseModel

from app.user_identity.domain.entities.session_tokens import SessionTokens


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SessionTokensData(BaseModel):
    """The session: the access token, the refresh token and the access token's
    lifetime in seconds (OAuth 2.0 `expires_in`)."""

    token: str
    refresh_token: str
    expires_in: int

    @classmethod
    def from_session(
        cls, tokens: SessionTokens, access_token_lifetime: timedelta, **fields: Any
    ) -> Self:
        return cls(
            token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=int(access_token_lifetime.total_seconds()),
            **fields,
        )
