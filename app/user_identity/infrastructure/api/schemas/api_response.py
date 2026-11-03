from typing import Literal

from pydantic import BaseModel


class FieldError(BaseModel):
    """One failing field of a request (nested fields joined with dots)."""

    field: str
    error: str


class ApiResponse[T](BaseModel):
    success: bool = False
    message: str = ''
    detail: list[FieldError] | None = None
    data: T | None = None


class ApiErrorResponse(BaseModel):
    """The envelope of every error: `detail` only lists fields when several failed."""

    success: Literal[False] = False
    message: str
    detail: list[FieldError] | None = None
    data: None = None
