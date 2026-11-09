import hmac
from datetime import timedelta, tzinfo
from functools import cache
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.user_identity.application.use_cases.block_account import BlockAccountUseCase
from app.user_identity.application.use_cases.refresh_session import (
    RefreshSessionUseCase,
)
from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.application.use_cases.revoke_session import (
    RevokeSessionUseCase,
)
from app.user_identity.application.use_cases.start_session import (
    StartSessionUseCase,
)
from app.user_identity.application.use_cases.unblock_account import (
    UnblockAccountUseCase,
)
from app.user_identity.domain.entities.turfbook_contact import TurfBookContact
from app.user_identity.domain.ports.input.block_account_port import BlockAccountPort
from app.user_identity.domain.ports.input.refresh_session_port import (
    RefreshSessionPort,
)
from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.domain.ports.input.revoke_session_port import RevokeSessionPort
from app.user_identity.domain.ports.input.start_session_port import StartSessionPort
from app.user_identity.domain.ports.input.unblock_account_port import (
    UnblockAccountPort,
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
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.infrastructure.api.exceptions import NotAuthorizedError
from app.user_identity.infrastructure.clock.system_clock import SystemClock
from app.user_identity.infrastructure.database.session import async_session
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.messaging.sns_notice_publisher import (
    SnsNoticePublisher,
    sns_client,
)
from app.user_identity.infrastructure.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.user_identity.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from app.user_identity.infrastructure.security.secrets_refresh_token_generator import (
    SecretsRefreshTokenGenerator,
)
from config.settings import settings

if TYPE_CHECKING:  # the type stubs are a development dependency
    from types_boto3_sns.client import SNSClient


@cache
def _sns_client() -> 'SNSClient':
    """One client per Lambda execution environment, created on first use."""
    return sns_client(
        settings.notices_topic_arn, settings.notice_publish_timeout_seconds
    )


def get_access_token_lifetime() -> timedelta:
    return timedelta(minutes=settings.access_token_expire_minutes)


def get_refresh_token_ttl() -> timedelta:
    return timedelta(days=settings.refresh_token_expire_days)


def get_unit_of_work() -> UnitOfWorkPort:
    return SqlAlchemyUnitOfWork(async_session)


def get_clock() -> ClockPort:
    return SystemClock()


def get_token_issuer(
    clock: ClockPort = Depends(get_clock),
    lifetime: timedelta = Depends(get_access_token_lifetime),
) -> TokenIssuerPort:
    return JwtTokenIssuer(
        private_key=settings.jwt_private_key, lifetime=lifetime, clock=clock
    )


def get_password_hasher() -> PasswordHasherPort:
    return Argon2PasswordHasher()


def get_refresh_token_generator() -> RefreshTokenGeneratorPort:
    return SecretsRefreshTokenGenerator(token_bytes=settings.refresh_token_bytes)


def get_notice_publisher() -> NoticePublisherPort:
    return SnsNoticePublisher(_sns_client(), settings.notices_topic_arn)


def get_turfbook_contact() -> TurfBookContact:
    return TurfBookContact(
        phone=settings.turfbook_contact_phone, email=settings.turfbook_contact_email
    )


def get_business_timezone() -> tzinfo:
    return ZoneInfo(settings.business_timezone)


def get_register_user_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    token_issuer: TokenIssuerPort = Depends(get_token_issuer),
    clock: ClockPort = Depends(get_clock),
    generator: RefreshTokenGeneratorPort = Depends(get_refresh_token_generator),
    refresh_token_ttl: timedelta = Depends(get_refresh_token_ttl),
) -> RegisterUserPort:
    return RegisterUserUseCase(
        uow=uow,
        hasher=password_hasher,
        token_issuer=token_issuer,
        clock=clock,
        refresh_token_generator=generator,
        refresh_token_ttl=refresh_token_ttl,
    )


def get_start_session_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    token_issuer: TokenIssuerPort = Depends(get_token_issuer),
    clock: ClockPort = Depends(get_clock),
    generator: RefreshTokenGeneratorPort = Depends(get_refresh_token_generator),
    refresh_token_ttl: timedelta = Depends(get_refresh_token_ttl),
    notice_publisher: NoticePublisherPort = Depends(get_notice_publisher),
    contact: TurfBookContact = Depends(get_turfbook_contact),
    business_timezone: tzinfo = Depends(get_business_timezone),
) -> StartSessionPort:
    return StartSessionUseCase(
        uow=uow,
        hasher=password_hasher,
        token_issuer=token_issuer,
        clock=clock,
        refresh_token_generator=generator,
        refresh_token_ttl=refresh_token_ttl,
        notice_publisher=notice_publisher,
        contact=contact,
        max_failed_attempts=settings.max_failed_attempts,
        business_timezone=business_timezone,
    )


def get_refresh_session_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    token_issuer: TokenIssuerPort = Depends(get_token_issuer),
    clock: ClockPort = Depends(get_clock),
    generator: RefreshTokenGeneratorPort = Depends(get_refresh_token_generator),
    refresh_token_ttl: timedelta = Depends(get_refresh_token_ttl),
) -> RefreshSessionPort:
    return RefreshSessionUseCase(
        uow=uow,
        token_issuer=token_issuer,
        clock=clock,
        refresh_token_generator=generator,
        refresh_token_ttl=refresh_token_ttl,
    )


def get_revoke_session_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    clock: ClockPort = Depends(get_clock),
    generator: RefreshTokenGeneratorPort = Depends(get_refresh_token_generator),
) -> RevokeSessionPort:
    return RevokeSessionUseCase(uow=uow, clock=clock, refresh_token_generator=generator)


_api_key_header = APIKeyHeader(name='X-Api-Key', auto_error=False)


def require_turfbook_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Only TurfBook manages accounts (S7): compared in constant time, so the answer
    time tells nothing about the key; the key is never logged."""
    expected = settings.accounts_api_key.encode()
    if api_key is None or not hmac.compare_digest(api_key.encode(), expected):
        raise NotAuthorizedError()


def get_block_account_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    clock: ClockPort = Depends(get_clock),
    notice_publisher: NoticePublisherPort = Depends(get_notice_publisher),
    contact: TurfBookContact = Depends(get_turfbook_contact),
) -> BlockAccountPort:
    return BlockAccountUseCase(uow, clock, notice_publisher, contact)


def get_unblock_account_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    clock: ClockPort = Depends(get_clock),
    notice_publisher: NoticePublisherPort = Depends(get_notice_publisher),
    contact: TurfBookContact = Depends(get_turfbook_contact),
) -> UnblockAccountPort:
    return UnblockAccountUseCase(uow, clock, notice_publisher, contact)
