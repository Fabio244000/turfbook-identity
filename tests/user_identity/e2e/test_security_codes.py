from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text

from tests.user_identity.e2e.conftest import (
    EMAIL_VERIFICATIONS_PATH,
    SECURITY_CODES_PATH,
    bearer,
    error_body,
)


async def _support(
    accounts_client: AsyncClient, user_cellphone: str, **overrides: Any
) -> Response:
    payload = {'cellphone': user_cellphone, 'process_type': 'email_verification'}
    payload.update(overrides)
    return await accounts_client.post(SECURITY_CODES_PATH, json=payload)


class TestGetSecurityCode:
    async def test_shows_the_code_in_force(
        self, client, accounts_client, registered, notice_publisher
    ):
        started = await client.post(
            EMAIL_VERIFICATIONS_PATH, headers=bearer(registered)
        )

        response = await _support(accounts_client, registered['user']['cellphone'])

        assert response.status_code == 200
        assert response.json()['data'] == {
            'process_uuid': started.json()['data']['process_uuid'],
            'code': notice_publisher.sent[-1]['code'],
            'code_expires_at': started.json()['data']['code_expires_at'],
        }

    async def test_generates_a_code_when_the_last_one_expired(
        self, client, accounts_client, registered, clock, notice_publisher
    ):
        await client.post(EMAIL_VERIFICATIONS_PATH, headers=bearer(registered))
        clock.current += timedelta(minutes=40)

        response = await _support(accounts_client, registered['user']['cellphone'])

        assert response.status_code == 201
        assert response.json()['data']['code'] != notice_publisher.sent[-1]['code']
        assert len(notice_publisher.sent) == 1

    async def test_records_what_support_got_without_the_code(
        self, client, accounts_client, registered, clock, connection
    ):
        await client.post(EMAIL_VERIFICATIONS_PATH, headers=bearer(registered))
        shown = await _support(accounts_client, registered['user']['cellphone'])
        clock.current += timedelta(minutes=40)
        await _support(accounts_client, registered['user']['cellphone'])

        rows = await connection.execute(
            text(
                'SELECT type, reason, actor, process_uuid::text FROM account_events'
                ' WHERE user_uuid = :uuid ORDER BY created_at'
            ),
            {'uuid': registered['user']['uuid']},
        )
        process_uuid = shown.json()['data']['process_uuid']
        assert [tuple(row) for row in rows] == [
            ('support_code_shown', 'support_request', 'turfbook', process_uuid),
            ('support_code_generated', 'support_request', 'turfbook', process_uuid),
        ]


class TestGetSecurityCodeErrors:
    async def test_rejects_a_cellphone_without_account(self, accounts_client):
        response = await _support(accounts_client, '+51900000777')

        assert response.status_code == 404
        assert response.json() == error_body('The user does not exist.')

    async def test_rejects_a_user_without_a_process_in_progress(
        self, accounts_client, registered
    ):
        response = await _support(accounts_client, registered['user']['cellphone'])

        assert response.status_code == 404
        assert response.json() == error_body('There is no process in progress.')

    async def test_rejects_a_code_after_the_grace_period(
        self, client, accounts_client, registered, clock
    ):
        await client.post(EMAIL_VERIFICATIONS_PATH, headers=bearer(registered))
        clock.current += timedelta(minutes=5 + 60)

        response = await _support(accounts_client, registered['user']['cellphone'])

        assert response.status_code == 409
        assert response.json() == error_body(
            'The grace period has ended: support cannot generate a security code.'
        )

    async def test_rejects_a_missing_api_key(self, accounts_client):
        accounts_client.headers.pop('X-Api-Key')

        response = await _support(accounts_client, '+51900000777')

        assert response.status_code == 401
        assert response.json() == error_body('Not authorized.')

    @pytest.mark.parametrize(
        ('field', 'value', 'message'),
        [
            ('cellphone', '987654321', 'Cellphone has an invalid value.'),
            ('process_type', 'login', 'Process type has an invalid value.'),
        ],
    )
    async def test_rejects_data_out_of_format(
        self, accounts_client, field, value, message
    ):
        response = await _support(accounts_client, '+51900000777', **{field: value})

        assert response.status_code == 422
        assert response.json() == error_body(message)
