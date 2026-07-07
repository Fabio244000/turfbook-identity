from typing import Any

import pytest

from app.domain.entities.user import User
from app.domain.exceptions.user_exceptions import (
    InvalidCellphoneError,
    InvalidEmailError,
    InvalidNameError,
    InvalidPasswordError,
    InvalidUsernameError,
    MissingRequiredFieldsError,
)


def _valid_user_kwargs(**overrides: Any) -> dict[str, Any]:
    """Valid base data to build a User; overridden per case."""
    data: dict[str, Any] = {
        'username': 'fabio01',
        'password': 'secret1234',
        'first_name': 'fabio',
        'last_name': 'ñunez',
        'cellphone': '+51 987654321',
        'email': 'fabio@mail.com',
    }
    data.update(overrides)
    return data


class TestUserUsername:
    def test_valid_username_builds_user(self) -> None:
        kwargs = _valid_user_kwargs(username='fabio01')
        user = User(**kwargs)
        assert user.username == 'fabio01'

    def test_username_starting_with_number_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(username='1fabio')
        with pytest.raises(InvalidUsernameError):
            User(**kwargs)

    def test_username_with_simbols_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(username='fabio_01')
        with pytest.raises(InvalidUsernameError):
            User(**kwargs)

    def test_empty_username_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(username='')
        with pytest.raises(InvalidUsernameError):
            User(**kwargs)


class TestUserPassword:
    def test_password_shorter_than_8_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(password='secret1')
        with pytest.raises(InvalidPasswordError):
            User(**kwargs)

    def test_password_longer_than_50_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(password='a' * 51)
        with pytest.raises(InvalidPasswordError):
            User(**kwargs)

    def test_password_within_range_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(password='secret123456')
        user = User(**kwargs)
        assert user.password == 'secret123456'


class TestUserPhone:
    def test_valid_phone_builds_user(self) -> None:
        kwargs = _valid_user_kwargs(cellphone='+51 987654321')
        user = User(**kwargs)
        assert user.cellphone == '+51 987654321'

    def test_phone_without_prefix_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(cellphone='987654321')
        with pytest.raises(InvalidCellphoneError):
            User(**kwargs)

    def test_phone_with_letters_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(cellphone='+51 abc654321')
        with pytest.raises(InvalidCellphoneError):
            User(**kwargs)

    def test_phone_exceeding_length_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(cellphone='+' + '9' * 25)
        with pytest.raises(InvalidCellphoneError):
            User(**kwargs)


class TestUserEmail:
    def test_valid_email_builds_user(self) -> None:
        kwargs = _valid_user_kwargs(email='fabio@mail.com')
        user = User(**kwargs)
        assert user.email == 'fabio@mail.com'

    def test_absent_email_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(email=None)
        user = User(**kwargs)
        assert user.email is None

    def test_invalid_email_format_raises_error(self) -> None:
        kwargs = _valid_user_kwargs(email='fabio-mail.com')
        with pytest.raises(InvalidEmailError):
            User(**kwargs)


class TestUserNames:
    def test_first_name_with_numbers_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='Fabio3')
        with pytest.raises(InvalidNameError):
            User(**kwargs)

    def test_last_name_with_symbols_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(last_name='Nunez@')
        with pytest.raises(InvalidNameError):
            User(**kwargs)

    def test_alphabetic_names_are_valid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='fabio', last_name='ñunez')
        user = User(**kwargs)
        assert user.first_name == 'fabio'
        assert user.last_name == 'ñunez'

    def test_name_with_accents_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='josé', last_name='núñez carcía')
        user = User(**kwargs)
        assert user.first_name == 'josé'

    def test_compound_name_with_spaces_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(
            first_name='josé luis', last_name='de la cruz ramirez'
        )
        user = User(**kwargs)
        assert user.last_name == 'de la cruz ramirez'

    def test_name_with_leading_or_trailing_space_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='fabio ')
        with pytest.raises(InvalidNameError):
            User(**kwargs)

    def test_name_with_double_space_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='fabio  luis')
        with pytest.raises(InvalidNameError):
            User(**kwargs)


class TestUserRequiredFields:
    def test_missing_first_name_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(first_name=None)
        with pytest.raises(MissingRequiredFieldsError):
            User(**kwargs)

    def test_missing_last_name_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(last_name=None)
        with pytest.raises(MissingRequiredFieldsError):
            User(**kwargs)

    def test_missing_phone_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(cellphone=None)
        with pytest.raises(MissingRequiredFieldsError):
            User(**kwargs)


class TestUserOptionalFields:
    def test_user_without_username_and_password_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(username=None, password=None)
        user = User(**kwargs)
        assert user.username is None
        assert user.password is None

    def test_user_without_email_is_valid(self) -> None:
        kwargs = _valid_user_kwargs(email=None)
        user = User(**kwargs)
        assert user.email is None


class TestUserMaxLength:
    def test_first_name_exceeding_max_length_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(first_name='A' * 251)
        with pytest.raises(InvalidNameError):
            User(**kwargs)

    def test_last_name_exceeding_max_length_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(last_name='A' * 251)
        with pytest.raises(InvalidNameError):
            User(**kwargs)

    def test_email_exceeding_max_length_is_invalid(self) -> None:
        kwargs = _valid_user_kwargs(email='a' * 251 + '@mail.com')
        with pytest.raises(InvalidEmailError):
            User(**kwargs)
