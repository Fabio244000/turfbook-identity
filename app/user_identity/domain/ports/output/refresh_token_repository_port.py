from abc import ABC, abstractmethod
from uuid import UUID

from app.user_identity.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepositoryPort(ABC):
    @abstractmethod
    async def add(self, token: RefreshToken) -> None: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    async def get_by_session(self, session_uuid: UUID) -> list[RefreshToken]: ...

    @abstractmethod
    async def update(self, token: RefreshToken) -> None: ...
