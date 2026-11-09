from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.user_identity.domain.entities.account_event import (
    AccountEventActor,
    AccountEventReason,
    AccountEventType,
)
from app.user_identity.domain.entities.user import AccountStatus

# Unique constraints are named (the names PostgreSQL already gave them), so
# constraint_errors.py can tell which one a duplicate broke.
USERS_CELLPHONE_KEY = 'users_cellphone_key'
USERS_USERNAME_KEY = 'users_username_key'
USERS_EMAIL_KEY = 'users_email_key'
USERS_FACEBOOK_TOKEN_KEY = 'users_facebook_token_key'
USERS_GMAIL_TOKEN_KEY = 'users_gmail_token_key'
REFRESH_TOKENS_TOKEN_HASH_KEY = 'refresh_tokens_token_hash_key'

# Fixed lists are stored as text that only accepts their values.
ENUM_LENGTH = 30


def _one_of(column: str, values: type[StrEnum], name: str) -> CheckConstraint:
    allowed = ', '.join(f"'{value}'" for value in values)
    return CheckConstraint(f'{column} IN ({allowed})', name=name)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('cellphone', name=USERS_CELLPHONE_KEY),
        UniqueConstraint('username', name=USERS_USERNAME_KEY),
        UniqueConstraint('email', name=USERS_EMAIL_KEY),
        UniqueConstraint('facebook_token', name=USERS_FACEBOOK_TOKEN_KEY),
        UniqueConstraint('gmail_token', name=USERS_GMAIL_TOKEN_KEY),
        _one_of('status', AccountStatus, 'users_status_check'),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(250))
    last_name: Mapped[str] = mapped_column(String(250))
    cellphone: Mapped[str] = mapped_column(String(12))
    username: Mapped[str | None] = mapped_column(String(50))
    password: Mapped[str | None] = mapped_column(String(255))
    facebook_token: Mapped[str | None] = mapped_column(String(250))
    gmail_token: Mapped[str | None] = mapped_column(String(250))
    email: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(ENUM_LENGTH))
    failed_attempts: Mapped[int] = mapped_column()
    last_failed_attempt_on: Mapped[date | None] = mapped_column()
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshTokenModel(Base):
    __tablename__ = 'refresh_tokens'
    __table_args__ = (
        UniqueConstraint('token_hash', name=REFRESH_TOKENS_TOKEN_HASH_KEY),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(ForeignKey('users.uuid'), index=True)
    session_uuid: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Never read: it tells the unit of work to INSERT the user before its tokens when
    # both are added in one transaction (the flush orders tables by relationships).
    user: Mapped[UserModel] = relationship(lazy='raise')


class AccountEventModel(Base):
    __tablename__ = 'account_events'
    __table_args__ = (
        _one_of('type', AccountEventType, 'account_events_type_check'),
        _one_of('reason', AccountEventReason, 'account_events_reason_check'),
        _one_of('actor', AccountEventActor, 'account_events_actor_check'),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(ForeignKey('users.uuid'), index=True)
    type: Mapped[str] = mapped_column(String(ENUM_LENGTH))
    reason: Mapped[str] = mapped_column(String(ENUM_LENGTH))
    actor: Mapped[str] = mapped_column(String(ENUM_LENGTH))
    notice_id: Mapped[UUID | None] = mapped_column()
    notice_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
