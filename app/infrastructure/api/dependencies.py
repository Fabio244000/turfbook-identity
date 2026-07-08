from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.register_user import RegisterUserUseCase
from app.domain.ports.output.password_hasher_port import PasswordHasherPort
from app.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.domain.ports.output.user_repository_port import UserRepositoryPort
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_session
from app.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from app.infrastructure.security.jwt_token_issuer import JwtTokenIssuer


def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepositoryPort:
    return UserRepository(session)


def get_jwt_token_issuer() -> TokenIssuerPort:
    return JwtTokenIssuer()


def get_password_hasher() -> PasswordHasherPort:
    return Argon2PasswordHasher()


def get_register_user_use_case(
    user_repository: UserRepositoryPort = Depends(get_user_repository),
    token_issuer: TokenIssuerPort = Depends(get_jwt_token_issuer),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(
        user_repository=user_repository,
        token_issuer=token_issuer,
        hasher=password_hasher,
    )
