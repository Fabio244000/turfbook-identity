from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.user_identity.domain.entities.account_event import (
    AccountEvent,
    AccountEventActor,
    AccountEventReason,
    AccountEventType,
)
from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.entities.security_process import (
    CodeIssuer,
    SecurityCode,
    SecurityCodeStatus,
    SecurityProcess,
    SecurityProcessType,
)
from app.user_identity.domain.entities.user import User

StoredUser = tuple[Any, ...] | None
StoredRefreshToken = tuple[Any, ...] | None
StoredAccountEvent = tuple[Any, ...] | None


REGISTERED_AT = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
REFRESH_TOKEN_TTL = timedelta(days=7)


@pytest.fixture
def new_user() -> Callable[..., User]:
    """Builds a valid User whose unique fields collide with no existing row."""

    def _new_user(**overrides: Any) -> User:
        suffix = uuid4().hex[:8]
        data: dict[str, Any] = {
            'first_name': 'fabio',
            'last_name': 'nunez',
            'cellphone': f'+519{uuid4().int % 10**8:08d}',
            'username': f'user{suffix}',
            'password': 'hashedsecret123',
            'email': f'user{suffix}@mail.com',
            'created_at': REGISTERED_AT,
            'updated_at': REGISTERED_AT,
        }
        data.update(overrides)
        return User(**data)

    return _new_user


@pytest.fixture
def insert_user(connection: AsyncConnection) -> Callable[[User], Awaitable[None]]:
    async def _insert_user(user: User) -> None:
        await connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone,'
                ' username, password, email, created_at, updated_at, status,'
                ' failed_attempts, last_failed_attempt_on, blocked_at, closed_at)'
                ' VALUES (:uuid, :first_name, :last_name, :cellphone,'
                ' :username, :password, :email, :created_at, :updated_at, :status,'
                ' :failed_attempts, :last_failed_attempt_on, :blocked_at, :closed_at)'
            ),
            {
                'uuid': user.uuid,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'cellphone': user.cellphone,
                'username': user.username,
                'password': user.password,
                'email': user.email,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'status': user.status.value,
                'failed_attempts': user.failed_attempts,
                'last_failed_attempt_on': user.last_failed_attempt_on,
                'blocked_at': user.blocked_at,
                'closed_at': user.closed_at,
            },
        )

    return _insert_user


@pytest.fixture
def stored_account_state(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[StoredUser]]:
    async def _stored_account_state(uuid: UUID) -> StoredUser:
        result = await connection.execute(
            text(
                'SELECT status, failed_attempts, last_failed_attempt_on,'
                ' blocked_at, closed_at FROM users WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_account_state


@pytest_asyncio.fixture
async def existing_user(
    new_user: Callable[..., User], insert_user: Callable[[User], Awaitable[None]]
) -> User:
    """A user already in the database, for rows that reference one."""
    user = new_user()
    await insert_user(user)
    return user


@pytest.fixture
def stored_user(connection: AsyncConnection) -> Callable[[UUID], Awaitable[StoredUser]]:
    async def _stored_user(uuid: UUID) -> StoredUser:
        result = await connection.execute(
            text(
                'SELECT username, cellphone, email, password'
                ' FROM users WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_user


@pytest.fixture
def new_refresh_token() -> Callable[..., RefreshToken]:
    """Builds a valid RefreshToken of `user` whose hash collides with no existing row."""

    def _new_refresh_token(user: User, **overrides: Any) -> RefreshToken:
        data: dict[str, Any] = {
            'user_uuid': user.uuid,
            'session_uuid': uuid4(),
            'token_hash': uuid4().hex + uuid4().hex,
            'created_at': REGISTERED_AT,
            'expires_at': REGISTERED_AT + REFRESH_TOKEN_TTL,
        }
        data.update(overrides)
        return RefreshToken(**data)

    return _new_refresh_token


@pytest.fixture
def insert_refresh_token(
    connection: AsyncConnection,
) -> Callable[[RefreshToken], Awaitable[None]]:
    async def _insert_refresh_token(token: RefreshToken) -> None:
        await connection.execute(
            text(
                'INSERT INTO refresh_tokens (uuid, user_uuid, session_uuid,'
                ' token_hash, created_at, expires_at, used_at, revoked_at)'
                ' VALUES (:uuid, :user_uuid, :session_uuid, :token_hash,'
                ' :created_at, :expires_at, :used_at, :revoked_at)'
            ),
            {
                'uuid': token.uuid,
                'user_uuid': token.user_uuid,
                'session_uuid': token.session_uuid,
                'token_hash': token.token_hash,
                'created_at': token.created_at,
                'expires_at': token.expires_at,
                'used_at': token.used_at,
                'revoked_at': token.revoked_at,
            },
        )

    return _insert_refresh_token


@pytest.fixture
def stored_refresh_token(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[StoredRefreshToken]]:
    async def _stored_refresh_token(uuid: UUID) -> StoredRefreshToken:
        result = await connection.execute(
            text(
                'SELECT user_uuid, session_uuid, token_hash, created_at,'
                ' expires_at, used_at, revoked_at'
                ' FROM refresh_tokens WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_refresh_token


@pytest.fixture
def new_account_event() -> Callable[..., AccountEvent]:
    def _new_account_event(user: User, **overrides: Any) -> AccountEvent:
        data: dict[str, Any] = {
            'user_uuid': user.uuid,
            'type': AccountEventType.BLOCKED,
            'reason': AccountEventReason.FAILED_ATTEMPTS,
            'actor': AccountEventActor.SYSTEM,
            'created_at': REGISTERED_AT,
            'notice_id': uuid4(),
        }
        data.update(overrides)
        return AccountEvent(**data)

    return _new_account_event


@pytest.fixture
def insert_account_event(
    connection: AsyncConnection,
) -> Callable[[AccountEvent], Awaitable[None]]:
    async def _insert_account_event(event: AccountEvent) -> None:
        await connection.execute(
            text(
                'INSERT INTO account_events (uuid, user_uuid, type, reason, actor,'
                ' notice_id, notice_published_at, created_at)'
                ' VALUES (:uuid, :user_uuid, :type, :reason, :actor,'
                ' :notice_id, :notice_published_at, :created_at)'
            ),
            {
                'uuid': event.uuid,
                'user_uuid': event.user_uuid,
                'type': event.type.value,
                'reason': event.reason.value,
                'actor': event.actor.value,
                'notice_id': event.notice_id,
                'notice_published_at': event.notice_published_at,
                'created_at': event.created_at,
            },
        )

    return _insert_account_event


@pytest.fixture
def stored_account_event(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[StoredAccountEvent]]:
    async def _stored_account_event(uuid: UUID) -> StoredAccountEvent:
        result = await connection.execute(
            text(
                'SELECT user_uuid, type, reason, actor, notice_id,'
                ' notice_published_at, created_at, process_uuid'
                ' FROM account_events WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_account_event


StoredProcess = tuple[Any, ...] | None
CODE_MINUTES = timedelta(minutes=5)
RULES = SecurityCodeRules(
    code_minutes=5,
    max_user_codes=3,
    max_support_codes=2,
    max_attempts=3,
    support_grace_minutes=60,
)


@pytest.fixture
def new_process() -> Callable[..., SecurityProcess]:
    """A process of `user` in progress, with one active code sent to the user."""

    def _new_process(user: User, **overrides: Any) -> SecurityProcess:
        data: dict[str, Any] = {
            'user_uuid': user.uuid,
            'type': SecurityProcessType.EMAIL_VERIFICATION,
            'started_at': REGISTERED_AT,
            'user_codes': 1,
        }
        data.update(overrides)
        process = SecurityProcess(**data)
        process.codes.append(
            SecurityCode(
                process_uuid=process.uuid,
                code='482913',
                issued_by=CodeIssuer.USER,
                created_at=process.started_at,
                expires_at=process.started_at + CODE_MINUTES,
                status=SecurityCodeStatus.ACTIVE,
            )
        )
        return process

    return _new_process


@pytest.fixture
def insert_process(
    connection: AsyncConnection,
) -> Callable[[SecurityProcess], Awaitable[None]]:
    async def _insert_process(process: SecurityProcess) -> None:
        await connection.execute(
            text(
                'INSERT INTO security_processes (uuid, user_uuid, type, status,'
                ' user_codes, support_codes, started_at, validated_at, finished_at,'
                ' failure_reason) VALUES (:uuid, :user_uuid, :type, :status,'
                ' :user_codes, :support_codes, :started_at, :validated_at,'
                ' :finished_at, :failure_reason)'
            ),
            {
                'uuid': process.uuid,
                'user_uuid': process.user_uuid,
                'type': process.type.value,
                'status': process.status.value,
                'user_codes': process.user_codes,
                'support_codes': process.support_codes,
                'started_at': process.started_at,
                'validated_at': process.validated_at,
                'finished_at': process.finished_at,
                'failure_reason': process.failure_reason,
            },
        )
        for code in process.codes:
            await connection.execute(
                text(
                    'INSERT INTO security_codes (uuid, process_uuid, code,'
                    ' issued_by, created_at, expires_at, failed_attempts, status)'
                    ' VALUES (:uuid, :process_uuid, :code, :issued_by, :created_at,'
                    ' :expires_at, :failed_attempts, :status)'
                ),
                {
                    'uuid': code.uuid,
                    'process_uuid': code.process_uuid,
                    'code': code.code,
                    'issued_by': code.issued_by.value,
                    'created_at': code.created_at,
                    'expires_at': code.expires_at,
                    'failed_attempts': code.failed_attempts,
                    'status': code.status.value,
                },
            )

    return _insert_process


@pytest.fixture
def stored_process(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[StoredProcess]]:
    async def _stored_process(uuid: UUID) -> StoredProcess:
        result = await connection.execute(
            text(
                'SELECT status, user_codes, support_codes, validated_at,'
                ' finished_at, failure_reason FROM security_processes'
                ' WHERE uuid = :uuid'
            ),
            {'uuid': uuid},
        )
        row = result.one_or_none()
        return tuple(row) if row else None

    return _stored_process


@pytest.fixture
def stored_codes(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[list[tuple[Any, ...]]]]:
    """The codes of a process, oldest first."""

    async def _stored_codes(process_uuid: UUID) -> list[tuple[Any, ...]]:
        result = await connection.execute(
            text(
                'SELECT code, issued_by, status, failed_attempts, expires_at'
                ' FROM security_codes WHERE process_uuid = :uuid'
                ' ORDER BY created_at'
            ),
            {'uuid': process_uuid},
        )
        return [tuple(row) for row in result]

    return _stored_codes


@pytest.fixture
def stored_email_verified_at(
    connection: AsyncConnection,
) -> Callable[[UUID], Awaitable[datetime | None]]:
    async def _stored_email_verified_at(uuid: UUID) -> datetime | None:
        result = await connection.execute(
            text('SELECT email_verified_at FROM users WHERE uuid = :uuid'),
            {'uuid': uuid},
        )
        value: datetime | None = result.scalar_one()
        return value

    return _stored_email_verified_at
