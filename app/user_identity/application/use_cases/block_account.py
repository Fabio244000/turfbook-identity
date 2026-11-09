from datetime import datetime
from functools import partial
from uuid import UUID

from app.user_identity.application.accounts import account_for_update, change_account
from app.user_identity.application.notices import account_change_notice, publish_notice
from app.user_identity.application.sessions import revoke_user_sessions
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.input.block_account_port import BlockAccountPort
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class BlockAccountUseCase(BlockAccountPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        notice_publisher: NoticePublisherPort,
        contact: TurfBookContact,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._notice_publisher = notice_publisher
        self._contact = contact

    async def execute(self, user_uuid: UUID) -> tuple[str, datetime]:
        now = self._clock.now()
        async with self._uow:
            # Locked until the commit: a sign-in of the account waits for the block.
            user = await account_for_update(self._uow, user_uuid)
            change_account(partial(user.block_by_turfbook, now))
            await self._uow.users.update(user)
            await revoke_user_sessions(self._uow, user.uuid, now)
            event = AccountEvent.blocked_by_turfbook(user.uuid, now)
            await self._uow.account_events.add(event)
            await self._uow.commit()
        await self._notify(user, event, now)
        return user.status.value, now

    async def _notify(self, user: User, event: AccountEvent, now: datetime) -> None:
        """After the change is committed: a notice that cannot be published stays
        pending for the daily review, and the change answers the same (§5)."""
        notice = account_change_notice(user, event, self._contact)
        if await publish_notice(self._notice_publisher, event, notice, now):
            async with self._uow:
                await self._uow.account_events.update(event)
                await self._uow.commit()
