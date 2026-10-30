from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.ports.output.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
)
from app.user_identity.infrastructure.database.models import RefreshTokenModel


class RefreshTokenRepository(RefreshTokenRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        self._session.add(self._to_model(token))

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        query = select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == token_hash
        )
        model = (await self._session.execute(query)).scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_session(self, session_uuid: UUID) -> list[RefreshToken]:
        query = select(RefreshTokenModel).where(
            RefreshTokenModel.session_uuid == session_uuid
        )
        models = (await self._session.execute(query)).scalars()
        return [self._to_entity(model) for model in models]

    async def update(self, token: RefreshToken) -> None:
        await self._session.merge(self._to_model(token))

    def _to_model(self, token: RefreshToken) -> RefreshTokenModel:
        return RefreshTokenModel(
            uuid=token.uuid,
            user_uuid=token.user_uuid,
            session_uuid=token.session_uuid,
            token_hash=token.token_hash,
            created_at=token.created_at,
            expires_at=token.expires_at,
            used_at=token.used_at,
            revoked_at=token.revoked_at,
        )

    def _to_entity(self, model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            uuid=model.uuid,
            user_uuid=model.user_uuid,
            session_uuid=model.session_uuid,
            token_hash=model.token_hash,
            created_at=model.created_at,
            expires_at=model.expires_at,
            used_at=model.used_at,
            revoked_at=model.revoked_at,
        )
