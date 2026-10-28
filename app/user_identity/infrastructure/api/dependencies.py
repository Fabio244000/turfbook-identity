from fastapi import Depends

from app.user_identity.application.use_cases.register_user import RegisterUserUseCase
from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.infrastructure.database.session import async_session
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.infrastructure.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.user_identity.infrastructure.security.jwt_token_issuer import JwtTokenIssuer


def get_unit_of_work() -> UnitOfWorkPort:
    return SqlAlchemyUnitOfWork(async_session)


def get_jwt_issuer() -> TokenIssuerPort:
    return JwtTokenIssuer()


def get_password_hasher() -> PasswordHasherPort:
    return Argon2PasswordHasher()


def get_register_user_use_case(
    uow: UnitOfWorkPort = Depends(get_unit_of_work),
    token_issuer: TokenIssuerPort = Depends(get_jwt_issuer),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
) -> RegisterUserPort:
    return RegisterUserUseCase(
        uow=uow,
        hasher=password_hasher,
        token_issuer=token_issuer,
    )
