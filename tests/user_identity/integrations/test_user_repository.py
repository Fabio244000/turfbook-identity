from app.user_identity.infrastructure.database.repositories.user_repository import (
    UserRepository,
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
