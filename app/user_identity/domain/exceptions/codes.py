from enum import StrEnum


class DomainErrorCode(StrEnum):
    """One code per broken rule, or per failure an output port declares; the use case
    translates each into its application error."""

    ACCOUNT_CLOSED = 'account_closed'
    ACCOUNT_ALREADY_BLOCKED = 'account_already_blocked'
    ACCOUNT_NOT_BLOCKED = 'account_not_blocked'
    NOTICE_NOT_PUBLISHED = 'notice_not_published'
