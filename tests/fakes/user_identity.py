from uuid import UUID

from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort
from app.user_identity.domain.ports.output.user_repository_port import (
    UserRepositoryPort,
)


class FakeUserRepository(UserRepositoryPort):
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = list(users or [])

    async def add(self, user: User) -> None:
        self.users.append(user)

    async def exists_by_username(self, username: str) -> bool:
        return any(user.username == username for user in self.users)

    async def exists_by_email(self, email: str) -> bool:
        return any(user.email == email for user in self.users)

    async def exists_by_cellphone(self, cellphone: str) -> bool:
        return any(user.cellphone == cellphone for user in self.users)


class FakeUnitOfWork(UnitOfWorkPort):
    def __init__(self, users: list[User] | None = None):
        self.users = FakeUserRepository(users)
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


class FakeHasher(PasswordHasherPort):
    def hash(self, password: str) -> str:
        return f'hashed-{password}'

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == self.hash(password)


class FakeTokenIssuer(TokenIssuerPort):
    def issue(self, user_uuid: UUID) -> str:
        return f'token-{user_uuid}'
