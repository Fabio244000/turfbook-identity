from app.user_identity.domain.exceptions.domain_error import DomainError

SESSION_EXPIRED_MESSAGE = 'Your session has expired. Please sign in again.'


class InvalidRefreshTokenError(DomainError):
    """One error for every refresh token that cannot renew a session (unknown,
    expired, revoked, reused): the client gets the same answer in every case."""

    def __init__(self) -> None:
        super().__init__(SESSION_EXPIRED_MESSAGE)
