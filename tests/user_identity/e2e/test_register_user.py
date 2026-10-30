import re

import jwt

from config.settings import settings
from tests.user_identity.e2e.conftest import USERS_PATH, valid_user_payload

BASE64URL_256_BITS = re.compile(r'[A-Za-z0-9_-]{43}')


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


class TestRegisterUserDuplicates:
    async def test_returns_409_on_duplicate_username(self, client):
        first = valid_user_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH, json=valid_user_payload(username=first['username'])
        )

        assert response.status_code == 409
        assert response.json()['success'] is False

    async def test_invalid_data_is_rejected_before_looking_for_duplicates(self, client):
        first = valid_user_payload()
        await client.post(USERS_PATH, json=first)

        response = await client.post(
            USERS_PATH,
            json=valid_user_payload(username=first['username'], email='fabio-mail.com'),
        )

        assert response.status_code == 400


class TestRegisterUserInvalidData:
    async def test_returns_400_on_invalid_password(self, client):
        payload = valid_user_payload(password='short')

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 400

    async def test_returns_422_without_username_and_password_or_social_token(
        self, client
    ):
        payload = valid_user_payload(username=None, password=None)

        response = await client.post(USERS_PATH, json=payload)

        assert response.status_code == 422
