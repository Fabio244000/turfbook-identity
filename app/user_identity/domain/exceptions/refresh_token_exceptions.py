from app.user_identity.domain.exceptions.domain_error import DomainError
from app.user_identity.domain.messages import SESSION_EXPIRED


class InvalidRefreshTokenError(DomainError):
    """One error for every refresh token that cannot renew a session (unknown,
    expired, revoked, reused): the client gets the same answer in every case."""

    def __init__(self) -> None:
        super().__init__(SESSION_EXPIRED)
