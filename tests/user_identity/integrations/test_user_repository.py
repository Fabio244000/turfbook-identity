from datetime import UTC, date, datetime
from typing import Any

from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.infrastructure.database.repositories.user_repository import (
    UserRepository,
)

BLOCKED_AT = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)
BLOCKED_ON = date(2026, 11, 5)


def _blocked(user: User) -> User:
    user.status = AccountStatus.BLOCKED
    user.failed_attempts = 5
    user.last_failed_attempt_on = BLOCKED_ON
    user.blocked_at = BLOCKED_AT
    return user


def _account_of(user: User) -> tuple[Any, ...]:
    return (
        user.status,
        user.failed_attempts,
        user.last_failed_attempt_on,
        user.blocked_at,
        user.closed_at,
    )


class TestUserRepository:
    async def test_adds_a_user(self, session, new_user, stored_user):
        user = new_user()
        repository = UserRepository(session)

        await repository.add(user)
        await session.commit()

        assert await stored_user(user.uuid) == (
            user.username,
            user.cellphone,
            user.email,
            user.password,
        )

    async def test_finds_an_existing_username(self, session, new_user, insert_user):
        user = new_user()
        await insert_user(user)
        repository = UserRepository(session)

        exists = await repository.exists_by_username(user.username)

        assert exists is True

    async def test_finds_an_existing_email(self, session, new_user, insert_user):
        user = new_user()
        await insert_user(user)
        repository = UserRepository(session)

        exists = await repository.exists_by_email(user.email)

        assert exists is True

    async def test_finds_an_existing_cellphone(self, session, new_user, insert_user):
        user = new_user()
        await insert_user(user)
        repository = UserRepository(session)

        exists = await repository.exists_by_cellphone(user.cellphone)

        assert exists is True

    async def test_does_not_find_a_username_nobody_has(self, session, new_user):
        repository = UserRepository(session)

        exists = await repository.exists_by_username(new_user().username)

        assert exists is False

    async def test_a_new_user_is_stored_active_without_failed_attempts(
        self, session, new_user, stored_account_state
    ):
        user = new_user()

        await UserRepository(session).add(user)
        await session.commit()

        assert await stored_account_state(user.uuid) == ('active', 0, None, None, None)


class TestUserRepositoryGet:
    async def test_gets_a_user_by_uuid_with_its_account_state(
        self, session, new_user, insert_user
    ):
        user = _blocked(new_user())
        await insert_user(user)

        found = await UserRepository(session).get_by_uuid(user.uuid)

        assert found is not None
        assert _account_of(found) == _account_of(user)
        assert (found.uuid, found.username, found.password) == (
            user.uuid,
            user.username,
            user.password,
        )

    async def test_does_not_get_a_uuid_nobody_has(self, session, new_user):
        found = await UserRepository(session).get_by_uuid(new_user().uuid)

        assert found is None

    async def test_gets_a_user_by_username_for_update(
        self, session, new_user, insert_user
    ):
        user = _blocked(new_user())
        await insert_user(user)

        found = await UserRepository(session).get_by_username_for_update(user.username)

        assert found is not None
        assert (found.uuid, _account_of(found)) == (user.uuid, _account_of(user))

    async def test_does_not_get_a_username_nobody_has(self, session, new_user):
        found = await UserRepository(session).get_by_username_for_update(
            new_user().username
        )

        assert found is None


class TestUserRepositoryUpdate:
    async def test_saves_the_account_state_of_a_user(
        self, session, new_user, insert_user, stored_account_state
    ):
        user = new_user()
        await insert_user(user)
        repository = UserRepository(session)
        found = await repository.get_by_uuid(user.uuid)
        assert found is not None

        await repository.update(_blocked(found))
        await session.commit()

        assert await stored_account_state(user.uuid) == (
            'blocked',
            5,
            BLOCKED_ON,
            BLOCKED_AT,
            None,
        )
