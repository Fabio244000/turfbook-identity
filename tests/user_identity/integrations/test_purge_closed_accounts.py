from app.user_identity.application.use_cases.purge_closed_accounts import (
    PurgeClosedAccountsUseCase,
)
from app.user_identity.domain.entities.user import AccountStatus
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from tests.user_identity.integrations.conftest import REGISTERED_AT


class TestPurgeClosedAccounts:
    """Its history can only be seen in the database (D17): with the real foreign keys,
    a closed user cannot go while its sessions or events stay."""

    async def test_deletes_a_closed_account_with_its_sessions_and_history(
        self,
        session_factory,
        new_user,
        insert_user,
        new_refresh_token,
        insert_refresh_token,
        new_account_event,
        insert_account_event,
        stored_user,
        stored_refresh_token,
        stored_account_event,
    ):
        closed = new_user(status=AccountStatus.CLOSED, closed_at=REGISTERED_AT)
        await insert_user(closed)
        token, event = new_refresh_token(closed), new_account_event(closed)
        await insert_refresh_token(token)
        await insert_account_event(event)

        await PurgeClosedAccountsUseCase(
            SqlAlchemyUnitOfWork(session_factory)
        ).execute()

        assert await stored_user(closed.uuid) is None
        assert await stored_refresh_token(token.uuid) is None
        assert await stored_account_event(event.uuid) is None

    async def test_keeps_a_blocked_account(
        self, session_factory, new_user, insert_user, stored_user
    ):
        blocked = new_user(status=AccountStatus.BLOCKED, blocked_at=REGISTERED_AT)
        await insert_user(blocked)

        await PurgeClosedAccountsUseCase(
            SqlAlchemyUnitOfWork(session_factory)
        ).execute()

        assert await stored_user(blocked.uuid) is not None
