from datetime import datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.user_identity.accounts_main import app as accounts_app
from app.user_identity.infrastructure.api.dependencies import (
    get_block_account_use_case,
)
from config.settings import settings
from tests.user_identity.e2e.conftest import ACCOUNTS_PATH, error_body

NOT_AUTHORIZED = 'Not authorized.'


async def _change(
    accounts_client: AsyncClient, user_uuid: str, operation: str
) -> Response:
    return await accounts_client.patch(
        ACCOUNTS_PATH.format(user_uuid=user_uuid), json={'operation': operation}
    )


class TestChangeAccountStatus:
    async def test_blocks_an_account(self, accounts_client, registered, clock):
        user_uuid = registered['user']['uuid']

        response = await _change(accounts_client, user_uuid, 'block')

        assert response.status_code == 200
        assert response.json()['data'] == {
            'user_uuid': user_uuid,
            'status': 'blocked',
            'changed_at': clock.current.isoformat().replace('+00:00', 'Z'),
        }

    async def test_unblocks_an_account(self, accounts_client, registered):
        user_uuid = registered['user']['uuid']
        await _change(accounts_client, user_uuid, 'block')

        response = await _change(accounts_client, user_uuid, 'unblock')

        assert response.status_code == 200
        assert response.json()['data']['status'] == 'active'

    async def test_records_that_turfbook_made_the_change_and_when(
        self, accounts_client, registered, connection
    ):
        user_uuid = registered['user']['uuid']

        response = await _change(accounts_client, user_uuid, 'block')

        row = await connection.execute(
            text(
                'SELECT type, reason, actor, created_at FROM account_events'
                ' WHERE user_uuid = :uuid'
            ),
            {'uuid': user_uuid},
        )
        changed_at = datetime.fromisoformat(response.json()['data']['changed_at'])
        assert tuple(row.one()) == ('blocked', 'turfbook', 'turfbook', changed_at)


class TestChangeAccountStatusErrors:
    @pytest.mark.parametrize('api_key', [None, 'not-the-api-key'])
    async def test_rejects_a_missing_or_wrong_api_key(
        self, accounts_client, registered, api_key
    ):
        headers = {} if api_key is None else {'X-Api-Key': api_key}
        accounts_client.headers.pop('X-Api-Key')

        response = await accounts_client.patch(
            ACCOUNTS_PATH.format(user_uuid=registered['user']['uuid']),
            json={'operation': 'block'},
            headers=headers,
        )

        assert response.status_code == 401
        assert response.json() == error_body(NOT_AUTHORIZED)

    async def test_checks_the_api_key_before_the_data(self, accounts_client):
        accounts_client.headers.pop('X-Api-Key')

        response = await _change(accounts_client, 'not-a-uuid', 'delete')

        assert response.status_code == 401
        assert response.json() == error_body(NOT_AUTHORIZED)

    async def test_rejects_an_account_that_does_not_exist(self, accounts_client):
        response = await _change(accounts_client, str(uuid4()), 'block')

        assert response.status_code == 404
        assert response.json() == error_body('The account does not exist.')

    async def test_rejects_blocking_an_account_already_blocked(
        self, accounts_client, registered
    ):
        user_uuid = registered['user']['uuid']
        await _change(accounts_client, user_uuid, 'block')

        response = await _change(accounts_client, user_uuid, 'block')

        assert response.status_code == 409
        assert response.json() == error_body('The account is already blocked.')

    async def test_rejects_an_unknown_operation(self, accounts_client, registered):
        response = await _change(accounts_client, registered['user']['uuid'], 'delete')

        assert response.status_code == 422
        assert response.json() == error_body('Operation has an invalid value.')

    async def test_names_each_invalid_field_by_its_name(self, accounts_client):
        response = await _change(accounts_client, 'not-a-uuid', 'delete')

        assert response.status_code == 422
        assert response.json() == error_body(
            'There were problems with the submitted data.',
            [
                {'field': 'user_uuid', 'error': 'User UUID has an invalid value.'},
                {'field': 'operation', 'error': 'Operation has an invalid value.'},
            ],
        )

    async def test_answers_500_without_technical_detail(self):
        def _broken_use_case():
            raise RuntimeError('database is down: password=secret')

        accounts_app.dependency_overrides[get_block_account_use_case] = _broken_use_case
        transport = ASGITransport(app=accounts_app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.patch(
                ACCOUNTS_PATH.format(user_uuid=uuid4()),
                json={'operation': 'block'},
                headers={'X-Api-Key': settings.accounts_api_key},
            )
        accounts_app.dependency_overrides.clear()

        assert response.status_code == 500
        assert response.json() == error_body(
            'An unexpected error occurred. Please try again later.'
        )
