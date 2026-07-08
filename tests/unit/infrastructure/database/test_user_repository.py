import pytest

from app.domain.entities.user import User
from app.domain.exceptions import UserAlreadyExistsError
from app.infrastructure.database.repositories.user_repository import UserRepository


def _valid_user(**overrides):
    data = {
        'first_name': 'fabio',
        'last_name': 'nunez garcia',
        'cellphone': '+51 987654321',
        'username': 'fabio01',
        'password': 'hashedpassword123',
        'email': 'fabio@mail.com',
    }
    data.update(overrides)
    return User(**data)


class TestUserRepositorySave:
    async def test_saves_user(self, session):
        repository = UserRepository(session)
        user = _valid_user()
        saved = await repository.save(user)
        assert saved.uuid == user.uuid

    async def test_does_not_allow_duplicate_username(self, session):
        repository = UserRepository(session)
        await repository.save(
            _valid_user(
                username='samename', cellphone='+51 911111111', email='a@mail.com'
            )
        )
        with pytest.raises(UserAlreadyExistsError):
            await repository.save(
                _valid_user(
                    username='samename', cellphone='+51 922222222', email='b@mail.com'
                )
            )

    async def test_does_not_allow_duplicate_email(self, session):
        repository = UserRepository(session)
        await repository.save(
            _valid_user(
                username='usera', cellphone='+51 911111111', email='same@mail.com'
            )
        )
        with pytest.raises(UserAlreadyExistsError):
            await repository.save(
                _valid_user(
                    username='userb', cellphone='+51 922222222', email='same@mail.com'
                )
            )

    async def test_does_not_allow_duplicate_cellphone(self, session):
        repository = UserRepository(session)
        await repository.save(
            _valid_user(username='usera', cellphone='+51 911111111', email='a@mail.com')
        )
        with pytest.raises(UserAlreadyExistsError):
            await repository.save(
                _valid_user(
                    username='userb', cellphone='+51 911111111', email='b@mail.com'
                )
            )


class TestUserRepositoryExistsBy:
    async def test_exists_by_username_true_when_present(self, session):
        repository = UserRepository(session)
        await repository.save(_valid_user(username='carla01'))
        assert await repository.exists_by_username('carla01') is True

    async def test_exists_by_username_false_when_absent(self, session):
        repository = UserRepository(session)
        assert await repository.exists_by_username('nobody') is False

    async def test_exists_by_email_true_when_present(self, session):
        repository = UserRepository(session)
        await repository.save(_valid_user(email='carla@mail.com'))
        assert await repository.exists_by_email('carla@mail.com') is True

    async def test_exists_by_cellphone_true_when_present(self, session):
        repository = UserRepository(session)
        await repository.save(_valid_user(cellphone='+51 912345678'))
        assert await repository.exists_by_cellphone('+51 912345678') is True
