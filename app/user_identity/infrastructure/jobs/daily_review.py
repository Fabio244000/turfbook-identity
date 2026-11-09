"""Lambda `daily-review`: closes the accounts blocked long enough and publishes the
notices still pending (R9). Its handler is the entry point and composition root."""

import asyncio
import logging
from functools import cache
from typing import Any

from app.user_identity.application.use_cases.close_expired_accounts import (
    CloseExpiredAccountsUseCase,
)
from app.user_identity.application.use_cases.publish_pending_notices import (
    PublishPendingNoticesUseCase,
)
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.ports.input.close_expired_accounts_port import (
    CloseExpiredAccountsPort,
)
from app.user_identity.domain.ports.input.publish_pending_notices_port import (
    PublishPendingNoticesPort,
)
from app.user_identity.infrastructure.clock.system_clock import SystemClock
from app.user_identity.infrastructure.database.session import async_session
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.jobs.messages import DAILY_REVIEW_LOG
from app.user_identity.infrastructure.messaging.sns_notice_publisher import (
    SnsNoticePublisher,
    sns_client,
)
from config.settings import settings

logger = logging.getLogger(__name__)
# One event loop per execution environment, reused on every invocation, as the
# module-level engine requires (reference/queue.md).
_runner = asyncio.Runner()


async def review(
    close: CloseExpiredAccountsPort, publish: PublishPendingNoticesPort
) -> dict[str, int]:
    """Closes first, so the notices of today's closes go out in this same run."""
    closed = await close.execute()
    published, pending = await publish.execute()
    logger.info(DAILY_REVIEW_LOG, closed, published, pending)
    return {'closed': closed, 'published': published, 'pending': pending}


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    uow, clock = SqlAlchemyUnitOfWork(async_session), SystemClock()
    publisher, contact = _publisher(), _contact()
    return _runner.run(
        review(
            CloseExpiredAccountsUseCase(
                uow, clock, publisher, contact, settings.block_days_before_close
            ),
            PublishPendingNoticesUseCase(
                uow, clock, publisher, contact, settings.max_failed_attempts
            ),
        )
    )


@cache
def _publisher() -> SnsNoticePublisher:
    """One SNS client per execution environment, created on the first run."""
    client = sns_client(
        settings.notices_topic_arn, settings.notice_publish_timeout_seconds
    )
    return SnsNoticePublisher(client, settings.notices_topic_arn)


def _contact() -> TurfBookContact:
    return TurfBookContact(
        phone=settings.turfbook_contact_phone, email=settings.turfbook_contact_email
    )
