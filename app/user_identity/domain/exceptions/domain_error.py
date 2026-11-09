from dataclasses import dataclass

from app.user_identity.domain.exceptions.codes import DomainErrorCode


@dataclass(frozen=True)
class ErrorCause:
    """One broken rule of a field, when several break at once."""

    field: str
    code: DomainErrorCode
    message: str


class DomainError(Exception):
    """The one error type of the domain: the code and the message of the broken rule,
    and its causes when several break at once. The code goes by name, so the
    subclasses written before 2026-11-09 (which pass only a message) keep working."""

    def __init__(
        self,
        message: str = '',
        *,
        code: DomainErrorCode | None = None,
        causes: tuple[ErrorCause, ...] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.causes = causes
