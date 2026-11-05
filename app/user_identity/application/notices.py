"""The notices the account sends to its user. Built only from stored data, so a
pending notice can be built again, with the same `notice_id`, and published later."""

from uuid import UUID

from app.user_identity.application.messages import (
    ACCOUNT_BLOCKED_NOTICE_BODY,
    ACCOUNT_BLOCKED_NOTICE_SUBJECT,
)
from app.user_identity.domain.entities.notice import Notice, NoticeRecipient, Notifier
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import User


def account_blocked_notice(
    user: User, notice_id: UUID, contact: TurfBookContact, failed_attempts: int
) -> Notice:
    body = ACCOUNT_BLOCKED_NOTICE_BODY.format(
        name=user.first_name.title(),
        failed_attempts=failed_attempts,
        phone=contact.phone,
        email=contact.email,
    )
    return Notice(
        notice_id=notice_id,
        notifiers=_notifiers(user),
        recipient=NoticeRecipient(
            uuid=user.uuid,
            email=user.email,
            cellphone=user.cellphone,
            first_name=user.first_name,
        ),
        subject=ACCOUNT_BLOCKED_NOTICE_SUBJECT,
        body=body,
    )


def _notifiers(user: User) -> tuple[Notifier, ...]:
    """A channel the user has no data for is left out (e.g. an old user without
    email); the cellphone is always there."""
    if user.email:
        return Notifier.EMAIL, Notifier.SMS
    return (Notifier.SMS,)
