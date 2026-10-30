from datetime import timedelta

from fastapi import Depends

from app.user_identity.application.use_cases.refresh_session import (
    RefreshSessionUseCase,
)
from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.application.use_cases.revoke_session import (
    RevokeSessionUseCase,
)
from app.user_identity.domain.ports.input.refresh_session_port import (
    RefreshSessionPort,
)
from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.domain.ports.input.revoke_session_port import RevokeSessionPort
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.infrastructure.clock.system_clock import SystemClock
from app.user_identity.infrastructure.database.session import async_session
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.user_identity.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from app.user_identity.infrastructure.security.secrets_refresh_token_generator import (
    SecretsRefreshTokenGenerator,
)
from config.settings import settings


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
