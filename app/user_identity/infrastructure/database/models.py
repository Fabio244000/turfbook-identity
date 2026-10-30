from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = 'users'

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(250))
    last_name: Mapped[str] = mapped_column(String(250))
    cellphone: Mapped[str] = mapped_column(String(13), unique=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True)
    password: Mapped[str | None] = mapped_column(String(255))
    facebook_token: Mapped[str | None] = mapped_column(String(250), unique=True)
    gmail_token: Mapped[str | None] = mapped_column(String(250), unique=True)
    email: Mapped[str | None] = mapped_column(String(250), unique=True)
    created_at: Mapped[datetime] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column()


class RefreshTokenModel(Base):
    __tablename__ = 'refresh_tokens'

    uuid: Mapped[UUID] = mapped_column(primary_key=True)
    user_uuid: Mapped[UUID] = mapped_column(ForeignKey('users.uuid'))
    session_uuid: Mapped[UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Never read: it tells the unit of work to INSERT the user before its tokens when
    # both are added in one transaction (the flush orders tables by relationships).
    user: Mapped[UserModel] = relationship(lazy='raise')
