from app.user_identity.application.use_cases.purge_closed_accounts import (
    PurgeClosedAccountsUseCase,
)
from app.user_identity.domain.entities.user import AccountStatus
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.jobs.yearly_purge import purge
from tests.user_identity.integrations.conftest import REGISTERED_AT


class TestYearlyPurge:
    async def test_deletes_the_closed_accounts(
        self, session_factory, new_user, insert_user, stored_user
    ):
        closed = new_user(status=AccountStatus.CLOSED, closed_at=REGISTERED_AT)
        await insert_user(closed)

        summary = await purge(
            PurgeClosedAccountsUseCase(SqlAlchemyUnitOfWork(session_factory))
        )

        assert await stored_user(closed.uuid) is None
        assert summary['deleted'] >= 1
