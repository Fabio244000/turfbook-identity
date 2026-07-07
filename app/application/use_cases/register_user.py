from app.domain.entities.user import User
from app.domain.exceptions import UserAlreadyExistsError
from app.domain.ports.output.password_hasher_port import PasswordHasherPort
from app.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.domain.ports.output.user_repository_port import UserRepositoryPort


class RegisterUserUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        hasher: PasswordHasherPort,
        token_issuer: TokenIssuerPort,
    ) -> None:
        self._user_repository = user_repository
        self._hasher = hasher
        self._token_issuer = token_issuer

    def execute(
        self,
        first_name: str,
        last_name: str,
        cellphone: str,
        username: str | None = None,
        password: str | None = None,
        email: str | None = None,
    ) -> tuple[User, str]:
        self._verify_already_exists_user_with_unique_fields(
            username=username, cellphone=cellphone, email=email
        )
        user = User(
            first_name=first_name,
            last_name=last_name,
            cellphone=cellphone,
            username=username,
            password=password,
            email=email,
        )

        if user.password:
            user.password = self._hasher.hash(user.password)
        self._user_repository.save(user)
        sesion_token = self._token_issuer.issue(user.uuid)

        return user, sesion_token

    def _verify_already_exists_user_with_unique_fields(
        self, cellphone: str, username: str | None = None, email: str | None = None
    ) -> None:
        if username and self._user_repository.exists_by_username(username):
            raise UserAlreadyExistsError(
                f'User with username {username} already exists.'
            )

        if self._user_repository.exists_by_cellphone(cellphone):
            raise UserAlreadyExistsError(
                f'User with cellphone {cellphone} already exists.'
            )

        if email and self._user_repository.exists_by_email(email):
            raise UserAlreadyExistsError(f'User with email {email} already exists.')
