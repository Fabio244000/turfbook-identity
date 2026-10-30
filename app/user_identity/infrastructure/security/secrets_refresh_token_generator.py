import hashlib
import secrets

from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)


class SecretsRefreshTokenGenerator(RefreshTokenGeneratorPort):
    def __init__(self, token_bytes: int) -> None:
        self._token_bytes = token_bytes

    def generate(self) -> str:
        return secrets.token_urlsafe(self._token_bytes)

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
