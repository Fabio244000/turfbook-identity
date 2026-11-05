from uuid import UUID

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.domain.ports.output.user_repository_port import (
    UserRepositoryPort,
)
from app.user_identity.infrastructure.database.models import UserModel


class UserRepository(UserRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(self._to_model(user))

    async def get_by_uuid(self, user_uuid: UUID) -> User | None:
        return await self._get(select(UserModel).where(UserModel.uuid == user_uuid))

    async def get_by_username_for_update(self, username: str) -> User | None:
        query = select(UserModel).where(UserModel.username == username)
        return await self._get(query.with_for_update())

    async def update(self, user: User) -> None:
        await self._session.merge(self._to_model(user))

    async def exists_by_username(self, username: str) -> bool:
        return await self._exists(UserModel.username == username)

    async def exists_by_cellphone(self, cellphone: str) -> bool:
        return await self._exists(UserModel.cellphone == cellphone)

    async def exists_by_email(self, email: str) -> bool:
        return await self._exists(UserModel.email == email)

    async def _get(self, query: Select[tuple[UserModel]]) -> User | None:
        model = (await self._session.execute(query)).scalar_one_or_none()
        return self._to_entity(model) if model else None

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
            status=user.status.value,
            failed_attempts=user.failed_attempts,
            last_failed_attempt_on=user.last_failed_attempt_on,
            blocked_at=user.blocked_at,
            closed_at=user.closed_at,
        )

    def _to_entity(self, model: UserModel) -> User:
        """Rebuilt as stored: the registration rules are not applied again."""
        return User(
            uuid=model.uuid,
            first_name=model.first_name,
            last_name=model.last_name,
            username=model.username,
            password=model.password,
            facebook_token=model.facebook_token,
            gmail_token=model.gmail_token,
            cellphone=model.cellphone,
            email=model.email,
            created_at=model.created_at,
            updated_at=model.updated_at,
            status=AccountStatus(model.status),
            failed_attempts=model.failed_attempts,
            last_failed_attempt_on=model.last_failed_attempt_on,
            blocked_at=model.blocked_at,
            closed_at=model.closed_at,
        )
