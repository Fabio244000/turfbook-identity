from app.user_identity.domain.entities.user import User
from app.user_identity.domain.exceptions import UserAlreadyExistsError
from app.user_identity.domain.ports.input.register_user_port import RegisterUserPort
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class RegisterUserUseCase(RegisterUserPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        hasher: PasswordHasherPort,
        token_issuer: TokenIssuerPort,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._token_issuer = token_issuer

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
    ) -> tuple[User, str]:
        user = User(
            first_name=first_name,
            last_name=last_name,
            cellphone=cellphone,
            username=username,
            password=password,
            email=email,
            facebook_token=facebook_token,
            gmail_token=gmail_token,
        )
        async with self._uow:
            await self._ensure_unique(user)
            if user.password:
                user.password = self._hasher.hash(user.password)
            await self._uow.users.add(user)
            await self._uow.commit()
        return user, self._token_issuer.issue(user.uuid)

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
