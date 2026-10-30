from datetime import timedelta
from uuid import UUID

import jwt

from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort

# Part of the session token contract: consumers verify against these values.
ALGORITHM = 'RS256'
ISSUER = 'turfbook-identity'


class JwtTokenIssuer(TokenIssuerPort):
    def __init__(self, private_key: str, lifetime: timedelta, clock: ClockPort) -> None:
        self._private_key = private_key
        self._lifetime = lifetime
        self._clock = clock

    def issue(self, user_uuid: UUID) -> str:
        now = self._clock.now()
        claims = {
            'sub': str(user_uuid),
            'iss': ISSUER,
            'iat': now,
            'exp': now + self._lifetime,
        }
        return jwt.encode(claims, self._private_key, algorithm=ALGORITHM)
