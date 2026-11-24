"""Steps shared by the use cases of the security processes. They work inside the
caller's Unit of Work and never commit: committing stays in the use case."""

from collections.abc import Awaitable, Callable
from datetime import datetime, tzinfo
from functools import partial
from typing import NoReturn
from uuid import UUID

from app.user_identity.application.exceptions import (
    ApplicationError,
    EmailAlreadyVerifiedError,
    InvalidNewPasswordError,
    PasswordAttemptsExceededError,
    PasswordRejectedError,
    PasswordUpdateIntervalError,
    ProcessFailedError,
    ProcessNotAllowedError,
    ProcessNotFoundError,
    SecurityCodeAlreadyValidatedError,
    SecurityCodeDeliveredError,
    SecurityCodeExhaustedError,
    SecurityCodeExpiredError,
    SecurityCodeIncorrectError,
    SecurityCodeLimitError,
    SecurityCodeNotValidatedError,
    SupportCodeLimitError,
)
from app.user_identity.domain.entities.notice import Notice
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    SecurityCode,
    SecurityProcess,
    SecurityProcessType,
    start_of_day,
)
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
from app.user_identity.domain.ports.driven.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.driven.security_code_generator_port import (
    SecurityCodeGeneratorPort,
)
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
    DomainErrorCode.SECURITY_CODE_ALREADY_VALIDATED: SecurityCodeAlreadyValidatedError,
    DomainErrorCode.PASSWORD_UPDATE_INTERVAL: PasswordUpdateIntervalError,
    DomainErrorCode.SECURITY_CODE_NOT_VALIDATED: SecurityCodeNotValidatedError,
    DomainErrorCode.INVALID_NEW_PASSWORD: InvalidNewPasswordError,
    DomainErrorCode.PASSWORDS_DO_NOT_MATCH: PasswordRejectedError,
    DomainErrorCode.CURRENT_PASSWORD_INCORRECT: PasswordRejectedError,
    DomainErrorCode.PASSWORD_TOO_SIMILAR: PasswordRejectedError,
    DomainErrorCode.PASSWORD_UNCHANGED: PasswordRejectedError,
    DomainErrorCode.PASSWORD_ATTEMPTS_EXCEEDED: PasswordAttemptsExceededError,
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
    raise application_error(error) from error


def application_error(error: DomainError) -> ApplicationError:
    """The application error of a broken rule, with its causes by field; any other
    error passes through."""
    error_type = _APPLICATION_ERRORS.get(error.code)
    if error_type is None:
        raise error
    if error.causes:
        causes = tuple((cause.field, cause.message) for cause in error.causes)
        return error_type(error.message, causes)
    return error_type(error.message)


async def close_if_ended(
    uow: UnitOfWorkPort,
    process: SecurityProcess,
    now: datetime,
    zone: tzinfo,
    rules: SecurityCodeRules,
) -> bool:
    """Stores the close of a process whose life ended; says whether it closed it."""
    if not process.close_if_ended(now, zone, rules):
        return False
    await uow.security_processes.update(process)
    return True


async def open_process(
    uow: UnitOfWorkPort,
    user_uuid: UUID,
    type: SecurityProcessType,
    now: datetime,
    zone: tzinfo,
    rules: SecurityCodeRules,
) -> SecurityProcess | None:
    """The user's open process of that type, locked; one whose life ended is closed
    and never goes on."""
    process = await uow.security_processes.get_open_for_update(user_uuid, type)
    if process is None or await close_if_ended(uow, process, now, zone, rules):
        return None
    return process


async def issue_code(
    uow: UnitOfWorkPort,
    generator: SecurityCodeGeneratorPort,
    user_uuid: UUID,
    type: SecurityProcessType,
    now: datetime,
    zone: tzinfo,
    rules: SecurityCodeRules,
    start: Callable[[bool], Awaitable[SecurityProcess]],
) -> tuple[SecurityProcess, SecurityCode]:
    """A pending code in the user's open process, or in a new one that `start` opens
    (it receives whether a process of that type failed today)."""
    process = await open_process(uow, user_uuid, type, now, zone, rules)
    is_new = process is None
    if process is None:
        failed_today = await uow.security_processes.has_failed_since(
            user_uuid, type, start_of_day(now, zone)
        )
        process = await start(failed_today)
    code = apply_rule(
        partial(process.issue_user_code, generator.generate(), now, rules)
    )
    if is_new:
        await uow.security_processes.add(process)
    else:
        await uow.security_processes.update(process)
    return process, code


async def publish_code(publisher: NoticePublisherPort, notice: Notice) -> bool:
    """Publishes the notice with the code, once the pending code was committed; says
    whether it went out."""
    try:
        await publisher.publish(notice)
    except DomainError as error:
        if error.code is not DomainErrorCode.NOTICE_NOT_PUBLISHED:
            raise
        return False
    return True


async def settle_code(
    uow: UnitOfWorkPort, process_uuid: UUID, code_uuid: UUID, sent: bool
) -> None:
    """Sent, the code becomes the active one; not sent, it is deleted, so it never
    counts (and a new process without codes goes with it)."""
    repository = uow.security_processes
    process = await repository.get_by_uuid_for_update(process_uuid)
    if process is None:
        raise ProcessNotFoundError()
    if sent:
        process.activate_code(code_uuid)
    else:
        process.discard_code(code_uuid)
    if process.has_codes:
        await repository.update(process)
    else:
        await repository.delete(process.uuid)


async def validate_code(
    uow: UnitOfWorkPort,
    process: SecurityProcess,
    code: str,
    now: datetime,
    rules: SecurityCodeRules,
) -> ApplicationError | None:
    """Validates the code and stores the outcome, also a rejected attempt, so it
    counts; returns the error the caller raises once it committed."""
    try:
        process.validate(code, now, rules)
    except DomainError as error:
        await uow.security_processes.update(process)
        return application_error(error)
    await uow.security_processes.update(process)
    return None
