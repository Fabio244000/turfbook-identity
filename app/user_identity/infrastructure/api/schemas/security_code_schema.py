from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.user_identity.domain.constants import CELLPHONE_PATTERN

SECURITY_CODE_PATTERN = r'^[0-9]{6}$'


class ProcessTypeOption(StrEnum):
    EMAIL_VERIFICATION = 'email_verification'
    PASSWORD_UPDATE = 'password_update'
    PASSWORD_RECOVERY = 'password_recovery'


class EmailVerificationData(BaseModel):
    """The process and when its code expires; the code only goes to the email."""

    process_uuid: UUID
    code_expires_at: datetime


class CodeValidationRequest(BaseModel):
    code: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=SECURITY_CODE_PATTERN)
    ]


class SupportSecurityCodeRequest(BaseModel):
    cellphone: Annotated[
        str,
        StringConstraints(strip_whitespace=True, pattern=CELLPHONE_PATTERN.pattern),
    ]
    process_type: ProcessTypeOption


class SupportSecurityCodeData(BaseModel):
    process_uuid: UUID
    code: str
    code_expires_at: datetime
