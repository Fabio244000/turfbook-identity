from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.user_identity.domain.entities.security_process import (
    ProcessFailureReason,
    SecurityCodeStatus,
    SecurityProcess,
    SecurityProcessStatus,
    SecurityProcessType,
)
from app.user_identity.infrastructure.database.repositories.security_process_repository import (
    SecurityProcessRepository,
)
from tests.user_identity.integrations.conftest import REGISTERED_AT, RULES

LATER = REGISTERED_AT + timedelta(minutes=2)


class TestSecurityProcessRepository:
    async def test_adds_a_process_with_its_codes(
        self, session, existing_user, new_process, stored_process, stored_codes
    ):
        process = new_process(existing_user)

        await SecurityProcessRepository(session).add(process)
        await session.commit()

        assert await stored_process(process.uuid) == (
            'in_progress',
            1,
            0,
            None,
            None,
            None,
        )
        assert await stored_codes(process.uuid) == [
            ('482913', 'user', 'active', 0, REGISTERED_AT + timedelta(minutes=5))
        ]

    async def test_gets_a_process_with_its_codes_for_update(
        self, session, existing_user, new_process, insert_process
    ):
        process = new_process(existing_user)
        await insert_process(process)

        found = await SecurityProcessRepository(session).get_by_uuid_for_update(
            process.uuid
        )

        assert found == process

    async def test_does_not_get_a_process_nobody_has(self, session):
        repository = SecurityProcessRepository(session)

        assert await repository.get_by_uuid_for_update(uuid4()) is None


class TestSecurityProcessRepositoryUpdate:
    async def test_saves_the_state_and_the_new_codes(
        self, session, existing_user, new_process, insert_process, stored_codes
    ):
        process = new_process(existing_user)
        await insert_process(process)
        process.issue_support_code('735120', LATER, RULES)

        await SecurityProcessRepository(session).update(process)
        await session.commit()

        assert [(c[0], c[1], c[2]) for c in await stored_codes(process.uuid)] == [
            ('482913', 'user', 'replaced'),
            ('735120', 'turfbook', 'active'),
        ]

    async def test_saves_a_sent_code_that_replaces_the_active_one(
        self, session, existing_user, new_process, insert_process, stored_codes
    ):
        process = new_process(existing_user)
        pending = process.issue_user_code('735120', LATER, RULES)
        await insert_process(process)
        process.activate_code(pending.uuid)

        await SecurityProcessRepository(session).update(process)
        await session.commit()

        assert [(c[0], c[2]) for c in await stored_codes(process.uuid)] == [
            ('482913', 'replaced'),
            ('735120', 'active'),
        ]

    async def test_deletes_a_code_removed_from_the_process(
        self, session, existing_user, new_process, insert_process, stored_codes
    ):
        process = new_process(existing_user)
        pending = process.issue_user_code('735120', LATER, RULES)
        await insert_process(process)
        process.discard_code(pending.uuid)

        await SecurityProcessRepository(session).update(process)
        await session.commit()

        assert [c[0] for c in await stored_codes(process.uuid)] == ['482913']

    async def test_saves_a_failed_process(
        self, session, existing_user, new_process, insert_process, stored_process
    ):
        process = new_process(existing_user)
        await insert_process(process)
        process.status = SecurityProcessStatus.FAILED
        process.finished_at = LATER
        process.failure_reason = ProcessFailureReason.ATTEMPTS

        await SecurityProcessRepository(session).update(process)
        await session.commit()

        assert await stored_process(process.uuid) == (
            'failed',
            1,
            0,
            None,
            LATER,
            'attempts',
        )


class TestSecurityProcessRepositoryQueries:
    async def test_gets_the_open_process_of_the_user_and_type(
        self, session, existing_user, new_process, insert_process
    ):
        completed = new_process(
            existing_user, status=SecurityProcessStatus.COMPLETED, finished_at=LATER
        )
        completed.codes[0].status = SecurityCodeStatus.USED
        open_process = new_process(existing_user, started_at=LATER)
        await insert_process(completed)
        await insert_process(open_process)
        repository = SecurityProcessRepository(session)

        found = await repository.get_open_for_update(
            existing_user.uuid, SecurityProcessType.EMAIL_VERIFICATION
        )

        assert found is not None
        assert found.uuid == open_process.uuid

    async def test_does_not_get_an_open_process_of_another_type(
        self, session, existing_user, new_process, insert_process
    ):
        await insert_process(new_process(existing_user))
        repository = SecurityProcessRepository(session)

        found = await repository.get_open_for_update(
            existing_user.uuid, SecurityProcessType.PASSWORD_UPDATE
        )

        assert found is None

    async def test_finds_a_process_failed_since_a_moment(
        self, session, existing_user, new_process, insert_process
    ):
        await insert_process(_failed(new_process(existing_user), at=LATER))
        repository = SecurityProcessRepository(session)

        failed = await repository.has_failed_since(
            existing_user.uuid, SecurityProcessType.EMAIL_VERIFICATION, LATER
        )

        assert failed is True

    async def test_does_not_find_a_process_failed_before_a_moment(
        self, session, existing_user, new_process, insert_process
    ):
        await insert_process(_failed(new_process(existing_user), at=LATER))
        repository = SecurityProcessRepository(session)

        failed = await repository.has_failed_since(
            existing_user.uuid,
            SecurityProcessType.EMAIL_VERIFICATION,
            LATER + timedelta(seconds=1),
        )

        assert failed is False

    async def test_an_incomplete_process_is_not_a_failed_one(
        self, session, existing_user, new_process, insert_process
    ):
        incomplete = new_process(
            existing_user, status=SecurityProcessStatus.INCOMPLETE, finished_at=LATER
        )
        await insert_process(incomplete)
        repository = SecurityProcessRepository(session)

        failed = await repository.has_failed_since(
            existing_user.uuid, SecurityProcessType.EMAIL_VERIFICATION, REGISTERED_AT
        )

        assert failed is False


class TestSecurityProcessRepositoryDelete:
    async def test_deletes_a_process_with_its_codes(
        self,
        session,
        existing_user,
        new_process,
        insert_process,
        stored_process,
        stored_codes,
    ):
        process = new_process(existing_user)
        await insert_process(process)

        await SecurityProcessRepository(session).delete(process.uuid)
        await session.commit()

        assert await stored_process(process.uuid) is None
        assert await stored_codes(process.uuid) == []

    async def test_deletes_only_the_processes_of_the_users_given(
        self,
        session,
        new_user,
        insert_user,
        new_process,
        insert_process,
        stored_process,
    ):
        luis, rosa = new_user(), new_user()
        await insert_user(luis)
        await insert_user(rosa)
        of_luis, of_rosa = new_process(luis), new_process(rosa)
        await insert_process(of_luis)
        await insert_process(of_rosa)

        await SecurityProcessRepository(session).delete_of_users([luis.uuid])
        await session.commit()

        assert await stored_process(of_luis.uuid) is None
        assert await stored_process(of_rosa.uuid) is not None


class TestSecurityProcessGuarantees:
    """What the database guarantees even if two requests run at once."""

    async def test_rejects_a_second_process_in_progress_of_the_same_type(
        self, existing_user, new_process, insert_process
    ):
        await insert_process(new_process(existing_user))

        with pytest.raises(IntegrityError):
            await insert_process(new_process(existing_user))

    async def test_rejects_a_second_active_code_in_a_process(
        self, existing_user, new_process, insert_process
    ):
        process = new_process(existing_user)
        process.issue_support_code('735120', LATER, RULES)
        process.codes[0].status = SecurityCodeStatus.ACTIVE

        with pytest.raises(IntegrityError):
            await insert_process(process)


def _failed(process: SecurityProcess, at: datetime) -> SecurityProcess:
    process.status = SecurityProcessStatus.FAILED
    process.finished_at = at
    process.failure_reason = ProcessFailureReason.ATTEMPTS
    process.codes[0].status = SecurityCodeStatus.EXHAUSTED
    return process
