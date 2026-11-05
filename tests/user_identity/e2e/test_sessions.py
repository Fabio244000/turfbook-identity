from typing import Any

import jwt
from httpx import AsyncClient, Response

from config.settings import settings
from tests.user_identity.e2e.conftest import USERS_PATH, valid_user_payload

# Public contract: written literally so an accidental prefix/version change fails here.
SESSIONS_PATH = '/api/v1/sessions'
TOKENS_PATH = '/api/v1/tokens'
PASSWORD = 'GrassElSol2026!'
INVALID_CREDENTIALS = 'Incorrect username or password.'
SESSION_EXPIRED = 'Your session has expired. Please sign in again.'


def _error(message: str, detail: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {'success': False, 'message': message, 'detail': detail, 'data': None}


async def _register(client: AsyncClient) -> dict[str, Any]:
    payload = valid_user_payload(password=PASSWORD)
    response = await client.post(USERS_PATH, json=payload)
    return dict(response.json()['data']['user'])


async def _sign_in(client: AsyncClient, username: str, password: str) -> Response:
    return await client.post(
        SESSIONS_PATH, json={'username': username, 'password': password}
    )


async def _refresh(client: AsyncClient, refresh_token: str) -> Response:
    return await client.post(TOKENS_PATH, json={'refresh_token': refresh_token})


class TestStartSession:
    async def test_signs_in_with_the_right_credentials(self, client, public_key):
        user = await _register(client)

        response = await _sign_in(client, user['username'], PASSWORD)

        assert response.status_code == 201
        data = response.json()['data']
        claims = jwt.decode(data['token'], public_key, algorithms=['RS256'])
        assert claims['sub'] == user['uuid']
        assert data['expires_in'] == settings.access_token_expire_minutes * 60
        assert (await _refresh(client, data['refresh_token'])).status_code == 200

    async def test_wrong_credentials_answer_401(self, client):
        user = await _register(client)

        response = await _sign_in(client, user['username'], 'GrassElSol2026')

        assert response.status_code == 401
        assert response.json() == _error(INVALID_CREDENTIALS)

    async def test_requires_a_password(self, client):
        response = await client.post(SESSIONS_PATH, json={'username': 'rosaquispe'})

        assert response.status_code == 422
        assert response.json() == _error('Password is required.')

    async def test_signing_in_on_another_device_ends_the_previous_session(self, client):
        user = await _register(client)
        phone = await _sign_in(client, user['username'], PASSWORD)

        tablet = await _sign_in(client, user['username'], PASSWORD)

        phone_refresh = await _refresh(client, phone.json()['data']['refresh_token'])
        assert phone_refresh.status_code == 401
        assert phone_refresh.json()['message'] == SESSION_EXPIRED
        tablet_refresh = await _refresh(client, tablet.json()['data']['refresh_token'])
        assert tablet_refresh.status_code == 200


class TestStartSessionBlock:
    async def test_five_failures_block_the_account_and_notify_the_user(
        self, client, notice_publisher
    ):
        user = await _register(client)
        failures = [
            await _sign_in(client, user['username'], 'wrong')
            for _ in range(settings.max_failed_attempts)
        ]

        response = await _sign_in(client, user['username'], PASSWORD)

        assert [failure.status_code for failure in failures] == [401] * 5
        assert response.status_code == 403
        assert response.json() == _error(
            f'Your account is blocked. Contact TurfBook at '
            f'{settings.turfbook_contact_phone} or {settings.turfbook_contact_email}.'
        )
        [notice] = notice_publisher.published
        assert str(notice.recipient.uuid) == user['uuid']
