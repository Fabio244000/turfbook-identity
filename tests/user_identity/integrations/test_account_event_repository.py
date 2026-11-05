from datetime import timedelta

from app.user_identity.infrastructure.database.repositories.account_event_repository import (
    AccountEventRepository,
)
from tests.user_identity.integrations.conftest import REGISTERED_AT

PUBLISHED_AT = REGISTERED_AT + timedelta(seconds=1)


class TestAccountEventRepository:
    async def test_adds_an_event(
        self, session, existing_user, new_account_event, stored_account_event
    ):
        event = new_account_event(existing_user)

        await AccountEventRepository(session).add(event)
        await session.commit()

        assert await stored_account_event(event.uuid) == (
            existing_user.uuid,
            'blocked',
            'failed_attempts',
            'system',
            event.notice_id,
            None,
            REGISTERED_AT,
        )

    async def test_saves_when_its_notice_was_published(
        self,
        session,
        existing_user,
        new_account_event,
        insert_account_event,
        stored_account_event,
    ):
        event = new_account_event(existing_user)
        await insert_account_event(event)
        event.mark_notice_published(PUBLISHED_AT)

        await AccountEventRepository(session).update(event)
        await session.commit()

        stored = await stored_account_event(event.uuid)
        assert stored is not None
        assert stored[5] == PUBLISHED_AT
