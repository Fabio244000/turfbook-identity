from abc import ABC, abstractmethod

from app.user_identity.domain.entities.session_tokens import SessionTokens


class StartSessionPort(ABC):
    @abstractmethod
    async def execute(self, username: str, password: str) -> SessionTokens: ...
