from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.user import User
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.refresh_token_repository_port import (
    RefreshTokenRepositoryPort,
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

    async def exists_by_uuid(self, user_uuid: UUID) -> bool:
        return any(user.uuid == user_uuid for user in self.users)

    async def exists_by_username(self, username: str) -> bool:
        return any(user.username == username for user in self.users)

    async def exists_by_email(self, email: str) -> bool:
        return any(user.email == email for user in self.users)

    async def exists_by_cellphone(self, cellphone: str) -> bool:
        return any(user.cellphone == cellphone for user in self.users)


class FakeRefreshTokenRepository(RefreshTokenRepositoryPort):
    """Stores copies, like a database: a change the use case does not `update` is
    not kept, so a test cannot pass because two objects are the same instance."""

    def __init__(self, tokens: list[RefreshToken] | None = None) -> None:
        self.tokens = [replace(token) for token in tokens or []]

    async def add(self, token: RefreshToken) -> None:
        self.tokens.append(replace(token))

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        found = next((t for t in self.tokens if t.token_hash == token_hash), None)
        return replace(found) if found else None

    async def get_by_session(self, session_uuid: UUID) -> list[RefreshToken]:
        return [replace(t) for t in self.tokens if t.session_uuid == session_uuid]

    async def update(self, token: RefreshToken) -> None:
        index = next(i for i, t in enumerate(self.tokens) if t.uuid == token.uuid)
        self.tokens[index] = replace(token)

    def stored(self, token_hash: str) -> RefreshToken:
        return next(t for t in self.tokens if t.token_hash == token_hash)


class FakeUnitOfWork(UnitOfWorkPort):
    def __init__(
        self,
        users: list[User] | None = None,
        refresh_tokens: list[RefreshToken] | None = None,
    ) -> None:
        self.users = FakeUserRepository(users)
        self.refresh_tokens = FakeRefreshTokenRepository(refresh_tokens)
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


class FakeClock(ClockPort):
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class FakeRefreshTokenGenerator(RefreshTokenGeneratorPort):
    """Generates `refresh-1`, `refresh-2`… and hashes them as `hash-<token>`."""

    def __init__(self) -> None:
        self._count = 0

    def generate(self) -> str:
        self._count += 1
        return f'refresh-{self._count}'

    def hash(self, token: str) -> str:
        return f'hash-{token}'
