from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import (
    InvalidCellphoneError,
    InvalidEmailError,
    InvalidNameError,
    InvalidPasswordError,
    InvalidUsernameError,
    MissingRequiredFieldsError,
    UserAlreadyExistsError,
)
from tests.fakes.user_identity import (
    FakeClock,
    FakeHasher,
    FakeRefreshTokenGenerator,
    FakeTokenIssuer,
    FakeUnitOfWork,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
REFRESH_TOKEN_TTL = timedelta(days=7)


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
    return User(**_valid_input(**overrides), created_at=NOW, updated_at=NOW)


def _register_user(uow: FakeUnitOfWork) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        uow=uow,
        hasher=FakeHasher(),
        token_issuer=FakeTokenIssuer(),
        clock=FakeClock(NOW),
        refresh_token_generator=FakeRefreshTokenGenerator(),
        refresh_token_ttl=REFRESH_TOKEN_TTL,
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

    async def test_returns_an_access_token_for_the_registered_user(self) -> None:
        uow = FakeUnitOfWork()

        user, tokens = await _register_user(uow).execute(**_valid_input())

        assert tokens.access_token == f'token-{user.uuid}'


class TestRegisterUserSession:
    async def test_returns_a_refresh_token_that_starts_a_session(self) -> None:
        uow = FakeUnitOfWork()

        _, tokens = await _register_user(uow).execute(**_valid_input())

        assert tokens.refresh_token == 'refresh-1'

    async def test_stores_only_the_hash_of_the_refresh_token(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(**_valid_input())

        stored = uow.refresh_tokens.stored('hash-refresh-1')
        assert stored.user_uuid == user.uuid
        assert stored.expires_at == NOW + REFRESH_TOKEN_TTL
        assert all(
            token.token_hash != 'refresh-1' for token in uow.refresh_tokens.tokens
        )

    async def test_issues_no_refresh_token_when_registration_fails(self) -> None:
        uow = FakeUnitOfWork(users=[_existing_user(username='fabio01')])

        with pytest.raises(UserAlreadyExistsError):
            await _register_user(uow).execute(**_valid_input(username='fabio01'))

        assert uow.refresh_tokens.tokens == []


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


class TestRegisterUserRequiredData:
    @pytest.mark.parametrize('field', ['first_name', 'last_name', 'cellphone'])
    async def test_rejects_a_missing_required_field(self, field: str) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(MissingRequiredFieldsError, match=f'{field} is required'):
            await _register_user(uow).execute(**_valid_input(**{field: None}))

    async def test_rejects_without_credentials_or_social_token(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(MissingRequiredFieldsError, match='must provide'):
            await _register_user(uow).execute(
                **_valid_input(username=None, password=None)
            )

    async def test_rejects_a_username_without_password(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(MissingRequiredFieldsError, match='must provide'):
            await _register_user(uow).execute(**_valid_input(password=None))

    async def test_registers_without_email(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(**_valid_input(email=None))

        assert uow.users.users == [user]


class TestRegisterUserUsername:
    @pytest.mark.parametrize(
        'username', ['1fabio', 'fabio_01', 'Fabio01'], ids=['digit', 'symbol', 'upper']
    )
    async def test_rejects_a_username_that_is_not_lowercase_letters_and_digits(
        self, username: str
    ) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidUsernameError, match='only contain'):
            await _register_user(uow).execute(**_valid_input(username=username))

    async def test_rejects_an_empty_username_even_with_a_social_token(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidUsernameError, match='only contain'):
            await _register_user(uow).execute(
                **_valid_input(username='', facebook_token='fb_111')
            )

    async def test_rejects_a_username_longer_than_50(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidUsernameError, match='too long'):
            await _register_user(uow).execute(**_valid_input(username='a' * 51))


class TestRegisterUserPassword:
    @pytest.mark.parametrize(
        'password', ['secret1', 'a' * 51], ids=['shorter_than_8', 'longer_than_50']
    )
    async def test_rejects_a_password_out_of_range(self, password: str) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidPasswordError):
            await _register_user(uow).execute(**_valid_input(password=password))


class TestRegisterUserCellphone:
    @pytest.mark.parametrize(
        'cellphone',
        ['987654321', '+51 abc654321', '+51 9876543210'],
        ids=['without_prefix', 'with_letters', 'more_than_9_digits'],
    )
    async def test_rejects_a_cellphone_that_is_not_a_peruvian_mobile(
        self, cellphone: str
    ) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidCellphoneError):
            await _register_user(uow).execute(**_valid_input(cellphone=cellphone))


class TestRegisterUserEmail:
    async def test_rejects_an_invalid_email(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidEmailError, match='is invalid'):
            await _register_user(uow).execute(**_valid_input(email='fabio-mail.com'))

    async def test_rejects_an_email_longer_than_250(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidEmailError, match='exceeds maximum length'):
            await _register_user(uow).execute(
                **_valid_input(email='a' * 251 + '@mail.com')
            )


class TestRegisterUserNames:
    async def test_rejects_a_first_name_with_digits(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidNameError, match='first_name is invalid'):
            await _register_user(uow).execute(**_valid_input(first_name='fabio3'))

    async def test_rejects_a_last_name_with_symbols(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidNameError, match='last_name is invalid'):
            await _register_user(uow).execute(**_valid_input(last_name='nunez@'))

    @pytest.mark.parametrize(
        'first_name', ['fabio ', 'fabio  luis'], ids=['edge_space', 'double_space']
    )
    async def test_rejects_badly_placed_spaces(self, first_name: str) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidNameError, match='first_name is invalid'):
            await _register_user(uow).execute(**_valid_input(first_name=first_name))

    @pytest.mark.parametrize('field', ['first_name', 'last_name'])
    async def test_rejects_a_name_longer_than_250(self, field: str) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(InvalidNameError, match='exceeds maximum length'):
            await _register_user(uow).execute(**_valid_input(**{field: 'a' * 251}))

    async def test_accepts_accents_and_compound_names(self) -> None:
        uow = FakeUnitOfWork()

        user, _ = await _register_user(uow).execute(
            **_valid_input(first_name='josé luis', last_name='de la cruz núñez')
        )

        assert (user.first_name, user.last_name) == ('josé luis', 'de la cruz núñez')
