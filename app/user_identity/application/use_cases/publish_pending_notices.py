from app.user_identity.application.notices import notice_for_event, publish_notice
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.input.publish_pending_notices_port import (
    PublishPendingNoticesPort,
)
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class PublishPendingNoticesUseCase(PublishPendingNoticesPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        notice_publisher: NoticePublisherPort,
        contact: TurfBookContact,
        max_failed_attempts: int,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._notice_publisher = notice_publisher
        self._contact = contact
        self._max_failed_attempts = max_failed_attempts

    async def execute(self) -> tuple[int, int]:
        now = self._clock.now()
        pending = await self._pending()
        published = 0
        for user, event in pending:
            notice = notice_for_event(
                user, event, self._contact, self._max_failed_attempts
            )
            # A notice that fails again stays pending; the others still go out.
            if await publish_notice(self._notice_publisher, event, notice, now):
                async with self._uow:
                    await self._uow.account_events.update(event)
                    await self._uow.commit()
                published += 1
        return published, len(pending) - published

    async def _pending(self) -> list[tuple[User, AccountEvent]]:
        async with self._uow:
            events = await self._uow.account_events.get_pending_notices()
            users = [await self._uow.users.get_by_uuid(e.user_uuid) for e in events]
        return [(u, e) for u, e in zip(users, events, strict=True) if u is not None]
