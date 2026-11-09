from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.account_event import (
    AccountEvent,
    AccountEventActor,
    AccountEventReason,
    AccountEventType,
)
from app.user_identity.domain.ports.output.account_event_repository_port import (
    AccountEventRepositoryPort,
)
from app.user_identity.infrastructure.database.models import AccountEventModel


class AccountEventRepository(AccountEventRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AccountEvent) -> None:
        self._session.add(self._to_model(event))

    async def update(self, event: AccountEvent) -> None:
        await self._session.merge(self._to_model(event))

    async def get_pending_notices(self) -> list[AccountEvent]:
        query = (
            select(AccountEventModel)
            .where(
                AccountEventModel.notice_id.is_not(None),
                AccountEventModel.notice_published_at.is_(None),
            )
            .order_by(AccountEventModel.created_at)
        )
        models = (await self._session.execute(query)).scalars()
        return [self._to_entity(model) for model in models]

    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None:
        await self._session.execute(
            delete(AccountEventModel).where(AccountEventModel.user_uuid.in_(user_uuids))
        )

    def _to_model(self, event: AccountEvent) -> AccountEventModel:
        return AccountEventModel(
            uuid=event.uuid,
            user_uuid=event.user_uuid,
            type=event.type.value,
            reason=event.reason.value,
            actor=event.actor.value,
            notice_id=event.notice_id,
            notice_published_at=event.notice_published_at,
            created_at=event.created_at,
        )

    def _to_entity(self, model: AccountEventModel) -> AccountEvent:
        return AccountEvent(
            uuid=model.uuid,
            user_uuid=model.user_uuid,
            type=AccountEventType(model.type),
            reason=AccountEventReason(model.reason),
            actor=AccountEventActor(model.actor),
            notice_id=model.notice_id,
            notice_published_at=model.notice_published_at,
            created_at=model.created_at,
        )
