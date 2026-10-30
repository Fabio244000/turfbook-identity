from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from httpx import ASGITransport, AsyncClient

from app.user_identity.infrastructure.api.dependencies import (
    get_clock,
    get_unit_of_work,
)
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.main import app
from config.settings import settings
from tests.fakes.user_identity import FakeClock

# Public contract: written literally so an accidental prefix/version change fails here.
USERS_PATH = '/api/v1/users'


def valid_user_payload(**overrides: Any) -> dict[str, Any]:
    suffix = uuid4().hex[:8]
    data: dict[str, Any] = {
        'first_name': 'fabio',
        'last_name': 'nunez garcia',
        'cellphone': f'+51 9{uuid4().int % 10**8:08d}',
        'username': f'user{suffix}',
        'password': 'secretpass123',
        'email': f'user{suffix}@mail.com',
    }
    data.update(overrides)
    return data


@pytest.fixture
def clock() -> FakeClock:
    """Starts at the real time, so the tokens it stamps are valid today."""
    return FakeClock(datetime.now(UTC))


@pytest_asyncio.fixture
async def client(session_factory, clock):
    app.dependency_overrides[get_unit_of_work] = lambda: SqlAlchemyUnitOfWork(
        session_factory
    )
    app.dependency_overrides[get_clock] = lambda: clock
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered(client: AsyncClient) -> dict[str, Any]:
    """The `data` of a successful registration: the user and its session tokens."""
    response = await client.post(USERS_PATH, json=valid_user_payload())
    return dict(response.json()['data'])


@pytest.fixture(scope='session')
def public_key() -> str:
    """The public half of the configured key: what a consumer verifies with."""
    private_key = serialization.load_pem_private_key(
        settings.jwt_private_key.encode(), password=None
    )
    return (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
