"""Steps shared by the use cases that change an account. They work inside the caller's
Unit of Work and never commit: committing stays in the use case."""

from collections.abc import Callable
from uuid import UUID

from app.user_identity.application.exceptions import (
    AccountAlreadyBlockedError,
    AccountClosedError,
    AccountNotBlockedError,
    AccountNotFoundError,
    ApplicationError,
)
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort

# What a caller is told when the domain rejects a change of the account.
_APPLICATION_ERRORS: dict[DomainErrorCode | None, type[ApplicationError]] = {
    DomainErrorCode.ACCOUNT_CLOSED: AccountClosedError,
    DomainErrorCode.ACCOUNT_ALREADY_BLOCKED: AccountAlreadyBlockedError,
    DomainErrorCode.ACCOUNT_NOT_BLOCKED: AccountNotBlockedError,
}


async def account_for_update(uow: UnitOfWorkPort, user_uuid: UUID) -> User:
    user = await uow.users.get_by_uuid_for_update(user_uuid)
    if user is None:
        raise AccountNotFoundError()
    return user


def change_account(change: Callable[[], None]) -> None:
    """Runs a change of the account and translates a broken rule, by its code, into
    the application error its caller presents; any other error passes through."""
    try:
        change()
    except DomainError as error:
        application_error = _APPLICATION_ERRORS.get(error.code)
        if application_error is None:
            raise
        raise application_error(error.message) from error
