import pytest
from sqlalchemy.exc import IntegrityError

from app.user_identity.domain.entities.user import AccountStatus
from app.user_identity.domain.exceptions import UserAlreadyExistsError
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


class TestSqlAlchemyUnitOfWork:
    async def test_commit_saves_the_work(self, session_factory, new_user, stored_user):
        user = new_user()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.users.add(user)
            await uow.commit()

        assert await stored_user(user.uuid) is not None

    async def test_leaving_without_commit_discards_the_work(
        self, session_factory, new_user, stored_user
    ):
        user = new_user()

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.users.add(user)
            await uow.users.exists_by_username(user.username)  # sends the INSERT

        assert await stored_user(user.uuid) is None

    async def test_an_error_inside_the_block_discards_the_work(
        self, session_factory, new_user, stored_user
    ):
        user = new_user()

        with pytest.raises(RuntimeError):
            async with SqlAlchemyUnitOfWork(session_factory) as uow:
                await uow.users.add(user)
                await uow.users.exists_by_username(user.username)  # sends the INSERT
                raise RuntimeError('fails after writing')

        assert await stored_user(user.uuid) is None

    async def test_commit_saves_the_user_and_its_refresh_token_together(
        self, session_factory, new_user, new_refresh_token, stored_refresh_token
    ):
        user = new_user()
        token = new_refresh_token(user)

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.users.add(user)
            await uow.refresh_tokens.add(token)
            await uow.commit()

        assert await stored_refresh_token(token.uuid) is not None

    async def test_commit_saves_the_block_and_its_event_together(
        self,
        session_factory,
        new_user,
        insert_user,
        new_account_event,
        stored_account_state,
        stored_account_event,
    ):
        user = new_user()
        await insert_user(user)
        event = new_account_event(user)

        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            found = await uow.users.get_by_uuid(user.uuid)
            assert found is not None
            found.status = AccountStatus.BLOCKED
            await uow.users.update(found)
            await uow.account_events.add(event)
            await uow.commit()

        state = await stored_account_state(user.uuid)
        assert state is not None
        assert state[0] == 'blocked'
        assert await stored_account_event(event.uuid) is not None

    async def test_a_duplicate_found_by_the_database_raises_user_already_exists(
        self, session_factory, new_user, insert_user
    ):
        existing = new_user()
        await insert_user(existing)
        duplicate = new_user(username=existing.username)

        with pytest.raises(
            UserAlreadyExistsError, match='User with this username already exists.'
        ):
            async with SqlAlchemyUnitOfWork(session_factory) as uow:
                await uow.users.add(duplicate)
                await uow.commit()

    async def test_a_violation_without_business_meaning_is_not_translated(
        self, session_factory, new_user, new_refresh_token
    ):
        token_of_a_missing_user = new_refresh_token(new_user())

        with pytest.raises(IntegrityError):
            async with SqlAlchemyUnitOfWork(session_factory) as uow:
                await uow.refresh_tokens.add(token_of_a_missing_user)
                await uow.commit()
