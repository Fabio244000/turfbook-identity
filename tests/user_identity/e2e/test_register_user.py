import re

import jwt
from httpx import ASGITransport, AsyncClient

from app.user_identity.infrastructure.api.dependencies import get_register_user_use_case
from app.user_identity.main import app
from config.settings import settings
from tests.user_identity.e2e.conftest import USERS_PATH, error_body, valid_user_payload

BASE64URL_256_BITS = re.compile(r'[A-Za-z0-9_-]{43}')
VALIDATION_FAILED = 'There were problems with the submitted data.'


class TestRegisterUser:
    async def test_returns_201_with_the_user_and_a_session(self, client):
        payload = valid_user_payload()

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body['success'] is True
        assert body['data']['user']['username'] == payload['username']
        assert BASE64URL_256_BITS.fullmatch(body['data']['refresh_token'])

    async def test_the_session_token_is_rs256_for_the_registered_user(
        self, client, public_key
    ):
        response = await client.post(USERS_PATH, json=valid_user_payload())

        data = response.json()['data']
        claims = jwt.decode(data['token'], public_key, algorithms=['RS256'])
        assert claims['sub'] == data['user']['uuid']
        assert claims['iss'] == 'turfbook-identity'

    async def test_expires_in_is_the_lifetime_of_the_session_token(
        self, client, public_key
    ):
        response = await client.post(USERS_PATH, json=valid_user_payload())

        data = response.json()['data']
        claims = jwt.decode(data['token'], public_key, algorithms=['RS256'])
        assert data['expires_in'] == settings.access_token_expire_minutes * 60
        assert data['expires_in'] == claims['exp'] - claims['iat']

    async def test_does_not_expose_the_password(self, client):
        payload = valid_user_payload()

        response = await client.post(USERS_PATH, json=payload)

        assert 'password' not in response.json()['data']['user']

    async def test_stores_the_email_trimmed_and_in_lowercase(self, client):
        payload = valid_user_payload()
        payload['email'] = f'  {payload["username"].upper()}@Gmail.com '

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 201
        stored = response.json()['data']['user']['email']
        assert stored == f'{payload["username"]}@gmail.com'


class TestRegisterUserDuplicates:
    async def test_returns_409_on_duplicate_username(self, client):
        first = valid_user_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH, json=valid_user_payload(username=first['username'])
        )

        assert response.status_code == 409
        assert response.json() == error_body(
            f'User with username {first["username"]} already exists.'
        )

    async def test_invalid_data_is_rejected_before_looking_for_duplicates(self, client):
        first = valid_user_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH,
            json=valid_user_payload(username=first['username'], email='fabio-mail.com'),
        )

        assert response.status_code == 422


class TestRegisterUserInvalidData:
    async def test_one_broken_rule_answers_422_with_its_message(self, client):
        payload = valid_user_payload(password='short')

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
        assert response.json() == error_body(
            'Password must be between 15 and 64 characters.'
        )

    async def test_several_broken_rules_are_listed_by_field(self, client):
        payload = valid_user_payload(password='short', email='fabio-mail.com')

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
        assert response.json() == error_body(
            VALIDATION_FAILED,
            [
                {
                    'field': 'password',
                    'error': 'Password must be between 15 and 64 characters.',
                },
                {'field': 'email', 'error': 'Email is invalid.'},
            ],
        )

    async def test_a_registration_without_email_answers_422(self, client):
        payload = valid_user_payload()
        del payload['email']

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
        assert response.json() == error_body('Email is required.')

    async def test_returns_422_without_username_and_password_or_social_token(
        self, client
    ):
        payload = valid_user_payload(username=None, password=None)

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
        assert response.json()['detail'] is None

    async def test_several_missing_fields_are_listed_by_field(self, client):
        payload = valid_user_payload()
        del payload['first_name'], payload['last_name']

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
        assert response.json() == error_body(
            VALIDATION_FAILED,
            [
                {'field': 'first_name', 'error': 'First name is required.'},
                {'field': 'last_name', 'error': 'Last name is required.'},
            ],
        )


class TestRegisterUserUnexpectedError:
    async def test_answers_500_without_technical_detail(self):
        def _broken_use_case():
            raise RuntimeError('database is down: password=secret')

        app.dependency_overrides[get_register_user_use_case] = _broken_use_case
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.post(USERS_PATH, json=valid_user_payload())
        app.dependency_overrides.clear()

        assert response.status_code == 500
        assert response.json() == error_body(
            'An unexpected error occurred. Please try again later.'
        )
