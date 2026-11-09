"""The notices the account sends to its user. Built only from stored data, so a
pending notice can be built again, with the same `notice_id`, and published later."""

from datetime import datetime
from uuid import UUID

from app.user_identity.application.messages import (
    ACCOUNT_BLOCKED_BY_TURFBOOK_NOTICE_BODY,
    ACCOUNT_BLOCKED_NOTICE_BODY,
    ACCOUNT_BLOCKED_NOTICE_SUBJECT,
    ACCOUNT_CLOSED_NOTICE_BODY,
    ACCOUNT_CLOSED_NOTICE_SUBJECT,
    ACCOUNT_UNBLOCKED_NOTICE_BODY,
    ACCOUNT_UNBLOCKED_NOTICE_SUBJECT,
)
from app.user_identity.domain.entities.account_event import (
    AccountEvent,
    AccountEventReason,
    AccountEventType,
)
from app.user_identity.domain.entities.notice import Notice, NoticeRecipient, Notifier
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)


def account_blocked_notice(
    user: User, notice_id: UUID, contact: TurfBookContact, failed_attempts: int
) -> Notice:
    body = ACCOUNT_BLOCKED_NOTICE_BODY.format(
        name=user.first_name.title(),
        failed_attempts=failed_attempts,
        phone=contact.phone,
        email=contact.email,
    )
    return _notice(user, notice_id, ACCOUNT_BLOCKED_NOTICE_SUBJECT, body)


def account_change_notice(
    user: User, event: AccountEvent, contact: TurfBookContact
) -> Notice:
    """The notice of a block or unblock by TurfBook, or of a close by the review."""
    subject, body = _CHANGE_TEXTS[event.type]
    text = body.format(
        name=user.first_name.title(), phone=contact.phone, email=contact.email
    )
    return _notice(user, _notice_id(event), subject, text)


def notice_for_event(
    user: User, event: AccountEvent, contact: TurfBookContact, failed_attempts: int
) -> Notice:
    """The notice an event raised, built again with its same `notice_id`."""
    if event.reason is AccountEventReason.FAILED_ATTEMPTS:
        return account_blocked_notice(user, _notice_id(event), contact, failed_attempts)
    return account_change_notice(user, event, contact)


async def publish_notice(
    publisher: NoticePublisherPort, event: AccountEvent, notice: Notice, now: datetime
) -> bool:
    """Publishes the notice and marks the event as published; a notice that cannot be
    published stays pending (the publisher logged why). The caller commits the mark."""
    try:
        await publisher.publish(notice)
    except DomainError as error:
        if error.code is DomainErrorCode.NOTICE_NOT_PUBLISHED:
            return False
        raise
    event.mark_notice_published(now)
    return True


_CHANGE_TEXTS = {
    AccountEventType.BLOCKED: (
        ACCOUNT_BLOCKED_NOTICE_SUBJECT,
        ACCOUNT_BLOCKED_BY_TURFBOOK_NOTICE_BODY,
    ),
    AccountEventType.UNBLOCKED: (
        ACCOUNT_UNBLOCKED_NOTICE_SUBJECT,
        ACCOUNT_UNBLOCKED_NOTICE_BODY,
    ),
    AccountEventType.CLOSED: (
        ACCOUNT_CLOSED_NOTICE_SUBJECT,
        ACCOUNT_CLOSED_NOTICE_BODY,
    ),
}


def _notice_id(event: AccountEvent) -> UUID:
    if event.notice_id is None:
        raise ValueError('the event raised no notice')
    return event.notice_id


def _notice(user: User, notice_id: UUID, subject: str, body: str) -> Notice:
    return Notice(
        notice_id=notice_id,
        notifiers=_notifiers(user),
        recipient=NoticeRecipient(
            uuid=user.uuid,
            email=user.email,
            cellphone=user.cellphone,
            first_name=user.first_name,
        ),
        subject=subject,
        body=body,
    )


def _notifiers(user: User) -> tuple[Notifier, ...]:
    """A channel the user has no data for is left out (e.g. an old user without
    email); the cellphone is always there."""
    if user.email:
        return Notifier.EMAIL, Notifier.SMS
    return (Notifier.SMS,)
