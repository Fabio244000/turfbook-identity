from typing import Any

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    success: bool = False
    message: str = ''
    detail: dict[str, Any] | None = None
    data: T | None = None
