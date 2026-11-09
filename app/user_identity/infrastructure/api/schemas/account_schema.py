from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class AccountOperation(StrEnum):
    BLOCK = 'block'
    UNBLOCK = 'unblock'


class AccountStatusRequest(BaseModel):
    operation: AccountOperation


class AccountStatusData(BaseModel):
    user_uuid: UUID
    status: str
    changed_at: datetime
