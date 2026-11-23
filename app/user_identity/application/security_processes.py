"""Steps shared by the use cases of the security processes. They work inside the
caller's Unit of Work and never commit: committing stays in the use case."""

from collections.abc import Callable
from datetime import datetime, tzinfo
from typing import NoReturn
from uuid import UUID

from app.user_identity.application.exceptions import (
    ApplicationError,
    EmailAlreadyVerifiedError,
    GracePeriodEndedError,
    ProcessFailedError,
    ProcessNotAllowedError,
    ProcessNotFoundError,
    SecurityCodeDeliveredError,
    SecurityCodeExhaustedError,
    SecurityCodeExpiredError,
    SecurityCodeIncorrectError,
    SecurityCodeLimitError,
    SupportCodeLimitError,
)
from app.user_identity.domain.entities.security_process import (
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort

_APPLICATION_ERRORS: dict[DomainErrorCode | None, type[ApplicationError]] = {
    DomainErrorCode.PROCESS_NOT_ALLOWED: ProcessNotAllowedError,
    DomainErrorCode.EMAIL_ALREADY_VERIFIED: EmailAlreadyVerifiedError,
    DomainErrorCode.SECURITY_CODE_LIMIT: SecurityCodeLimitError,
    DomainErrorCode.PROCESS_FAILED: ProcessFailedError,
    DomainErrorCode.PROCESS_NOT_IN_PROGRESS: ProcessNotFoundError,
    DomainErrorCode.SECURITY_CODE_INCORRECT: SecurityCodeIncorrectError,
    DomainErrorCode.SECURITY_CODE_EXPIRED: SecurityCodeExpiredError,
    DomainErrorCode.SECURITY_CODE_EXHAUSTED: SecurityCodeExhaustedError,
    DomainErrorCode.SUPPORT_CODE_LIMIT: SupportCodeLimitError,
    DomainErrorCode.SECURITY_CODE_DELIVERED: SecurityCodeDeliveredError,
    DomainErrorCode.GRACE_PERIOD_ENDED: GracePeriodEndedError,
}


def apply_rule[T](step: Callable[[], T]) -> T:
    """Runs a step of the domain; a broken rule becomes its application error."""
    try:
        return step()
    except DomainError as error:
        raise_application_error(error)


def raise_application_error(error: DomainError) -> NoReturn:
    """The application error its caller presents for a broken rule, by its code; any
    other error passes through."""
    application_error = _APPLICATION_ERRORS.get(error.code)
    if application_error is None:
        raise error
    raise application_error(error.message) from error


async def open_process_of_day(
    uow: UnitOfWorkPort,
    user_uuid: UUID,
    type: SecurityProcessType,
    now: datetime,
    zone: tzinfo,
) -> SecurityProcess | None:
    """The user's open process of that type, locked; one left open from a previous
    day is closed as incomplete and never goes on."""
    process = await uow.security_processes.get_open_for_update(user_uuid, type)
    if process is not None and process.close_if_day_ended(now, zone):
        await uow.security_processes.update(process)
        return None
    return process
