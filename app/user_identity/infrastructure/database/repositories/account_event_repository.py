from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.account_event import AccountEvent
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
