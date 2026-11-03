import psycopg
from sqlalchemy.exc import IntegrityError

from app.user_identity.application.messages import USER_FIELD_ALREADY_EXISTS
from app.user_identity.domain.exceptions import DomainError, UserAlreadyExistsError
from app.user_identity.infrastructure.database.models import (
    USERS_CELLPHONE_KEY,
    USERS_EMAIL_KEY,
    USERS_FACEBOOK_TOKEN_KEY,
    USERS_GMAIL_TOKEN_KEY,
    USERS_USERNAME_KEY,
)

# Unique constraints whose violation means a user that already exists (a concurrent
# duplicate the use case could not see). Named in `models.py`.
DUPLICATE_USER_CONSTRAINTS = {
    USERS_USERNAME_KEY: 'username',
    USERS_CELLPHONE_KEY: 'cellphone',
    USERS_EMAIL_KEY: 'email',
    USERS_FACEBOOK_TOKEN_KEY: 'facebook_token',
    USERS_GMAIL_TOKEN_KEY: 'gmail_token',
}


def to_domain_error(error: IntegrityError) -> DomainError | None:
    """The domain meaning of a violated constraint, or None when it has none."""
    field = DUPLICATE_USER_CONSTRAINTS.get(_constraint_name(error))
    if field is None:
        return None
    return UserAlreadyExistsError(USER_FIELD_ALREADY_EXISTS.format(field=field))


def _constraint_name(error: IntegrityError) -> str:
    if isinstance(error.orig, psycopg.Error):
        return error.orig.diag.constraint_name or ''
    return ''
