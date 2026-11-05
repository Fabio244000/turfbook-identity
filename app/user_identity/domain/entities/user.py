from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from app.user_identity.domain.constants import (
    CELLPHONE_LENGTH,
    CELLPHONE_PATTERN,
    EMAIL_MAX_LENGTH,
    EMAIL_MIN_LENGTH,
    EMAIL_PATTERN,
    MAX_LENGTH,
    MAX_USERNAME_LENGTH,
    NAME_PATTERN,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_PATTERN,
)
from app.user_identity.domain.exceptions import (
    InvalidCellphoneError,
    InvalidEmailError,
    InvalidFieldError,
    InvalidNameError,
    InvalidPasswordError,
    InvalidUserError,
    InvalidUsernameError,
    MissingRequiredFieldsError,
)
from app.user_identity.domain.messages import (
    CELLPHONE_INVALID,
    EMAIL_INVALID,
    EMAIL_REQUIRED,
    FIELD_REQUIRED,
    IDENTIFIER_REQUIRED,
    NAME_INVALID,
    NAME_TOO_LONG,
    PASSWORD_LENGTH,
    USERNAME_INVALID,
    USERNAME_TOO_LONG,
)


class AccountStatus(StrEnum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    CLOSED = 'closed'


@dataclass
class User:
    first_name: str
    last_name: str
    cellphone: str
    username: str | None
    password: str | None
    email: str | None
    created_at: datetime
    updated_at: datetime
    facebook_token: str | None = field(default=None)
    gmail_token: str | None = field(default=None)
    status: AccountStatus = AccountStatus.ACTIVE
    # Consecutive failed sign-ins of the business day `last_failed_attempt_on`.
    failed_attempts: int = 0
    last_failed_attempt_on: date | None = None
    blocked_at: datetime | None = None
    closed_at: datetime | None = None
    uuid: UUID = field(default_factory=uuid4)

    @classmethod
    def register(
        cls,
        first_name: str,
        last_name: str,
        cellphone: str,
        username: str | None,
        password: str | None,
        email: str | None,
        now: datetime,
        facebook_token: str | None = None,
        gmail_token: str | None = None,
    ) -> Self:
        """A new user from its registration input; only here are input rules applied,
        so a user rebuilt from stored data (a hashed password) is never re-validated."""
        _ensure_identifier(username, password, facebook_token, gmail_token)
        _ensure_required(
            first_name=first_name, last_name=last_name, cellphone=cellphone
        )
        user = cls(
            first_name=first_name,
            last_name=last_name,
            cellphone=cellphone.strip(),
            username=username,
            password=password,
            email=email.strip().lower() if email is not None else None,
            created_at=now,
            updated_at=now,
            facebook_token=facebook_token,
            gmail_token=gmail_token,
        )
        errors = user._rule_errors()
        if errors:
            raise InvalidUserError(errors)
        return user

    def record_failed_attempt(self, today: date, now: datetime, limit: int) -> None:
        """`today` is the business day of `now`: the attempts of another day are not
        consecutive, so they start again from zero."""
        if self.last_failed_attempt_on != today:
            self.failed_attempts = 0
        self.failed_attempts += 1
        self.last_failed_attempt_on = today
        if self.failed_attempts >= limit:
            self.status = AccountStatus.BLOCKED
            self.blocked_at = now

    def record_sign_in(self) -> None:
        self.failed_attempts = 0

    def _rule_errors(self) -> list[InvalidFieldError]:
        """Every failing field at once, so the client fixes them in one go."""
        checks = (
            _name_error('first_name', self.first_name),
            _name_error('last_name', self.last_name),
            _username_error(self.username),
            _password_error(self.password),
            _cellphone_error(self.cellphone),
            _email_error(self.email),
        )
        return [error for error in checks if error is not None]


def _ensure_identifier(
    username: str | None,
    password: str | None,
    facebook_token: str | None,
    gmail_token: str | None,
) -> None:
    if not (facebook_token or gmail_token) and not (username and password):
        raise MissingRequiredFieldsError(IDENTIFIER_REQUIRED)


def _ensure_required(**values: str | None) -> None:
    for name, value in values.items():
        if value is None:
            raise MissingRequiredFieldsError(FIELD_REQUIRED.format(field=name))


def _name_error(name: str, value: str) -> InvalidFieldError | None:
    if len(value) > MAX_LENGTH:
        return InvalidNameError(
            NAME_TOO_LONG.format(field=name, max_length=MAX_LENGTH), name
        )
    if not NAME_PATTERN.match(value):
        return InvalidNameError(NAME_INVALID.format(field=name), name)
    return None


def _username_error(username: str | None) -> InvalidFieldError | None:
    if username is None:
        return None
    if len(username) > MAX_USERNAME_LENGTH:
        return InvalidUsernameError(USERNAME_TOO_LONG, 'username')
    if not USERNAME_PATTERN.match(username):
        return InvalidUsernameError(USERNAME_INVALID, 'username')
    return None


def _password_error(password: str | None) -> InvalidFieldError | None:
    if password is None:
        return None
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        return InvalidPasswordError(PASSWORD_LENGTH, 'password')
    return None


def _cellphone_error(cellphone: str) -> InvalidFieldError | None:
    if len(cellphone) != CELLPHONE_LENGTH or not CELLPHONE_PATTERN.match(cellphone):
        return InvalidCellphoneError(CELLPHONE_INVALID, 'cellphone')
    return None


def _email_error(email: str | None) -> InvalidFieldError | None:
    if not email:
        return InvalidEmailError(EMAIL_REQUIRED, 'email')
    if not EMAIL_MIN_LENGTH <= len(email) <= EMAIL_MAX_LENGTH:
        return InvalidEmailError(EMAIL_INVALID, 'email')
    if not EMAIL_PATTERN.match(email):
        return InvalidEmailError(EMAIL_INVALID, 'email')
    return None
