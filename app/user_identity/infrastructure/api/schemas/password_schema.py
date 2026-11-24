from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.user_identity.domain.constants import (
    CELLPHONE_PATTERN,
    EMAIL_MAX_LENGTH,
    EMAIL_MIN_LENGTH,
    EMAIL_PATTERN,
)


class PasswordCodeRequest(BaseModel):
    """The cellphone and email that identify the account."""

    cellphone: Annotated[
        str,
        StringConstraints(strip_whitespace=True, pattern=CELLPHONE_PATTERN.pattern),
    ]
    email: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_lower=True,
            min_length=EMAIL_MIN_LENGTH,
            max_length=EMAIL_MAX_LENGTH,
            pattern=EMAIL_PATTERN.pattern,
        ),
    ]


class PasswordCodeData(BaseModel):
    """The process and when its code expires; the code only goes by email and SMS."""

    process_uuid: UUID
    code_expires_at: datetime


class PasswordDeadlineData(BaseModel):
    password_deadline: datetime


# No format for the passwords: the length of the new one is a rule of the domain, with
# the registration's message, and the current one is only compared.


class PasswordRecoveryRequest(BaseModel):
    new_password: str
    new_password_confirmation: str


class PasswordUpdateRequest(BaseModel):
    new_password: str
    new_password_confirmation: str
    current_password: str
