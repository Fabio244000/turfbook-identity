from datetime import datetime, timedelta, tzinfo
from uuid import uuid4

from app.user_identity.application.notices import account_blocked_notice
from app.user_identity.application.sessions import (
    issue_refresh_token,
    revoke_user_sessions,
)
from app.user_identity.domain.entities.account_event import AccountEvent
from app.user_identity.domain.entities.session_tokens import SessionTokens
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.entities.user import AccountStatus, User
from app.user_identity.domain.exceptions import (
    AccountBlockedError,
    InvalidCredentialsError,
    NoticeNotPublishedError,
)
from app.user_identity.domain.ports.input.start_session_port import StartSessionPort
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
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class StartSessionUseCase(StartSessionPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        hasher: PasswordHasherPort,
        token_issuer: TokenIssuerPort,
        clock: ClockPort,
        refresh_token_generator: RefreshTokenGeneratorPort,
        refresh_token_ttl: timedelta,
        notice_publisher: NoticePublisherPort,
        contact: TurfBookContact,
        max_failed_attempts: int,
        business_timezone: tzinfo,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_issuer = token_issuer
        self._clock = clock
        self._refresh_token_generator = refresh_token_generator
        self._refresh_token_ttl = refresh_token_ttl
        self._notice_publisher = notice_publisher
        self._contact = contact
        self._max_failed_attempts = max_failed_attempts
        self._business_timezone = business_timezone

    async def execute(self, username: str, password: str) -> SessionTokens:
        now = self._clock.now()
        async with self._uow:
            # Locked until the commit: concurrent attempts are counted one by one.
            user = await self._uow.users.get_by_username_for_update(username)
            # Verified even without a user, so the answer time reveals nothing.
            password_ok = self._hasher.verify(password, user.password if user else None)
            user = self._account_that_may_try(user, password_ok)
            if password_ok:
                refresh_token = await self._open_session(user, now)
            else:
                block = await self._record_failed_attempt(user, now)
            await self._uow.commit()
        if not password_ok:
            await self._publish_block_notice(user, block, now)
            raise InvalidCredentialsError()
        return SessionTokens(self._token_issuer.issue(user.uuid), refresh_token)

    def _account_that_may_try(self, user: User | None, password_ok: bool) -> User:
        """Without a password, or closed, there is nothing to guess: the attempt is
        rejected without counting. A blocked account only learns it is blocked
        with its right password."""
        if user is None or user.password is None or user.status is AccountStatus.CLOSED:
            raise InvalidCredentialsError()
        if user.status is AccountStatus.BLOCKED:
            if password_ok:
                raise AccountBlockedError(self._contact)
            raise InvalidCredentialsError()
        return user

    async def _open_session(self, user: User, now: datetime) -> str:
        user.record_sign_in()
        await self._uow.users.update(user)
        await revoke_user_sessions(self._uow, user.uuid, now)
        return await issue_refresh_token(
            self._uow,
            self._refresh_token_generator,
            user_uuid=user.uuid,
            session_uuid=uuid4(),
            now=now,
            ttl=self._refresh_token_ttl,
        )

    async def _record_failed_attempt(
        self, user: User, now: datetime
    ) -> AccountEvent | None:
        """The block event, when this attempt blocks the account."""
        today = now.astimezone(self._business_timezone).date()
        user.record_failed_attempt(today, now, self._max_failed_attempts)
        await self._uow.users.update(user)
        if user.status is not AccountStatus.BLOCKED:
            return None
        event = AccountEvent.blocked_for_failed_attempts(user.uuid, now)
        await self._uow.account_events.add(event)
        return event

    async def _publish_block_notice(
        self, user: User, event: AccountEvent | None, now: datetime
    ) -> None:
        """After the block is committed: a notice that cannot be published stays
        pending (the adapter logs why) and the sign-in answers the same."""
        if event is None or event.notice_id is None:
            return
        notice = account_blocked_notice(
            user, event.notice_id, self._contact, self._max_failed_attempts
        )
        try:
            await self._notice_publisher.publish(notice)
        except NoticeNotPublishedError:
            return
        event.mark_notice_published(now)
        async with self._uow:
            await self._uow.account_events.update(event)
            await self._uow.commit()
