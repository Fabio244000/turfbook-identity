from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.exceptions.domain_error import DomainError
from app.user_identity.domain.messages import ACCOUNT_BLOCKED, INVALID_CREDENTIALS


class InvalidCredentialsError(DomainError):
    """One error for every sign-in that does not open a session, whatever failed, so
    nobody learns which usernames exist."""

    def __init__(self) -> None:
        super().__init__(INVALID_CREDENTIALS)


class AccountBlockedError(DomainError):
    def __init__(self, contact: TurfBookContact) -> None:
        super().__init__(
            ACCOUNT_BLOCKED.format(phone=contact.phone, email=contact.email)
        )
