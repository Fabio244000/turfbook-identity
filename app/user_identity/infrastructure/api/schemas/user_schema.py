from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.user_identity.infrastructure.api.schemas.token_schema import (
    SessionTokensData,
)


class BaseUserSchema(BaseModel):
    first_name: str
    last_name: str
    cellphone: str
    username: str | None = None
    email: str | None = None


class UserRequest(BaseUserSchema):
    """Datos para registrar a un usuario en el Sistema"""

    password: str | None = None


class UserResponse(BaseUserSchema):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    created_at: datetime
    updated_at: datetime


class RegisterUserData(SessionTokensData):
    """The registered user and the session it starts."""

    user: UserResponse
