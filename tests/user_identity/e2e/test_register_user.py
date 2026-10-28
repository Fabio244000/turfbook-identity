from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.user_identity.infrastructure.api.dependencies import get_unit_of_work
from app.user_identity.infrastructure.database.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from app.user_identity.main import app

# Public contract: written literally so an accidental prefix/version change fails here.
USERS_PATH = '/api/v1/users'


def _valid_payload(**overrides):
    suffix = uuid4().hex[:8]
    data = {
        'first_name': 'fabio',
        'last_name': 'nunez garcia',
        'cellphone': f'+51 9{uuid4().int % 10**8:08d}',
        'username': f'user{suffix}',
        'password': 'secretpass123',
        'email': f'user{suffix}@mail.com',
    }
    data.update(overrides)
    return data


@pytest_asyncio.fixture
async def client(session_factory):
    app.dependency_overrides[get_unit_of_work] = lambda: SqlAlchemyUnitOfWork(
        session_factory
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        yield client
    app.dependency_overrides.clear()


class TestRegisterUser:
    async def test_returns_201_with_the_user_and_a_session_token(self, client):
        payload = _valid_payload()

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body['success'] is True
        assert body['data']['user']['username'] == payload['username']
        assert body['data']['token']

    async def test_does_not_expose_the_password(self, client):
        payload = _valid_payload()

        response = await client.post(USERS_PATH, json=payload)

        assert 'password' not in response.json()['data']['user']

    async def test_registers_without_email(self, client):
        payload = _valid_payload(email=None)

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 201


class TestRegisterUserDuplicates:
    async def test_returns_409_on_duplicate_username(self, client):
        first = _valid_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH, json=_valid_payload(username=first['username'])
        )

        assert response.status_code == 409
        assert response.json()['success'] is False

    async def test_returns_409_on_duplicate_email(self, client):
        first = _valid_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH, json=_valid_payload(email=first['email'])
        )

        assert response.status_code == 409

    async def test_returns_409_on_duplicate_cellphone(self, client):
        first = _valid_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH, json=_valid_payload(cellphone=first['cellphone'])
        )

        assert response.status_code == 409


class TestRegisterUserInvalidData:
    async def test_returns_400_on_invalid_password(self, client):
        payload = _valid_payload(password='short')

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 400

    async def test_returns_422_without_username_and_password_or_social_token(
        self, client
    ):
        payload = _valid_payload(username=None, password=None)

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize('field', ['first_name', 'last_name', 'cellphone'])
    async def test_returns_422_when_a_required_field_is_missing(self, client, field):
        payload = _valid_payload(**{field: None})

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
