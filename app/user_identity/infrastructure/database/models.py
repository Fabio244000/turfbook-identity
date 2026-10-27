from datetime import datetime
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
