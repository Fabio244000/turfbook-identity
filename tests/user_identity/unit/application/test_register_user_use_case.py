from typing import Any

import pytest

from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import (
    InvalidEmailError,
    UserAlreadyExistsError,
)
from tests.fakes.user_identity import FakeHasher, FakeTokenIssuer, FakeUnitOfWork


def _valid_input(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        'first_name': 'fabio',
        'last_name': 'nunez garcia',
        'cellphone': '+51 987654321',
        'username': 'fabio01',
        'password': 'secret1234',
        'email': 'fabio@mail.com',
    }
    data.update(overrides)
    return data


def _existing_user(**overrides: Any) -> User:
    return User(**_valid_input(**overrides))


def _register_user(uow: FakeUnitOfWork) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        uow=uow, hasher=FakeHasher(), token_issuer=FakeTokenIssuer()
    )


class TestRegisterUser:
    async def test_registers_the_user_and_commits(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(**_valid_input())

        assert uow.users.users == [user]
        assert uow.committed is True

    async def test_stores_the_password_hashed(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(
            **_valid_input(password='secret1234')
        )

        assert user.password == 'hashed-secret1234'

    async def test_returns_a_session_take_for_the_registered_user(self) -> None:
        uow = FakeUnitOfWork()

        user, token = await _register_user(uow).execute(**_valid_input())

        assert token == f'token-{user.uuid}'


class TestRegisterUserUniqueness:
    async def test_rejects_a_duplicate_username_without_committing(self) -> None:
        uow = FakeUnitOfWork(
            users=[
                _existing_user(
                    username='fabio01',
                    email='other@mail.com',
                    cellphone='+51 911111111',
                )
            ]
        )

        with pytest.raises(UserAlreadyExistsError, match='username'):
            await _register_user(uow).execute(**_valid_input(username='fabio01'))

        assert uow.committed is False

    async def test_rejects_a_duplicate_email_without_committing(self) -> None:
        uow = FakeUnitOfWork(
            users=[
                _existing_user(
                    username='other01',
                    email='fabio@mail.com',
                    cellphone='+51 911111111',
                )
            ]
        )

        with pytest.raises(UserAlreadyExistsError, match='email'):
            await _register_user(uow).execute(**_valid_input(email='fabio@mail.com'))

        assert uow.committed is False

    async def test_rejects_a_duplicate_cellphone_without_committing(self) -> None:
        uow = FakeUnitOfWork(
            users=[
                _existing_user(
                    username='other01',
                    email='other@mail.com',
                    cellphone='+51 987654321',
                )
            ]
        )

        with pytest.raises(UserAlreadyExistsError, match='cellphone'):
            await _register_user(uow).execute(**_valid_input(cellphone='+51 987654321'))

        assert uow.committed is False

    async def test_invalid_data_is_rejected_before_checking_duplicates(
        self,
    ) -> None:
        uow = FakeUnitOfWork(users=[_existing_user(username='fabio01')])

        with pytest.raises(InvalidEmailError):
            await _register_user(uow).execute(
                **_valid_input(username='fabio01', email='fabio-mail.com')
            )

        assert uow.committed is False


class TestRegisterUserWithSocialToken:
    async def test_registers_without_username_or_password(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(
            **_valid_input(username=None, password=None, facebook_token='fb_111')
        )

        assert uow.users.users == [user]
        assert user.password is None

    async def test_absent_username_and_email_are_not_checked_for_uniqueness(
        self,
    ) -> None:
        uow = FakeUnitOfWork(
            users=[
                _existing_user(
                    username=None,
                    password=None,
                    email=None,
                    facebook_token='fb_111',
                    cellphone='+51 911111111',
                )
            ]
        )

        user, _ = await _register_user(uow).execute(
            **_valid_input(
                username=None, password=None, email=None, facebook_token='fb_222'
            )
        )

        assert uow.users.users[-1] == user
        assert uow.committed is True
