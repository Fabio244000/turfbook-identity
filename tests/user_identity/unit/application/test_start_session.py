from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.user_identity.application.use_cases.start_session import (
    StartSessionUseCase,
)
from app.user_identity.domain.entities.account_event import (
    AccountEventActor,
    AccountEventReason,
    AccountEventType,
)
from app.user_identity.domain.entities.notice import Notifier
from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.domain.exceptions import (
    AccountBlockedError,
    InvalidCredentialsError,
)
from tests.fakes.user_identity import (
    FakeClock,
    FakeHasher,
    FakeNoticePublisher,
    FakeRefreshTokenGenerator,
    FakeTokenIssuer,
    FakeUnitOfWork,
)

# 12:00 in Lima (UTC-5) on Thursday 2026-11-05.
NOW = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)
TODAY = date(2026, 11, 5)
LIMA = ZoneInfo('America/Lima')
REFRESH_TOKEN_TTL = timedelta(days=7)
MAX_FAILED_ATTEMPTS = 5
CONTACT = TurfBookContact(phone='+51 999999998', email='turfbook@gmail.com')
PASSWORD = 'GrassElSol2026!'
INVALID_CREDENTIALS = 'Incorrect username or password.'


def _user(**overrides: Any) -> User:
    data: dict[str, Any] = {
        'first_name': 'rosa',
        'last_name': 'quispe',
        'cellphone': '+51987654321',
        'username': 'rosaquispe',
        'password': f'hashed-{PASSWORD}',
        'email': 'rosa.quispe@gmail.com',
        'created_at': NOW - timedelta(days=30),
        'updated_at': NOW - timedelta(days=30),
    }
    data.update(overrides)
    return User(**data)


def _session_token(user: User, value: str) -> RefreshToken:
    return RefreshToken.issue(
        user_uuid=user.uuid,
        session_uuid=uuid4(),
        token_hash=f'hash-{value}',
        now=NOW - timedelta(days=1),
        ttl=REFRESH_TOKEN_TTL,
    )


def _start_session(
    uow: FakeUnitOfWork,
    now: datetime = NOW,
    publisher: FakeNoticePublisher | None = None,
) -> StartSessionUseCase:
    return StartSessionUseCase(
        uow=uow,
        hasher=FakeHasher(),
        token_issuer=FakeTokenIssuer(),
        clock=FakeClock(now),
        refresh_token_generator=FakeRefreshTokenGenerator(),
        refresh_token_ttl=REFRESH_TOKEN_TTL,
        notice_publisher=publisher or FakeNoticePublisher(),
        contact=CONTACT,
        max_failed_attempts=MAX_FAILED_ATTEMPTS,
        business_timezone=LIMA,
    )


async def _fail_once(
    uow: FakeUnitOfWork,
    now: datetime = NOW,
    publisher: FakeNoticePublisher | None = None,
) -> None:
    with pytest.raises(InvalidCredentialsError, match=INVALID_CREDENTIALS):
        await _start_session(uow, now, publisher).execute('rosaquispe', 'wrong')


def _failed_today(attempts: int, **overrides: Any) -> User:
    return _user(failed_attempts=attempts, last_failed_attempt_on=TODAY, **overrides)


class TestStartSession:
    async def test_opens_a_session_with_the_right_credentials(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user])

        tokens = await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert tokens.access_token == f'token-{user.uuid}'
        assert tokens.refresh_token == 'refresh-1'
        assert uow.refresh_tokens.stored('hash-refresh-1').user_uuid == user.uuid

    async def test_the_new_session_expires_after_the_refresh_token_ttl(self) -> None:
        uow = FakeUnitOfWork(users=[_user()])

        await _start_session(uow).execute('rosaquispe', PASSWORD)

        stored = uow.refresh_tokens.stored('hash-refresh-1')
        assert stored.expires_at == NOW + REFRESH_TOKEN_TTL


class TestStartSessionWrongCredentials:
    async def test_rejects_a_wrong_password(self) -> None:
        uow = FakeUnitOfWork(users=[_user()])

        with pytest.raises(InvalidCredentialsError, match=INVALID_CREDENTIALS):
            await _start_session(uow).execute('rosaquispe', 'GrassElSol2026')

    async def test_rejects_an_unknown_username_with_the_same_error(self) -> None:
        uow = FakeUnitOfWork(users=[_user()])

        with pytest.raises(InvalidCredentialsError, match=INVALID_CREDENTIALS):
            await _start_session(uow).execute('rosaquispee', PASSWORD)

    async def test_opens_no_session_on_a_wrong_password(self) -> None:
        uow = FakeUnitOfWork(users=[_user()])

        await _fail_once(uow)

        assert uow.refresh_tokens.tokens == []

    async def test_a_failed_attempt_is_saved_although_the_sign_in_fails(
        self,
    ) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        stored = uow.users.stored(user.uuid)
        assert (stored.failed_attempts, stored.last_failed_attempt_on) == (1, TODAY)

    async def test_an_account_without_password_is_rejected_without_counting(
        self,
    ) -> None:
        user = _user(password=None, gmail_token='gmail-token')
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        assert uow.users.stored(user.uuid).failed_attempts == 0


class TestStartSessionSingleSession:
    async def test_signing_in_revokes_the_previous_sessions(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(
            users=[user],
            refresh_tokens=[_session_token(user, 'phone'), _session_token(user, 'pc')],
        )

        await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.refresh_tokens.stored('hash-phone').revoked_at == NOW
        assert uow.refresh_tokens.stored('hash-pc').revoked_at == NOW

    async def test_the_new_session_is_not_revoked(self) -> None:
        user = _user()
        uow = FakeUnitOfWork(users=[user], refresh_tokens=[_session_token(user, 'pc')])

        await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.refresh_tokens.stored('hash-refresh-1').is_revoked is False

    async def test_does_not_touch_the_sessions_of_other_users(self) -> None:
        other = _user(username='luish', cellphone='+51912345678', email='l@mail.com')
        uow = FakeUnitOfWork(
            users=[_user(), other], refresh_tokens=[_session_token(other, 'luis')]
        )

        await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.refresh_tokens.stored('hash-luis').is_revoked is False


class TestStartSessionFailedAttempts:
    async def test_a_correct_sign_in_resets_the_failed_attempts(self) -> None:
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])

        await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.users.stored(user.uuid).failed_attempts == 0

    async def test_attempts_of_another_day_do_not_count(self) -> None:
        user = _user(failed_attempts=3, last_failed_attempt_on=TODAY - timedelta(1))
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)
        await _fail_once(uow)

        stored = uow.users.stored(user.uuid)
        assert (stored.status, stored.failed_attempts) == (AccountStatus.ACTIVE, 2)

    async def test_the_day_is_counted_in_peru_time(self) -> None:
        # 23:30 in Lima is already the next day in UTC: it is still the same day.
        late_at_night = datetime(2026, 11, 6, 4, 30, tzinfo=UTC)
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow, now=late_at_night)

        assert uow.users.stored(user.uuid).status == AccountStatus.BLOCKED

    async def test_the_fourth_failure_does_not_block(self) -> None:
        user = _failed_today(3)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        assert uow.users.stored(user.uuid).status == AccountStatus.ACTIVE
        assert uow.account_events.events == []

    async def test_the_fifth_consecutive_failure_blocks_the_account(self) -> None:
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        stored = uow.users.stored(user.uuid)
        assert (stored.status, stored.blocked_at) == (AccountStatus.BLOCKED, NOW)

    async def test_blocking_records_the_event_with_its_notice(self) -> None:
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        [event] = uow.account_events.events
        assert (event.user_uuid, event.created_at) == (user.uuid, NOW)
        assert event.type == AccountEventType.BLOCKED
        assert event.reason == AccountEventReason.FAILED_ATTEMPTS
        assert event.actor == AccountEventActor.SYSTEM
        assert event.notice_id is not None


class TestStartSessionBlockNotice:
    async def test_publishes_the_notice_of_the_block(self) -> None:
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])
        publisher = FakeNoticePublisher()

        await _fail_once(uow, publisher=publisher)

        [notice] = publisher.published
        [event] = uow.account_events.events
        assert notice.notice_id == event.notice_id
        assert notice.notifiers == (Notifier.EMAIL, Notifier.SMS)
        assert notice.recipient.uuid == user.uuid
        assert notice.recipient.email == 'rosa.quispe@gmail.com'
        assert notice.recipient.cellphone == '+51987654321'
        assert notice.recipient.first_name == 'rosa'

    async def test_the_notice_tells_the_user_how_to_contact_turfbook(self) -> None:
        publisher = FakeNoticePublisher()

        await _fail_once(FakeUnitOfWork(users=[_failed_today(4)]), publisher=publisher)

        [notice] = publisher.published
        assert notice.subject == 'Tu cuenta de TurfBook fue bloqueada'
        assert notice.body == (
            'Hola Rosa, tu cuenta de TurfBook fue bloqueada por 5 intentos fallidos '
            'de ingreso. Comunícate con TurfBook al +51 999999998 o a '
            'turfbook@gmail.com dentro de los próximos 7 días; si no, tu cuenta se '
            'cerrará.'
        )

    async def test_greets_with_each_word_of_the_first_name_capitalized(
        self,
    ) -> None:
        publisher = FakeNoticePublisher()
        user = _failed_today(4, first_name='maría josé')

        await _fail_once(FakeUnitOfWork(users=[user]), publisher=publisher)

        [notice] = publisher.published
        assert notice.body.startswith('Hola María José, ')
        assert notice.recipient.first_name == 'maría josé'

    async def test_a_user_without_email_is_notified_only_by_sms(self) -> None:
        publisher = FakeNoticePublisher()
        user = _failed_today(4, email=None)

        await _fail_once(FakeUnitOfWork(users=[user]), publisher=publisher)

        [notice] = publisher.published
        assert notice.notifiers == (Notifier.SMS,)

    async def test_the_published_notice_is_recorded(self) -> None:
        uow = FakeUnitOfWork(users=[_failed_today(4)])

        await _fail_once(uow)

        [event] = uow.account_events.events
        assert event.notice_published_at == NOW

    async def test_a_failed_publication_keeps_the_block_and_the_notice_pending(
        self,
    ) -> None:
        user = _failed_today(4)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow, publisher=FakeNoticePublisher(fails=True))

        [event] = uow.account_events.events
        assert uow.users.stored(user.uuid).status == AccountStatus.BLOCKED
        assert event.notice_id is not None
        assert event.notice_published_at is None


class TestStartSessionBlockedOrClosedAccount:
    async def test_a_blocked_account_with_the_right_password_gets_the_contact(
        self,
    ) -> None:
        user = _failed_today(5, status=AccountStatus.BLOCKED, blocked_at=NOW)
        uow = FakeUnitOfWork(users=[user])

        with pytest.raises(
            AccountBlockedError,
            match=r'^Your account is blocked\. Contact TurfBook at \+51 999999998 '
            r'or turfbook@gmail\.com\.$',
        ):
            await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.refresh_tokens.tokens == []

    async def test_a_blocked_account_with_a_wrong_password_does_not_count(
        self,
    ) -> None:
        user = _failed_today(5, status=AccountStatus.BLOCKED, blocked_at=NOW)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        assert uow.users.stored(user.uuid).failed_attempts == 5
        assert uow.account_events.events == []

    async def test_a_closed_account_cannot_sign_in(self) -> None:
        uow = FakeUnitOfWork(users=[_user(status=AccountStatus.CLOSED)])

        with pytest.raises(InvalidCredentialsError, match=INVALID_CREDENTIALS):
            await _start_session(uow).execute('rosaquispe', PASSWORD)

        assert uow.refresh_tokens.tokens == []

    async def test_a_failure_on_a_closed_account_does_not_block_it(self) -> None:
        user = _failed_today(4, status=AccountStatus.CLOSED)
        uow = FakeUnitOfWork(users=[user])

        await _fail_once(uow)

        stored = uow.users.stored(user.uuid)
        assert (stored.status, stored.failed_attempts) == (AccountStatus.CLOSED, 4)
