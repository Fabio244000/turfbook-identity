import psycopg
from sqlalchemy.exc import IntegrityError

from app.user_identity.domain.exceptions import DomainError, UserAlreadyExistsError

# Unique constraints whose violation means a user that already exists (a concurrent
# duplicate the use case could not see). Names as PostgreSQL creates them.
DUPLICATE_USER_CONSTRAINTS = {
    'users_username_key': 'username',
    'users_cellphone_key': 'cellphone',
    'users_email_key': 'email',
    'users_facebook_token_key': 'facebook_token',
    'users_gmail_token_key': 'gmail_token',
}


def to_domain_error(error: IntegrityError) -> DomainError | None:
    """The domain meaning of a violated constraint, or None when it has none."""
    field = DUPLICATE_USER_CONSTRAINTS.get(_constraint_name(error))
    if field is None:
        return None
    return UserAlreadyExistsError(f'A user with this {field} already exists.')


def _constraint_name(error: IntegrityError) -> str:
    if isinstance(error.orig, psycopg.Error):
        return error.orig.diag.constraint_name or ''
    return ''
