from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient, Response

from config.settings import settings

# Public contract: written literally so an accidental prefix/version change fails here.
TOKENS_PATH = '/api/v1/tokens'
REVOKE_PATH = '/api/v1/tokens/revoke'
SESSION_EXPIRED = 'Your session has expired. Please sign in again.'


async def _refresh(client: AsyncClient, refresh_token: str) -> Response:
    return await client.post(TOKENS_PATH, json={'refresh_token': refresh_token})


class TestRefreshSession:
    async def test_renews_the_session_with_a_new_pair(
        self, client, registered, public_key
    ):
        response = await _refresh(client, registered['refresh_token'])

        assert response.status_code == 200
        data = response.json()['data']
        assert data['refresh_token'] != registered['refresh_token']
        claims = jwt.decode(data['token'], public_key, algorithms=['RS256'])
        assert claims['sub'] == registered['user']['uuid']
        assert data['expires_in'] == claims['exp'] - claims['iat']

    async def test_a_reused_refresh_token_ends_the_whole_session(
        self, client, registered
    ):
        renewed = await _refresh(client, registered['refresh_token'])

        reuse = await _refresh(client, registered['refresh_token'])

        assert reuse.status_code == 401
        assert reuse.json()['message'] == SESSION_EXPIRED
        renewed_token = renewed.json()['data']['refresh_token']
        assert (await _refresh(client, renewed_token)).status_code == 401

    async def test_an_expired_refresh_token_is_rejected(
        self, client, clock, registered
    ):
        clock.current += timedelta(days=settings.refresh_token_expire_days + 1)

        response = await _refresh(client, registered['refresh_token'])

        assert response.status_code == 401
        assert response.json()['message'] == SESSION_EXPIRED

    async def test_an_unknown_refresh_token_is_rejected(self, client):
        response = await _refresh(client, 'not-a-refresh-token')

        assert response.status_code == 401
        assert response.json()['success'] is False

    @pytest.mark.parametrize('path', [TOKENS_PATH, REVOKE_PATH])
    async def test_requires_a_refresh_token(self, client, path):
        response = await client.post(path, json={})

        assert response.status_code == 422


class TestRevokeSession:
    async def test_revoking_ends_the_session(self, client, registered):
        response = await client.post(
            REVOKE_PATH, json={'refresh_token': registered['refresh_token']}
        )

        assert response.status_code == 204
        assert response.content == b''
        assert (await _refresh(client, registered['refresh_token'])).status_code == 401

    async def test_revoking_an_unknown_token_answers_204(self, client):
        response = await client.post(
            REVOKE_PATH, json={'refresh_token': 'not-a-refresh-token'}
        )

        assert response.status_code == 204
