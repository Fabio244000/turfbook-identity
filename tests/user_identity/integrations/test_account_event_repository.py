from datetime import timedelta

from app.user_identity.domain.entities.account_event import AccountEvent
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
            None,
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

    async def test_finds_the_pending_notices_oldest_first(
        self, session, existing_user, new_account_event, insert_account_event
    ):
        newer = new_account_event(
            existing_user, created_at=REGISTERED_AT + timedelta(1)
        )
        older = new_account_event(existing_user)
        published = new_account_event(existing_user, notice_published_at=PUBLISHED_AT)
        without_notice = new_account_event(existing_user, notice_id=None)
        for event in (newer, older, published, without_notice):
            await insert_account_event(event)

        found = await AccountEventRepository(session).get_pending_notices()

        ours = [event for event in found if event.user_uuid == existing_user.uuid]
        assert ours == [older, newer]

    async def test_deletes_only_the_events_of_the_users_given(
        self,
        session,
        new_user,
        insert_user,
        new_account_event,
        insert_account_event,
        stored_account_event,
    ):
        deleted_user, kept_user = new_user(), new_user()
        for user in (deleted_user, kept_user):
            await insert_user(user)
        deleted, kept = new_account_event(deleted_user), new_account_event(kept_user)
        for event in (deleted, kept):
            await insert_account_event(event)

        await AccountEventRepository(session).delete_of_users([deleted_user.uuid])
        await session.commit()

        assert await stored_account_event(deleted.uuid) is None
        assert await stored_account_event(kept.uuid) is not None


class TestAccountEventRepositorySecurityCodes:
    async def test_adds_an_event_of_a_security_process_without_notice(
        self, session, existing_user, new_process, insert_process, stored_account_event
    ):
        process = new_process(existing_user)
        await insert_process(process)
        process_uuid = process.uuid
        event = AccountEvent.support_code_generated(
            existing_user.uuid, process_uuid, REGISTERED_AT
        )

        await AccountEventRepository(session).add(event)
        await session.commit()

        assert await stored_account_event(event.uuid) == (
            existing_user.uuid,
            'support_code_generated',
            'support_request',
            'turfbook',
            None,
            None,
            REGISTERED_AT,
            process_uuid,
        )

    async def test_adds_the_email_verified_by_the_user(
        self, session, existing_user, new_process, insert_process, stored_account_event
    ):
        process = new_process(existing_user)
        await insert_process(process)
        event = AccountEvent.email_verified(
            existing_user.uuid, process.uuid, REGISTERED_AT
        )

        await AccountEventRepository(session).add(event)
        await session.commit()

        stored = await stored_account_event(event.uuid)
        assert stored is not None
        assert stored[1:4] == ('email_verified', 'security_code', 'user')
