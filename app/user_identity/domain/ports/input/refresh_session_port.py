from abc import ABC, abstractmethod

from app.user_identity.domain.entities.session_tokens import SessionTokens


class RefreshSessionPort(ABC):
    @abstractmethod
    async def execute(self, refresh_token: str) -> SessionTokens: ...
