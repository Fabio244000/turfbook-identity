from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.domain.ports.output.token_issuer_port import TokenIssuerPort
from config.settings import settings


class JwtTokenIssuer(TokenIssuerPort):
    def issue(self, user_uuid: UUID) -> str:
        return str(
            jwt.encode(
                {
                    'sub': str(user_uuid),
                    'exp': datetime.now(UTC)
                    + timedelta(minutes=settings.access_token_expire_minutes),
                },
                key=settings.jwt_secret_key,
                algorithm=settings.jwt_algorithm,
            )
        )
