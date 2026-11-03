from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Unique constraints are named (the names PostgreSQL already gave them), so
# constraint_errors.py can tell which one a duplicate broke.
USERS_CELLPHONE_KEY = 'users_cellphone_key'
USERS_USERNAME_KEY = 'users_username_key'
USERS_EMAIL_KEY = 'users_email_key'
USERS_FACEBOOK_TOKEN_KEY = 'users_facebook_token_key'
USERS_GMAIL_TOKEN_KEY = 'users_gmail_token_key'
REFRESH_TOKENS_TOKEN_HASH_KEY = 'refresh_tokens_token_hash_key'


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
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class RefreshTokenModel(Base):
    __tablename__ = 'refresh_tokens'
    __table_args__ = (
        UniqueConstraint('token_hash', name=REFRESH_TOKENS_TOKEN_HASH_KEY),
    )

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(ForeignKey('users.uuid'))
    session_uuid: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Never read: it tells the unit of work to INSERT the user before its tokens when
    # both are added in one transaction (the flush orders tables by relationships).
    user: Mapped[UserModel] = relationship(lazy='raise')
