from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization

from app.user_identity.domain.ports.driven.clock_port import ClockPort
from app.user_identity.infrastructure.security.jwt_token_issuer import (
    ALGORITHM,
    ISSUER,
)


def public_key_of(private_key: str) -> str:
    """The public key of the signing key, so identity needs no second secret to
    verify its own tokens."""
    key = serialization.load_pem_private_key(private_key.encode(), password=None)
    return (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


class JwtTokenVerifier:
    """Checks a session token at the edge of the API: the use cases only receive
    the user it identifies."""

    def __init__(self, public_key: str, clock: ClockPort) -> None:
        self._public_key = public_key
        self._clock = clock

    def user_of(self, token: str) -> UUID | None:
        """The user of a token in force signed by identity; None for any other."""
        try:
            claims = jwt.decode(
                token,
                self._public_key,
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                # Checked against the clock below: PyJWT reads the real time.
                options={'verify_exp': False, 'require': ['exp', 'iss', 'sub']},
            )
            expired = claims['exp'] <= self._clock.now().timestamp()
            return None if expired else UUID(claims['sub'])
        except (jwt.PyJWTError, ValueError):
            return None
