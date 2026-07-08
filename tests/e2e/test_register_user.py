import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.session import get_session
from app.main import app


def _valid_payload(**overrides):
    data = {
        'first_name': 'fabio',
        'last_name': 'nunez garcia',
        'cellphone': '+51 987654321',
        'username': 'fabio01',
        'password': 'secretpass123',
        'email': 'fabio@mail.com',
    }
    data.update(overrides)
    return data


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url='http://test')
    app.dependency_overrides.clear()


class TestRegisterUserEndpoint:
    async def test_returns_201_and_token_on_success(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload())

        print(response.status_code)
        print(response.json())
        assert response.status_code == 201
        body = response.json()
        assert body['success'] is True
        assert 'token' in body['data']

    async def test_response_does_not_expose_password(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload())
        body = response.json()
        assert 'password' not in body['data']['user']

    async def test_returns_400_on_duplicate_username(self, client):
        async with client:
            await client.post(
                '/users',
                json=_valid_payload(
                    username='dup', cellphone='+51 911111111', email='a@mail.com'
                ),
            )
            response = await client.post(
                '/users',
                json=_valid_payload(
                    username='dup', cellphone='+51 922222222', email='b@mail.com'
                ),
            )
        assert response.status_code == 409
        assert response.json()['success'] is False

    async def test_returns_400_on_invalid_password(self, client):
        async with client:
            response = await client.post(
                '/users', json=_valid_payload(password='short')
            )
        assert response.status_code == 400

    async def test_returns_422_on_missing_identifier(self, client):
        async with client:
            response = await client.post(
                '/users', json=_valid_payload(username=None, password=None)
            )
        assert response.status_code == 422

    async def test_returns_201_without_email(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload(email=None))
        assert response.status_code == 201

    async def test_returns_400_on_duplicate_email(self, client):
        async with client:
            await client.post(
                '/users',
                json=_valid_payload(
                    username='user_a', cellphone='+51 911111111', email='same@mail.com'
                ),
            )
            response = await client.post(
                '/users',
                json=_valid_payload(
                    username='user_b', cellphone='+51 922222222', email='same@mail.com'
                ),
            )
        assert response.status_code == 400

    async def test_returns_400_on_duplicate_cellphone(self, client):
        async with client:
            await client.post(
                '/users',
                json=_valid_payload(
                    username='user_a', cellphone='+51 911111111', email='a@mail.com'
                ),
            )
            response = await client.post(
                '/users',
                json=_valid_payload(
                    username='user_b', cellphone='+51 911111111', email='b@mail.com'
                ),
            )
        assert response.status_code == 400

    async def test_returns_422_on_missing_first_name(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload(first_name=None))
        assert response.status_code == 422

    async def test_returns_422_on_missing_last_name(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload(last_name=None))
        assert response.status_code == 422

    async def test_returns_422_on_missing_cellphone(self, client):
        async with client:
            response = await client.post('/users', json=_valid_payload(cellphone=None))
        assert response.status_code == 422
