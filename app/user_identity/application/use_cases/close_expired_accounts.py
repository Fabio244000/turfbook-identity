from datetime import datetime, timedelta
from uuid import UUID

from app.user_identity.application.notices import account_change_notice, publish_notice
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.input.close_expired_accounts_port import (
    CloseExpiredAccountsPort,
)
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class CloseExpiredAccountsUseCase(CloseExpiredAccountsPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        notice_publisher: NoticePublisherPort,
        contact: TurfBookContact,
        block_days_before_close: int,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._notice_publisher = notice_publisher
        self._contact = contact
        self._block_days_before_close = block_days_before_close

    async def execute(self) -> int:
        now = self._clock.now()
        cutoff = now - timedelta(days=self._block_days_before_close)
        async with self._uow:
            expired = [u.uuid for u in await self._uow.users.get_blocked_before(cutoff)]
        closed = 0
        for user_uuid in expired:
            if await self._close(user_uuid, now):
                closed += 1
        return closed

    async def _close(self, user_uuid: UUID, now: datetime) -> bool:
        """Each account in its own unit of work: a failure leaves the accounts already
        closed as they are, and the next review closes the rest."""
        async with self._uow:
            user = await self._uow.users.get_by_uuid_for_update(user_uuid)
            if user is None or not user.close_if_expired(
                now, self._block_days_before_close
            ):
                return False
            await self._uow.users.update(user)
            event = AccountEvent.closed_for_inactivity(user.uuid, now)
            await self._uow.account_events.add(event)
            await self._uow.commit()
        await self._notify(user, event, now)
        return True

    async def _notify(self, user: User, event: AccountEvent, now: datetime) -> None:
        """After the change is committed: a notice that cannot be published stays
        pending for the daily review, and the change answers the same (§5)."""
        notice = account_change_notice(user, event, self._contact)
        if await publish_notice(self._notice_publisher, event, notice, now):
            async with self._uow:
                await self._uow.account_events.update(event)
                await self._uow.commit()
