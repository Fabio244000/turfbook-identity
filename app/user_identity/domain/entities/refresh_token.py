from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from app.user_identity.domain.exceptions import InvalidRefreshTokenError


@dataclass
class RefreshToken:
    """A single-use credential that renews a session. Only the hash of its value is
    kept; tokens of the same session share `session_uuid` so they are revoked together."""

    user_uuid: UUID
    session_uuid: UUID
    token_hash: str
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    uuid: UUID = field(default_factory=uuid4)

    @classmethod
    def issue(
        cls,
        user_uuid: UUID,
        session_uuid: UUID,
        token_hash: str,
        now: datetime,
        ttl: timedelta,
    ) -> Self:
        return cls(
            user_uuid=user_uuid,
            session_uuid=session_uuid,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + ttl,
        )

    @property
    def was_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def use(self, now: datetime) -> None:
        if self.was_used or self.is_revoked or self.is_expired(now):
            raise InvalidRefreshTokenError()
        self.used_at = now

    def revoke(self, now: datetime) -> None:
        if self.revoked_at is None:
            self.revoked_at = now
