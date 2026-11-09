from app.user_identity.domain.ports.input.purge_closed_accounts_port import (
    PurgeClosedAccountsPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class PurgeClosedAccountsUseCase(PurgeClosedAccountsPort):
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self._uow = uow

    async def execute(self) -> int:
        """The closed accounts go with their sessions and history, all or nothing;
        the blocked ones stay (R11)."""
        async with self._uow:
            closed = [user.uuid for user in await self._uow.users.get_closed()]
            if not closed:
                return 0
            await self._uow.refresh_tokens.delete_of_users(closed)
            await self._uow.account_events.delete_of_users(closed)
            await self._uow.users.delete(closed)
            await self._uow.commit()
        return len(closed)
