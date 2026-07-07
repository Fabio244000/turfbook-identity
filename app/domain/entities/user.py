from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.constants import (
    CELLPHONE_PATTERN,
    EMAIL_PATTERN,
    MAX_LENGTH,
    MAX_USERNAME_LENGTH,
    NAME_PATTERN,
    PASSWORD_PATTERN,
    USERNAME_PATTERN,
)
from app.domain.exceptions import (
    InvalidCellphoneError,
    InvalidEmailError,
    InvalidNameError,
    InvalidPasswordError,
    InvalidUsernameError,
    MissingRequiredFieldsError,
)


@dataclass
class User:
    first_name: str
    last_name: str
    cellphone: str
    username: str | None
    password: str | None
    email: str | None
    facebook_token: str | None = field(default=None)
    gmail_token: str | None = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    uuid: UUID = field(default_factory=uuid4)

    def _validate_cellphone(self, cellphone: str) -> None:
        if not CELLPHONE_PATTERN.match(cellphone):
            raise InvalidCellphoneError('cellphone format is invalid.')

    def _validate_username(self, username: str | None) -> None:
        if username is None:
            return
        if not USERNAME_PATTERN.match(username):
            raise InvalidUsernameError(
                'username is invalid, should only contain letters and numbers.'
            )
        if len(username) > MAX_USERNAME_LENGTH:
            raise InvalidUsernameError('username is too long.')

    def _validate_password(self, password: str | None) -> None:
        if password is None:
            return
        if not PASSWORD_PATTERN.match(password):
            raise InvalidPasswordError('password is invalid.')

    def _validate_email(self, email: str | None) -> None:
        if email is None:
            return
        if not EMAIL_PATTERN.match(email):
            raise InvalidEmailError('email is invalid.')
        self._validate_max_length(self.email, 'email', InvalidEmailError)

    def _validate_max_length(
        self, value: str | None, field_name: str, exception: type[Exception]
    ) -> None:
        if value is not None and len(value) > MAX_LENGTH:
            raise exception(f'{field_name} exceeds maximum length of {MAX_LENGTH}.')

    def _validate_required_field(self, field_name: str, value: str) -> None:
        if value is None:
            raise MissingRequiredFieldsError(f'{field_name} is required.')

    def _validate_name(self, field_name: str, value: str) -> None:
        if not NAME_PATTERN.match(value):
            raise InvalidNameError(f'{field_name} is invalid.')

    def __post_init__(self) -> None:
        self._validate_required_field('first_name', self.first_name)
        self._validate_required_field('last_name', self.last_name)
        self._validate_required_field('cellphone', self.cellphone)
        self._validate_name('first_name', self.first_name)
        self._validate_name('last_name', self.last_name)
        self._validate_max_length(self.first_name, 'first_name', InvalidNameError)
        self._validate_max_length(self.last_name, 'last_name', InvalidNameError)
        self._validate_username(username=self.username)
        self._validate_password(password=self.password)
        self._validate_cellphone(cellphone=self.cellphone)
        self._validate_email(email=self.email)
