from typing import Any
from unittest.mock import Mock

import pytest

from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.entities.user import User
from app.domain.exceptions import UserAlreadyExistsError
from app.domain.ports.output.password_hasher_port import PasswordHasherPort
from app.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.domain.ports.output.user_repository_port import UserRepositoryPort


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


@pytest.fixture
def repository() -> UserRepositoryPort:
    repo = Mock(spec=UserRepositoryPort)
    repo.exists_by_username.return_value = False
    repo.exists_by_email.return_value = False
    repo.exists_by_cellphone.return_value = False
    repo.save.side_effect = lambda user: user
    return repo


@pytest.fixture
def hasher() -> PasswordHasherPort:
    hasher = Mock(spec=PasswordHasherPort)
    hasher.hash.return_value = 'hashed'
    return hasher


@pytest.fixture
def token_issuer() -> TokenIssuerPort:
    issuer = Mock(spec=TokenIssuerPort)
    issuer.issue.return_value = 'session_token'
    return issuer


@pytest.fixture
def use_case(
    repository: UserRepositoryPort,
    hasher: PasswordHasherPort,
    token_issuer: TokenIssuerPort,
) -> RegisterUserUseCase:
    return RegisterUserUseCase(repository, hasher, token_issuer)


class TestRegisterUserSuccess:
    async def test_returns_user_and_token(self, use_case: RegisterUserUseCase) -> None:
        user, token = await use_case.execute(**_valid_input())
        assert isinstance(user, User)
        assert token == 'session_token'

    async def test_password_is_hashed_not_plain(
        self, use_case: RegisterUserUseCase, hasher: PasswordHasherPort
    ) -> None:
        user, _ = await use_case.execute(**_valid_input())
        hasher.hash.assert_called_once_with('secret1234')
        assert user.password == 'hashed'

    async def test_user_is_persisted(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        await use_case.execute(**_valid_input())
        repository.save.assert_called_once()

    async def test_token_is_issued(
        self, use_case: RegisterUserUseCase, token_issuer: TokenIssuerPort
    ) -> None:
        await use_case.execute(**_valid_input())
        token_issuer.issue.assert_called_once()


class TestRegisterUserUniqueness:
    async def test_duplicate_username_raises(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        repository.exists_by_username.return_value = True
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(**_valid_input())

    async def test_duplicate_email_raises(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        repository.exists_by_email.return_value = True
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(**_valid_input())

    async def test_duplicate_cellphone_raises(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        repository.exists_by_cellphone.return_value = True
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(**_valid_input())

    async def test_does_not_persist_when_duplicate(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        repository.exists_by_username.return_value = True
        with pytest.raises(UserAlreadyExistsError):
            await use_case.execute(**_valid_input())
        repository.save.assert_not_called()


class TestRegisterUserOptionalFields:
    async def test_registers_without_username(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        user, token = await use_case.execute(
            **_valid_input(username=None, password=None)
        )
        assert user.username is None

    async def test_skips_username_uniqueness_when_absent(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        await use_case.execute(**_valid_input(username=None, password=None))
        repository.exists_by_username.assert_not_called()

    async def test_skips_email_uniqueness_when_absent(
        self, use_case: RegisterUserUseCase, repository: UserRepositoryPort
    ) -> None:
        await use_case.execute(**_valid_input(email=None))
        repository.exists_by_email.assert_not_called()
