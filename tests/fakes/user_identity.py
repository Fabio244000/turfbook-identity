from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import UUID

from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.notice import Notice
from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.domain.exceptions import NoticeNotPublishedError
from app.user_identity.domain.ports.output.account_event_repository_port import (
    AccountEventRepositoryPort,
)
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.domain.ports.output.user_repository_port import (
    UserRepositoryPort,
)

# The repositories store copies, like a database: a change the use case does not
# `update` is not kept, so a test cannot pass because two objects are the same
# instance. They replace stored items, never change them in place, so the unit of
# work can keep its last committed state as a plain copy of each list.


class FakeUserRepository(UserRepositoryPort):
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = [replace(user) for user in users or []]

    async def add(self, user: User) -> None:
        self.users.append(replace(user))

    async def get_by_uuid(self, user_uuid: UUID) -> User | None:
        found = next((u for u in self.users if u.uuid == user_uuid), None)
        return replace(found) if found else None

    async def get_by_username_for_update(self, username: str) -> User | None:
        found = next((u for u in self.users if u.username == username), None)
        return replace(found) if found else None

    async def get_by_uuid_for_update(self, user_uuid: UUID) -> User | None:
        return await self.get_by_uuid(user_uuid)

    async def get_blocked_before(self, cutoff: datetime) -> list[User]:
        return [
            replace(u)
            for u in self.users
            if u.status is AccountStatus.BLOCKED
            and u.blocked_at is not None
            and u.blocked_at <= cutoff
        ]

    async def get_closed(self) -> list[User]:
        return [replace(u) for u in self.users if u.status is AccountStatus.CLOSED]

    async def update(self, user: User) -> None:
        index = next(i for i, u in enumerate(self.users) if u.uuid == user.uuid)
        self.users[index] = replace(user)

    async def delete(self, user_uuids: Sequence[UUID]) -> None:
        self.users = [u for u in self.users if u.uuid not in user_uuids]

    async def exists_by_username(self, username: str) -> bool:
        return any(user.username == username for user in self.users)

    async def exists_by_email(self, email: str) -> bool:
        return any(user.email == email for user in self.users)

    async def exists_by_cellphone(self, cellphone: str) -> bool:
        return any(user.cellphone == cellphone for user in self.users)

    def stored(self, user_uuid: UUID) -> User:
        return next(u for u in self.users if u.uuid == user_uuid)


class FakeRefreshTokenRepository(RefreshTokenRepositoryPort):
    def __init__(self, tokens: list[RefreshToken] | None = None) -> None:
        self.tokens = [replace(token) for token in tokens or []]

    async def add(self, token: RefreshToken) -> None:
        self.tokens.append(replace(token))

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        found = next((t for t in self.tokens if t.token_hash == token_hash), None)
        return replace(found) if found else None

    async def get_by_session(self, session_uuid: UUID) -> list[RefreshToken]:
        return [replace(t) for t in self.tokens if t.session_uuid == session_uuid]

    async def get_active_by_user(self, user_uuid: UUID) -> list[RefreshToken]:
        return [
            replace(t)
            for t in self.tokens
            if t.user_uuid == user_uuid and not t.is_revoked
        ]

    async def update(self, token: RefreshToken) -> None:
        index = next(i for i, t in enumerate(self.tokens) if t.uuid == token.uuid)
        self.tokens[index] = replace(token)

    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None:
        self.tokens = [t for t in self.tokens if t.user_uuid not in user_uuids]

    def stored(self, token_hash: str) -> RefreshToken:
        return next(t for t in self.tokens if t.token_hash == token_hash)


class FakeAccountEventRepository(AccountEventRepositoryPort):
    def __init__(self, events: list[AccountEvent] | None = None) -> None:
        self.events = [replace(event) for event in events or []]

    async def add(self, event: AccountEvent) -> None:
        self.events.append(replace(event))

    async def update(self, event: AccountEvent) -> None:
        index = next(i for i, e in enumerate(self.events) if e.uuid == event.uuid)
        self.events[index] = replace(event)

    async def get_pending_notices(self) -> list[AccountEvent]:
        pending = [
            e
            for e in self.events
            if e.notice_id is not None and e.notice_published_at is None
        ]
        return [replace(e) for e in sorted(pending, key=lambda e: e.created_at)]

    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None:
        self.events = [e for e in self.events if e.user_uuid not in user_uuids]


class FakeUnitOfWork(UnitOfWorkPort):
    """Leaving without commit restores the last committed state, like a database
    rollback, so a test only sees what a use case actually committed. With
    `failing_commit`, that commit (counted from 1) fails, as a database that goes down."""

    def __init__(
        self,
        users: list[User] | None = None,
        refresh_tokens: list[RefreshToken] | None = None,
        account_events: list[AccountEvent] | None = None,
        failing_commit: int | None = None,
    ) -> None:
        self.users = FakeUserRepository(users)
        self.refresh_tokens = FakeRefreshTokenRepository(refresh_tokens)
        self.account_events = FakeAccountEventRepository(account_events)
        self.committed = False
        self.failing_commit = failing_commit
        self.commits = 0
        self._save()

    async def commit(self) -> None:
        self.commits += 1
        if self.commits == self.failing_commit:
            raise RuntimeError('the database is not available')
        self.committed = True
        self._save()

    async def rollback(self) -> None:
        self.users.users = list(self._users)
        self.refresh_tokens.tokens = list(self._tokens)
        self.account_events.events = list(self._events)

    def _save(self) -> None:
        self._users = list(self.users.users)
        self._tokens = list(self.refresh_tokens.tokens)
        self._events = list(self.account_events.events)


class FakeHasher(PasswordHasherPort):
    def hash(self, password: str) -> str:
        return f'hashed-{password}'

    def verify(self, password: str, hashed: str | None) -> bool:
        return hashed is not None and hashed == self.hash(password)


class FakeTokenIssuer(TokenIssuerPort):
    def issue(self, user_uuid: UUID) -> str:
        return f'token-{user_uuid}'


class FakeClock(ClockPort):
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class FakeRefreshTokenGenerator(RefreshTokenGeneratorPort):
    """Generates `refresh-1`, `refresh-2`… and hashes them as `hash-<token>`."""

    def __init__(self) -> None:
        self._count = 0

    def generate(self) -> str:
        self._count += 1
        return f'refresh-{self._count}'

    def hash(self, token: str) -> str:
        return f'hash-{token}'


class FakeNoticePublisher(NoticePublisherPort):
    """Keeps what it publishes. With `fails` every publication fails, as without the
    NAT (set it back to False to "create" the NAT); with `failing_recipients` only the
    notices of those users fail. It fails as its port declares: NoticeNotPublishedError."""

    def __init__(self, fails: bool = False) -> None:
        self.published: list[Notice] = []
        self.attempted: list[Notice] = []
        self.fails = fails
        self.failing_recipients: set[UUID] = set()

    async def publish(self, notice: Notice) -> None:
        self.attempted.append(notice)
        if self.fails or notice.recipient.uuid in self.failing_recipients:
            raise NoticeNotPublishedError()
        self.published.append(notice)

    @property
    def sent(self) -> list[dict[str, Any]]:
        """What was published, as plain data (like the message notifications reads),
        so a test checks it without touching the domain."""
        return [
            {
                'notice_id': notice.notice_id,
                'recipient': notice.recipient.uuid,
                'subject': notice.subject,
                'body': notice.body,
            }
            for notice in self.published
        ]

    @property
    def attempted_ids(self) -> list[UUID]:
        return [notice.notice_id for notice in self.attempted]
