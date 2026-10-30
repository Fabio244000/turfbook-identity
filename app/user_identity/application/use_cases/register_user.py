from datetime import timedelta
from uuid import uuid4

from app.user_identity.application.sessions import issue_refresh_token
from app.user_identity.domain.entities.session_tokens import SessionTokens
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import UserAlreadyExistsError
from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class RegisterUserUseCase(RegisterUserPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        hasher: PasswordHasherPort,
        token_issuer: TokenIssuerPort,
        clock: ClockPort,
        refresh_token_generator: RefreshTokenGeneratorPort,
        refresh_token_ttl: timedelta,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_issuer = token_issuer
        self._clock = clock
        self._refresh_token_generator = refresh_token_generator
        self._refresh_token_ttl = refresh_token_ttl

    async def execute(
        self,
        first_name: str,
        last_name: str,
        cellphone: str,
        username: str | None = None,
        password: str | None = None,
        email: str | None = None,
        facebook_token: str | None = None,
        gmail_token: str | None = None,
    ) -> tuple[User, SessionTokens]:
        now = self._clock.now()
        user = User(
            first_name=first_name,
            last_name=last_name,
            cellphone=cellphone,
            username=username,
            password=password,
            email=email,
            created_at=now,
            updated_at=now,
            facebook_token=facebook_token,
            gmail_token=gmail_token,
        )
        async with self._uow:
            await self._ensure_unique(user)
            if user.password:
                user.password = self._hasher.hash(user.password)
            await self._uow.users.add(user)
            refresh_token = await issue_refresh_token(
                self._uow,
                self._refresh_token_generator,
                user_uuid=user.uuid,
                session_uuid=uuid4(),
                now=now,
                ttl=self._refresh_token_ttl,
            )
            await self._uow.commit()
        access_token = self._token_issuer.issue(user.uuid)
        return user, SessionTokens(access_token, refresh_token)

    async def _ensure_unique(self, user: User) -> None:
        users = self._uow.users
        if user.username and await users.exists_by_username(user.username):
            raise UserAlreadyExistsError(
                f'User with username {user.username} already exists.'
            )
        if await users.exists_by_cellphone(user.cellphone):
            raise UserAlreadyExistsError(
                f'User with cellphone {user.cellphone} already exists.'
            )
        if user.email and await users.exists_by_email(user.email):
            raise UserAlreadyExistsError(f'User with email {user.email} already exists')
