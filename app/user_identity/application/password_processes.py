"""Steps shared by the use cases of the password processes (update and recovery).
They work inside the caller's Unit of Work and never commit: committing stays in the
use case."""

from datetime import datetime, tzinfo
from uuid import UUID

from app.user_identity.application.exceptions import (
    ApplicationError,
    PasswordDeadlineExpiredError,
    ProcessNotAllowedError,
    ProcessNotFoundError,
)
from app.user_identity.application.security_processes import (
    application_error,
    apply_rule,
    close_if_ended,
)
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    ProcessFailureReason,
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.domain.exceptions import DomainError
from app.user_identity.domain.ports.driven.unit_of_work_port import UnitOfWorkPort


async def identified_user(uow: UnitOfWorkPort, cellphone: str, email: str) -> User:
    """The account of that cellphone and email, locked until the commit; any other
    case answers the same, so nobody learns which data failed."""
    user = await uow.users.get_by_cellphone_for_update(cellphone)
    if user is None or not user.is_identified_by(cellphone, email):
        raise ProcessNotAllowedError()
    apply_rule(user.ensure_can_change_password)
    return user


async def owned_process(
    uow: UnitOfWorkPort,
    user: User | None,
    process_uuid: UUID,
    type: SecurityProcessType,
    now: datetime,
    zone: tzinfo,
) -> tuple[User, SecurityProcess]:
    """The active user and its process of that type and of today, locked after the
    user (the same order as a code request); any other is not found, so nobody
    learns that it exists."""
    process = await uow.security_processes.get_by_uuid_for_update(process_uuid)
    if (
        user is None
        or user.status is not AccountStatus.ACTIVE
        or process is None
        or process.user_uuid != user.uuid
        or process.type is not type
        or not process.is_of_day(now, zone)
    ):
        raise ProcessNotFoundError()
    return user, process


async def ended_process_error(
    uow: UnitOfWorkPort,
    process: SecurityProcess,
    now: datetime,
    zone: tzinfo,
    rules: SecurityCodeRules,
) -> ApplicationError | None:
    """Closes the process if its life ended; the error the caller raises once it
    committed: the deadline that just failed it, or a process no longer open."""
    if not await close_if_ended(uow, process, now, zone, rules):
        return None
    if process.failure_reason is ProcessFailureReason.DEADLINE:
        return PasswordDeadlineExpiredError()
    return ProcessNotFoundError()


async def rejected_password(
    uow: UnitOfWorkPort,
    process: SecurityProcess,
    rejection: DomainError,
    now: datetime,
    rules: PasswordProcessRules,
) -> ApplicationError:
    """Counts the rejection in the stored process; the error the caller raises once it
    committed."""
    try:
        process.reject_password(rejection, now, rules)
    except DomainError as error:
        await uow.security_processes.update(process)
        return application_error(error)


async def save_new_password(
    uow: UnitOfWorkPort,
    user: User,
    process: SecurityProcess,
    password_hash: str,
    event: AccountEvent,
) -> None:
    """The new password, the process completed and the event that records it."""
    user.change_password(password_hash, event.created_at)
    process.complete(event.created_at)
    await uow.users.update(user)
    await uow.security_processes.update(process)
    await uow.account_events.add(event)
