"""Lambda `yearly-purge`: deletes the closed accounts with their sessions and history
(R11). Its handler is the entry point and composition root."""

import asyncio
import logging
from typing import Any

from app.user_identity.application.use_cases.purge_closed_accounts import (
    PurgeClosedAccountsUseCase,
)
from app.user_identity.domain.ports.input.purge_closed_accounts_port import (
    PurgeClosedAccountsPort,
)
from app.user_identity.infrastructure.database.session import async_session
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.jobs.messages import YEARLY_PURGE_LOG

logger = logging.getLogger(__name__)
# One event loop per execution environment, reused on every invocation, as the
# module-level engine requires (reference/queue.md).
_runner = asyncio.Runner()


async def purge(purge_accounts: PurgeClosedAccountsPort) -> dict[str, int]:
    deleted = await purge_accounts.execute()
    logger.info(YEARLY_PURGE_LOG, deleted)
    return {'deleted': deleted}


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    use_case = PurgeClosedAccountsUseCase(SqlAlchemyUnitOfWork(async_session))
    return _runner.run(purge(use_case))
