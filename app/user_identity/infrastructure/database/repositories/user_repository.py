from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.output.user_repository_port import (
    UserRepositoryPort,
)
from app.user_identity.infrastructure.database.models import UserModel


class UserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(self._to_model(user))

    async def exists_by_uuid(self, user_uuid: UUID) -> bool:
        return await self._exists(UserModel.uuid == user_uuid)

    async def exists_by_username(self, username: str) -> bool:
        return await self._exists(UserModel.username == username)

    async def exists_by_cellphone(self, cellphone: str) -> bool:
        return await self._exists(UserModel.cellphone == cellphone)

    async def exists_by_email(self, email: str) -> bool:
        return await self._exists(UserModel.email == email)

    async def _exists(self, condition: ColumnElement[bool]) -> bool:
        query = select(UserModel.uuid).where(condition)
        return (await self._session.execute(query)).first() is not None

    def _to_model(self, user: User) -> UserModel:
        return UserModel(
            uuid=user.uuid,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            password=user.password,
            facebook_token=user.facebook_token,
            gmail_token=user.gmail_token,
            cellphone=user.cellphone,
            email=user.email,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
