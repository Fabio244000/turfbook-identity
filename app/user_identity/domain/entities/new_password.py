"""The rules of the new password of a password process. The current password only
exists as a hash: whoever holds the hasher compares it and passes the answer here."""

from app.user_identity.domain.constants import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode, ErrorCause
from app.user_identity.domain.messages import (
    CURRENT_PASSWORD_INCORRECT,
    PASSWORD_LENGTH,
    PASSWORD_TOO_SIMILAR,
    PASSWORD_UNCHANGED,
    PASSWORDS_DO_NOT_MATCH,
)


def ensure_new_password_format(password: str) -> None:
    """The rule of the registration; a format error is not a business rejection."""
    if PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        return
    code = DomainErrorCode.INVALID_NEW_PASSWORD
    cause = ErrorCause(field='new_password', code=code, message=PASSWORD_LENGTH)
    raise DomainError(PASSWORD_LENGTH, code=code, causes=(cause,))


def update_rejection(
    new_password: str,
    confirmation: str,
    current_password: str,
    current_is_right: bool,
    min_difference: int,
) -> DomainError | None:
    """The first business rule the new password of an update breaks, if any."""
    if new_password != confirmation:
        return _rejection(
            PASSWORDS_DO_NOT_MATCH, DomainErrorCode.PASSWORDS_DO_NOT_MATCH
        )
    if not current_is_right:
        return _rejection(
            CURRENT_PASSWORD_INCORRECT, DomainErrorCode.CURRENT_PASSWORD_INCORRECT
        )
    if differences(new_password, current_password) < min_difference:
        return _rejection(PASSWORD_TOO_SIMILAR, DomainErrorCode.PASSWORD_TOO_SIMILAR)
    return None


def recovery_rejection(
    new_password: str, confirmation: str, equals_current: bool
) -> DomainError | None:
    """The first business rule the new password of a recovery breaks, if any. The
    user does not know the current one, so only an equal one is rejected."""
    if new_password != confirmation:
        return _rejection(
            PASSWORDS_DO_NOT_MATCH, DomainErrorCode.PASSWORDS_DO_NOT_MATCH
        )
    if equals_current:
        return _rejection(PASSWORD_UNCHANGED, DomainErrorCode.PASSWORD_UNCHANGED)
    return None


def differences(first: str, second: str) -> int:
    """Characters added, removed or changed to go from one to the other, ignoring
    case (Levenshtein distance)."""
    first, second = first.lower(), second.lower()
    previous = list(range(len(second) + 1))
    for i, char in enumerate(first, start=1):
        current = [i]
        for j, other in enumerate(second, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (char != other),
                )
            )
        previous = current
    return previous[-1]


def _rejection(message: str, code: DomainErrorCode) -> DomainError:
    return DomainError(message, code=code)
