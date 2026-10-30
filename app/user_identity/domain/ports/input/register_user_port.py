from abc import ABC, abstractmethod

from app.user_identity.domain.entities.session_tokens import SessionTokens
from app.user_identity.domain.entities.user import User


class RegisterUserPort(ABC):
    @abstractmethod
    async def execute(
        self,
        first_name: str,
        last_name: str,
        cellphone: str,
        username: str | None = None,
        password: str | None = None,
        email: str | None = None,
        facebook_token: str | None = None,
        gmail_token: str | None = None,
    ) -> tuple[User, SessionTokens]: ...
