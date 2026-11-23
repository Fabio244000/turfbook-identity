import logging
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text

from tests.user_identity.e2e.conftest import (
    ACCOUNTS_PATH,
    EMAIL_VERIFICATIONS_PATH,
    SECURITY_CODES_PATH,
    VALIDATION_PATH,
    bearer,
    error_body,
)

INVALID_TOKEN = 'The session token is invalid.'
WRONG_CODE = '999999'


async def _request(client: AsyncClient, registered: dict[str, Any]) -> Response:
    return await client.post(EMAIL_VERIFICATIONS_PATH, headers=bearer(registered))


async def _validate(
    client: AsyncClient, registered: dict[str, Any], process_uuid: str, code: Any
) -> Response:
    return await client.post(
        VALIDATION_PATH.format(process_uuid=process_uuid),
        json={'code': code},
        headers=bearer(registered),
    )


async def _started(client: AsyncClient, registered: dict[str, Any]) -> str:
    response = await _request(client, registered)
    return str(response.json()['data']['process_uuid'])


class TestRequestEmailVerification:
    async def test_sends_a_code_to_the_email_and_never_returns_it(
        self, client, registered, clock, notice_publisher
    ):
        response = await _request(client, registered)

        assert response.status_code == 201
        data = response.json()['data']
        assert set(data) == {'process_uuid', 'code_expires_at'}
        expected = (clock.current + timedelta(minutes=5)).isoformat()
        assert data['code_expires_at'] == expected.replace('+00:00', 'Z')
        [notice] = notice_publisher.sent
        assert notice['notifiers'] == ['email']
        assert notice['code'] not in response.text

    async def test_rejects_a_blocked_account(self, client, accounts_client, registered):
        user_uuid = registered['user']['uuid']
        await accounts_client.patch(
            ACCOUNTS_PATH.format(user_uuid=user_uuid), json={'operation': 'block'}
        )

        response = await _request(client, registered)

        assert response.status_code == 422
        assert response.json() == error_body('It is not possible to start the process.')

    async def test_rejects_an_email_already_verified(
        self, client, registered, notice_publisher
    ):
        process_uuid = await _started(client, registered)
        code = notice_publisher.sent[-1]['code']
        await _validate(client, registered, process_uuid, code)

        response = await _request(client, registered)

        assert response.status_code == 409
        assert response.json() == error_body('The email is already verified.')

    async def test_a_code_that_could_not_be_sent_answers_500(
        self, client, registered, notice_publisher
    ):
        notice_publisher.fails = True

        response = await _request(client, registered)

        assert response.status_code == 500
        assert response.json() == error_body(
            'The security code could not be sent. Try again.'
        )

    @pytest.mark.parametrize('token', [None, 'not-a-token'])
    async def test_rejects_a_missing_or_invalid_session_token(self, client, token):
        headers = {} if token is None else {'Authorization': f'Bearer {token}'}

        response = await client.post(EMAIL_VERIFICATIONS_PATH, headers=headers)

        assert response.status_code == 401
        assert response.json() == error_body(INVALID_TOKEN)


class TestValidateEmailVerification:
    async def test_the_right_code_verifies_the_email_and_records_it(
        self, client, registered, notice_publisher, connection
    ):
        process_uuid = await _started(client, registered)
        code = notice_publisher.sent[-1]['code']

        response = await _validate(client, registered, process_uuid, f' {code} ')

        assert response.status_code == 200
        assert response.json() == {
            'success': True,
            'message': '',
            'detail': None,
            'data': None,
        }
        user = await connection.execute(
            text('SELECT email_verified_at FROM users WHERE uuid = :uuid'),
            {'uuid': registered['user']['uuid']},
        )
        assert user.scalar_one() is not None
        event = await connection.execute(
            text(
                'SELECT type, reason, actor, process_uuid::text FROM account_events'
                ' WHERE user_uuid = :uuid'
            ),
            {'uuid': registered['user']['uuid']},
        )
        assert tuple(event.one()) == (
            'email_verified',
            'security_code',
            'user',
            process_uuid,
        )

    async def test_rejects_a_wrong_code(self, client, registered):
        process_uuid = await _started(client, registered)

        response = await _validate(client, registered, process_uuid, WRONG_CODE)

        assert response.status_code == 422
        assert response.json() == error_body('The security code is incorrect.')

    async def test_rejects_an_expired_code(
        self, client, registered, clock, notice_publisher
    ):
        process_uuid = await _started(client, registered)
        clock.current += timedelta(minutes=6)

        response = await _validate(
            client, registered, process_uuid, notice_publisher.sent[-1]['code']
        )

        assert response.status_code == 422
        assert response.json() == error_body('The security code has expired.')

    async def test_rejects_a_code_whose_attempts_were_spent(self, client, registered):
        process_uuid = await _started(client, registered)
        for _ in range(3):
            await _validate(client, registered, process_uuid, WRONG_CODE)

        response = await _validate(client, registered, process_uuid, WRONG_CODE)

        assert response.status_code == 409
        assert response.json() == error_body('You can no longer validate the code.')

    async def test_rejects_a_process_that_is_not_of_the_user(self, client, registered):
        response = await _validate(client, registered, str(uuid4()), WRONG_CODE)

        assert response.status_code == 404
        assert response.json() == error_body('The process does not exist.')

    @pytest.mark.parametrize(
        ('code', 'message'),
        [
            ('48291', 'Security code has an invalid value.'),
            ('48291a', 'Security code has an invalid value.'),
            (None, 'Security code is required.'),
        ],
    )
    async def test_rejects_a_code_that_is_not_six_digits(
        self, client, registered, code, message
    ):
        process_uuid = await _started(client, registered)

        response = await _validate(client, registered, process_uuid, code)

        assert response.status_code == 422
        assert response.json() == error_body(message)

    async def test_rejects_a_process_uuid_that_is_not_a_uuid(self, client, registered):
        response = await _validate(client, registered, 'not-a-uuid', WRONG_CODE)

        assert response.status_code == 422
        assert response.json() == error_body('Process UUID has an invalid value.')

    async def test_an_invalid_token_is_answered_before_the_data(self, client):
        response = await client.post(
            VALIDATION_PATH.format(process_uuid='not-a-uuid'),
            json={'code': 'x'},
            headers={'Authorization': 'Bearer not-a-token'},
        )

        assert response.status_code == 401
        assert response.json() == error_body(INVALID_TOKEN)


class TestSecurityCodeNeverLogged:
    async def test_a_whole_process_never_writes_the_code_in_the_logs(
        self, client, accounts_client, registered, notice_publisher, caplog
    ):
        with caplog.at_level(logging.DEBUG):
            process_uuid = await _started(client, registered)
            code = notice_publisher.sent[-1]['code']
            await _validate(client, registered, process_uuid, WRONG_CODE)
            support = await accounts_client.post(
                SECURITY_CODES_PATH,
                json={
                    'cellphone': registered['user']['cellphone'],
                    'process_type': 'email_verification',
                },
            )
            await _validate(client, registered, process_uuid, code)

        assert support.json()['data']['code'] == code
        assert code not in caplog.text
