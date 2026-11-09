from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.user_identity.application.use_cases.close_expired_accounts import (
    CloseExpiredAccountsUseCase,
)
from app.user_identity.application.use_cases.publish_pending_notices import (
    PublishPendingNoticesUseCase,
)
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import AccountStatus
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.jobs.daily_review import review
from tests.fakes.user_identity import FakeClock, FakeNoticePublisher

NOW = datetime(2026, 11, 20, 6, 0, tzinfo=UTC)
CONTACT = TurfBookContact(phone='+51 999999998', email='turfbook@gmail.com')


async def _review(
    session_factory: async_sessionmaker[AsyncSession], publisher: FakeNoticePublisher
) -> dict[str, int]:
    uow, clock = SqlAlchemyUnitOfWork(session_factory), FakeClock(NOW)
    return await review(
        CloseExpiredAccountsUseCase(uow, clock, publisher, CONTACT, 7),
        PublishPendingNoticesUseCase(uow, clock, publisher, CONTACT, 5),
    )


class TestDailyReview:
    async def test_closes_the_expired_accounts_and_tells_their_users(
        self, session_factory, new_user, insert_user, stored_account_state
    ):
        expired = new_user(
            status=AccountStatus.BLOCKED, blocked_at=NOW - timedelta(days=8)
        )
        await insert_user(expired)
        publisher = FakeNoticePublisher()

        summary = await _review(session_factory, publisher)

        state = await stored_account_state(expired.uuid)
        assert state is not None
        assert state[0] == 'closed'
        assert summary['closed'] >= 1
        assert expired.uuid in [notice['recipient'] for notice in publisher.sent]

    async def test_publishes_the_pending_notices(
        self,
        session_factory,
        existing_user,
        new_account_event,
        insert_account_event,
        stored_account_event,
    ):
        pending = new_account_event(existing_user)
        await insert_account_event(pending)

        await _review(session_factory, FakeNoticePublisher())

        stored = await stored_account_event(pending.uuid)
        assert stored is not None
        assert stored[5] == NOW
