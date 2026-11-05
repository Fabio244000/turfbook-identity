from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Notifier(StrEnum):
    EMAIL = 'email'
    SMS = 'sms'


@dataclass(frozen=True)
class NoticeRecipient:
    uuid: UUID
    email: str | None
    cellphone: str
    first_name: str


@dataclass(frozen=True)
class Notice:
    """An order to notify a user through notifications; `notice_id` is the same on
    every publication of the notice."""

    notice_id: UUID
    notifiers: tuple[Notifier, ...]
    recipient: NoticeRecipient
    subject: str
    body: str
