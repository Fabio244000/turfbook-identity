from app.user_identity.domain.exceptions.codes import DomainErrorCode
from app.user_identity.domain.exceptions.domain_error import DomainError
from app.user_identity.domain.messages import NOTICE_NOT_PUBLISHED


class NoticeNotPublishedError(DomainError):
    """The notice could not reach notifications; it stays pending. Never reaches the
    client: the operation that raised the notice goes on. It carries its code, so the
    use cases written since 2026-11-09 recognise it by code."""

    def __init__(self) -> None:
        super().__init__(
            NOTICE_NOT_PUBLISHED, code=DomainErrorCode.NOTICE_NOT_PUBLISHED
        )
