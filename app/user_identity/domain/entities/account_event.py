from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4


class AccountEventType(StrEnum):
    BLOCKED = 'blocked'
    UNBLOCKED = 'unblocked'
    CLOSED = 'closed'


class AccountEventReason(StrEnum):
    FAILED_ATTEMPTS = 'failed_attempts'
    TURFBOOK = 'turfbook'
    INACTIVITY_7_DAYS = 'inactivity_7_days'


class AccountEventActor(StrEnum):
    SYSTEM = 'system'
    TURFBOOK = 'turfbook'


@dataclass
class AccountEvent:
    """Something that happened to an account. When it is told to the user, it keeps
    the notice's id and when the notice was published (empty while pending)."""

    user_uuid: UUID
    type: AccountEventType
    reason: AccountEventReason
    actor: AccountEventActor
    created_at: datetime
    notice_id: UUID | None = None
    notice_published_at: datetime | None = None
    uuid: UUID = field(default_factory=uuid4)

    @classmethod
    def blocked_for_failed_attempts(cls, user_uuid: UUID, now: datetime) -> Self:
        return cls(
            user_uuid=user_uuid,
            type=AccountEventType.BLOCKED,
            reason=AccountEventReason.FAILED_ATTEMPTS,
            actor=AccountEventActor.SYSTEM,
            created_at=now,
            notice_id=uuid4(),
        )

    def mark_notice_published(self, now: datetime) -> None:
        self.notice_published_at = now
