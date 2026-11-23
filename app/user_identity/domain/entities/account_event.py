from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4


class AccountEventType(StrEnum):
    BLOCKED = 'blocked'
    UNBLOCKED = 'unblocked'
    CLOSED = 'closed'
    EMAIL_VERIFIED = 'email_verified'
    SUPPORT_CODE_SHOWN = 'support_code_shown'
    SUPPORT_CODE_GENERATED = 'support_code_generated'


class AccountEventReason(StrEnum):
    FAILED_ATTEMPTS = 'failed_attempts'
    TURFBOOK = 'turfbook'
    INACTIVITY_7_DAYS = 'inactivity_7_days'
    SECURITY_CODE = 'security_code'
    SUPPORT_REQUEST = 'support_request'


class AccountEventActor(StrEnum):
    SYSTEM = 'system'
    TURFBOOK = 'turfbook'
    USER = 'user'


@dataclass
class AccountEvent:
    """Something that happened to an account. When it is told to the user, it keeps
    the notice's id and when the notice was published (empty while pending); when it
    happened in a security process, that process. It never keeps a security code."""

    user_uuid: UUID
    type: AccountEventType
    reason: AccountEventReason
    actor: AccountEventActor
    created_at: datetime
    notice_id: UUID | None = None
    notice_published_at: datetime | None = None
    process_uuid: UUID | None = None
    uuid: UUID = field(default_factory=uuid4)

    @classmethod
    def blocked_for_failed_attempts(cls, user_uuid: UUID, now: datetime) -> Self:
        return cls._with_notice(
            user_uuid,
            AccountEventType.BLOCKED,
            AccountEventReason.FAILED_ATTEMPTS,
            AccountEventActor.SYSTEM,
            now,
        )

    @classmethod
    def blocked_by_turfbook(cls, user_uuid: UUID, now: datetime) -> Self:
        return cls._with_notice(
            user_uuid,
            AccountEventType.BLOCKED,
            AccountEventReason.TURFBOOK,
            AccountEventActor.TURFBOOK,
            now,
        )

    @classmethod
    def unblocked_by_turfbook(cls, user_uuid: UUID, now: datetime) -> Self:
        return cls._with_notice(
            user_uuid,
            AccountEventType.UNBLOCKED,
            AccountEventReason.TURFBOOK,
            AccountEventActor.TURFBOOK,
            now,
        )

    @classmethod
    def closed_for_inactivity(cls, user_uuid: UUID, now: datetime) -> Self:
        return cls._with_notice(
            user_uuid,
            AccountEventType.CLOSED,
            AccountEventReason.INACTIVITY_7_DAYS,
            AccountEventActor.SYSTEM,
            now,
        )

    @classmethod
    def email_verified(cls, user_uuid: UUID, process_uuid: UUID, now: datetime) -> Self:
        return cls(
            user_uuid=user_uuid,
            type=AccountEventType.EMAIL_VERIFIED,
            reason=AccountEventReason.SECURITY_CODE,
            actor=AccountEventActor.USER,
            created_at=now,
            process_uuid=process_uuid,
        )

    @classmethod
    def support_code_shown(
        cls, user_uuid: UUID, process_uuid: UUID, now: datetime
    ) -> Self:
        return cls._by_support(
            user_uuid, AccountEventType.SUPPORT_CODE_SHOWN, process_uuid, now
        )

    @classmethod
    def support_code_generated(
        cls, user_uuid: UUID, process_uuid: UUID, now: datetime
    ) -> Self:
        return cls._by_support(
            user_uuid, AccountEventType.SUPPORT_CODE_GENERATED, process_uuid, now
        )

    @classmethod
    def _by_support(
        cls,
        user_uuid: UUID,
        type: AccountEventType,
        process_uuid: UUID,
        now: datetime,
    ) -> Self:
        return cls(
            user_uuid=user_uuid,
            type=type,
            reason=AccountEventReason.SUPPORT_REQUEST,
            actor=AccountEventActor.TURFBOOK,
            created_at=now,
            process_uuid=process_uuid,
        )

    @classmethod
    def _with_notice(
        cls,
        user_uuid: UUID,
        type: AccountEventType,
        reason: AccountEventReason,
        actor: AccountEventActor,
        now: datetime,
    ) -> Self:
        return cls(
            user_uuid=user_uuid,
            type=type,
            reason=reason,
            actor=actor,
            created_at=now,
            notice_id=uuid4(),
        )

    def mark_notice_published(self, now: datetime) -> None:
        self.notice_published_at = now
