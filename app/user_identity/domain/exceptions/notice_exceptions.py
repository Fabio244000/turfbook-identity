from app.user_identity.domain.exceptions.domain_error import DomainError


class NoticeNotPublishedError(DomainError):
    """The notice could not reach notifications; it stays pending. Never reaches the
    client: the operation that raised the notice goes on."""
