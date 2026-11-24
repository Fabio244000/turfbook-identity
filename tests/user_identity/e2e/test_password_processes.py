import logging
import time
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text

from app.user_identity.infrastructure.api.dependencies import get_minimum_duration
from app.user_identity.main import app
from tests.user_identity.e2e.conftest import (
    PASSWORD_RECOVERIES_PATH,
    PASSWORD_UPDATES_PATH,
    SECURITY_CODES_PATH,
    SESSIONS_PATH,
    TOKENS_PATH,
    bearer,
    error_body,
)

CURRENT_PASSWORD = 'GrassElSol2026!'
NEW_PASSWORD = 'CanchaVerde#Lima7'
WRONG_CODE = '999999'
INVALID_TOKEN = 'The session token is invalid.'
NOT_ALLOWED = 'It is not possible to start the process.'


def _data(registered: dict[str, Any]) -> dict[str, str]:
    user = registered['user']
    return {'cellphone': user['cellphone'], 'email': user['email']}


def _headers(path: str, registered: dict[str, Any]) -> dict[str, str]:
    return bearer(registered) if path == PASSWORD_UPDATES_PATH else {}


async def _request(
    client: AsyncClient, path: str, registered: dict[str, Any], **data: str
) -> Response:
    body = _data(registered) | data
    return await client.post(path, json=body, headers=_headers(path, registered))


async def _validate(
    client: AsyncClient, path: str, registered: dict[str, Any], process: str, code: str
) -> Response:
    return await client.post(
        f'{path}/{process}/validation',
        json={'code': code},
        headers=_headers(path, registered),
    )


async def _set(
    client: AsyncClient,
    path: str,
    registered: dict[str, Any],
    process: str,
    **body: str,
) -> Response:
    data = {'new_password': NEW_PASSWORD, 'new_password_confirmation': NEW_PASSWORD}
    if path == PASSWORD_UPDATES_PATH:
        data['current_password'] = CURRENT_PASSWORD
    return await client.put(
        f'{path}/{process}/password',
        json=data | body,
        headers=_headers(path, registered),
    )


async def _validated(
    client: AsyncClient, path: str, registered: dict[str, Any], notices: Any
) -> str:
    response = await _request(client, path, registered)
    process = str(response.json()['data']['process_uuid'])
    await _validate(client, path, registered, process, notices.sent[-1]['code'])
    return process


BOTH = [PASSWORD_UPDATES_PATH, PASSWORD_RECOVERIES_PATH]


class TestRequestPasswordCode:
    @pytest.mark.parametrize('path', BOTH)
    async def test_sends_a_code_by_email_and_sms_and_never_returns_it(
        self, client, registered, notice_publisher, path
    ):
        response = await _request(client, path, registered)

        assert response.status_code == 201
        assert set(response.json()['data']) == {'process_uuid', 'code_expires_at'}
        [notice] = notice_publisher.sent
        assert notice['notifiers'] == ['email', 'sms']
        assert notice['code'] not in response.text

    @pytest.mark.parametrize('path', BOTH)
    async def test_rejects_an_email_of_another_account(self, client, registered, path):
        response = await _request(client, path, registered, email='otro@gmail.com')

        assert response.status_code == 422
        assert response.json() == error_body(NOT_ALLOWED)

    async def test_normalizes_the_email_before_comparing_it(self, client, registered):
        email = f'  {registered["user"]["email"].upper()} '

        response = await _request(
            client, PASSWORD_RECOVERIES_PATH, registered, email=email
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        ('field', 'value', 'message'),
        [
            ('cellphone', '987654321', 'Cellphone has an invalid value.'),
            ('email', 'rosa@gmail', 'Email has an invalid value.'),
        ],
    )
    async def test_rejects_data_out_of_format(
        self, client, registered, field, value, message
    ):
        response = await _request(
            client, PASSWORD_RECOVERIES_PATH, registered, **{field: value}
        )

        assert response.status_code == 422
        assert response.json() == error_body(message)

    async def test_the_update_rejects_a_missing_session_token(self, client, registered):
        response = await client.post(PASSWORD_UPDATES_PATH, json=_data(registered))

        assert response.status_code == 401
        assert response.json() == error_body(INVALID_TOKEN)

    async def test_rejects_a_new_code_once_validated(
        self, client, registered, notice_publisher
    ):
        path = PASSWORD_RECOVERIES_PATH
        await _validated(client, path, registered, notice_publisher)

        response = await _request(client, path, registered)

        assert response.status_code == 409
        assert response.json() == error_body(
            'The security code was already validated. Set your new password.'
        )

    async def test_a_code_that_could_not_be_sent_answers_500(
        self, client, registered, notice_publisher
    ):
        notice_publisher.fails = True

        response = await _request(client, PASSWORD_RECOVERIES_PATH, registered)

        assert response.status_code == 500
        assert response.json() == error_body(
            'The security code could not be sent. Try again.'
        )


class TestRequestPasswordCodeTime:
    async def test_every_answer_takes_at_least_one_second(self, client, registered):
        app.dependency_overrides.pop(get_minimum_duration)
        cases = [
            {'email': 'otro@gmail.com'},
            {'cellphone': '+51900000999', 'email': 'nadie@gmail.com'},
            {},
        ]
        durations, statuses = [], []
        for data in cases:
            started = time.monotonic()
            response = await _request(
                client, PASSWORD_RECOVERIES_PATH, registered, **data
            )
            durations.append(time.monotonic() - started)
            statuses.append(response.status_code)

        assert statuses == [422, 422, 201]
        assert all(duration >= 1 for duration in durations)
        assert max(durations) - min(durations) < 0.5


class TestValidatePasswordCode:
    @pytest.mark.parametrize('path', BOTH)
    async def test_the_right_code_gives_the_deadline(
        self, client, registered, notice_publisher, clock, path
    ):
        response = await _request(client, path, registered)
        process = response.json()['data']['process_uuid']

        response = await _validate(
            client, path, registered, process, notice_publisher.sent[-1]['code']
        )

        assert response.status_code == 200
        expected = (clock.current + timedelta(minutes=5)).isoformat()
        assert response.json()['data'] == {
            'password_deadline': expected.replace('+00:00', 'Z')
        }

    async def test_rejects_a_wrong_code(self, client, registered):
        path = PASSWORD_RECOVERIES_PATH
        response = await _request(client, path, registered)
        process = response.json()['data']['process_uuid']

        response = await _validate(client, path, registered, process, WRONG_CODE)

        assert response.status_code == 422
        assert response.json() == error_body('The security code is incorrect.')

    async def test_rejects_a_process_that_does_not_exist(self, client, registered):
        response = await _validate(
            client, PASSWORD_RECOVERIES_PATH, registered, str(uuid4()), WRONG_CODE
        )

        assert response.status_code == 404
        assert response.json() == error_body('The process does not exist.')


class TestSetNewPassword:
    async def test_the_update_keeps_the_session(
        self, client, registered, notice_publisher
    ):
        path = PASSWORD_UPDATES_PATH
        process = await _validated(client, path, registered, notice_publisher)

        response = await _set(client, path, registered, process)

        assert response.status_code == 200
        assert response.json() == {
            'success': True,
            'message': '',
            'detail': None,
            'data': None,
        }
        renewed = await client.post(
            TOKENS_PATH, json={'refresh_token': registered['refresh_token']}
        )
        assert renewed.status_code == 200

    async def test_the_recovery_closes_the_session_and_signs_in_with_the_new_one(
        self, client, registered, notice_publisher
    ):
        path = PASSWORD_RECOVERIES_PATH
        process = await _validated(client, path, registered, notice_publisher)

        response = await _set(client, path, registered, process)

        assert response.status_code == 200
        renewed = await client.post(
            TOKENS_PATH, json={'refresh_token': registered['refresh_token']}
        )
        assert renewed.status_code == 401
        signed_in = await client.post(
            SESSIONS_PATH,
            json={
                'username': registered['user']['username'],
                'password': NEW_PASSWORD,
            },
        )
        assert signed_in.status_code == 201

    async def test_records_each_change_in_the_account_history(
        self, client, registered, notice_publisher, connection, clock
    ):
        changes = {
            PASSWORD_UPDATES_PATH: NEW_PASSWORD,
            PASSWORD_RECOVERIES_PATH: 'CanchaAzul#Cusco8',
        }
        for path, new_password in changes.items():
            process = await _validated(client, path, registered, notice_publisher)
            await _set(
                client,
                path,
                registered,
                process,
                new_password=new_password,
                new_password_confirmation=new_password,
            )
            clock.current += timedelta(minutes=1)

        rows = await connection.execute(
            text(
                'SELECT type, reason, actor, process_uuid IS NOT NULL FROM'
                ' account_events WHERE user_uuid = :uuid ORDER BY created_at'
            ),
            {'uuid': registered['user']['uuid']},
        )
        assert [tuple(row) for row in rows] == [
            ('password_updated', 'security_code', 'user', True),
            ('password_recovered', 'security_code', 'user', True),
        ]

    async def test_rejects_a_password_too_similar(
        self, client, registered, notice_publisher
    ):
        path = PASSWORD_UPDATES_PATH
        process = await _validated(client, path, registered, notice_publisher)

        response = await _set(
            client,
            path,
            registered,
            process,
            new_password='GrassElSol2026!!',
            new_password_confirmation='GrassElSol2026!!',
        )

        assert response.status_code == 422
        assert response.json() == error_body(
            'The new password is too similar to the current one.'
        )

    async def test_rejects_a_short_password(self, client, registered, notice_publisher):
        path = PASSWORD_RECOVERIES_PATH
        process = await _validated(client, path, registered, notice_publisher)

        response = await _set(
            client,
            path,
            registered,
            process,
            new_password='corta',
            new_password_confirmation='corta',
        )

        assert response.status_code == 422
        assert response.json() == error_body(
            'Password must be between 15 and 64 characters.'
        )

    async def test_the_update_requires_the_current_password(
        self, client, registered, notice_publisher
    ):
        path = PASSWORD_UPDATES_PATH
        process = await _validated(client, path, registered, notice_publisher)

        response = await client.put(
            f'{path}/{process}/password',
            json={
                'new_password': NEW_PASSWORD,
                'new_password_confirmation': NEW_PASSWORD,
            },
            headers=bearer(registered),
        )

        assert response.status_code == 422
        assert response.json() == error_body('Current password is required.')

    async def test_rejects_a_code_not_validated(self, client, registered):
        path = PASSWORD_RECOVERIES_PATH
        response = await _request(client, path, registered)
        process = response.json()['data']['process_uuid']

        response = await _set(client, path, registered, process)

        assert response.status_code == 409
        assert response.json() == error_body(
            'The security code has not been validated.'
        )

    async def test_after_the_deadline_the_process_fails(
        self, client, registered, notice_publisher, clock
    ):
        path = PASSWORD_RECOVERIES_PATH
        process = await _validated(client, path, registered, notice_publisher)
        clock.current += timedelta(minutes=6)

        response = await _set(client, path, registered, process)

        assert response.status_code == 409
        assert response.json() == error_body(
            'The time to set the new password has expired.'
        )

    async def test_the_update_rejects_a_missing_session_token(self, client):
        response = await client.put(
            f'{PASSWORD_UPDATES_PATH}/{uuid4()}/password', json={}
        )

        assert response.status_code == 401
        assert response.json() == error_body(INVALID_TOKEN)


class TestSupportWithAValidatedProcess:
    async def test_support_cannot_give_a_code(
        self, client, accounts_client, registered, notice_publisher
    ):
        await _validated(client, PASSWORD_RECOVERIES_PATH, registered, notice_publisher)

        response = await accounts_client.post(
            SECURITY_CODES_PATH,
            json={
                'cellphone': registered['user']['cellphone'],
                'process_type': 'password_recovery',
            },
        )

        assert response.status_code == 409
        assert response.json() == error_body(
            'The security code was already validated: the user must set the new '
            'password.'
        )


class TestPasswordsNeverLogged:
    async def test_codes_and_passwords_never_reach_the_logs(
        self, client, registered, notice_publisher, caplog
    ):
        with caplog.at_level(logging.DEBUG):
            update = await _validated(
                client, PASSWORD_UPDATES_PATH, registered, notice_publisher
            )
            await _set(client, PASSWORD_UPDATES_PATH, registered, update)
            recovery = await _validated(
                client, PASSWORD_RECOVERIES_PATH, registered, notice_publisher
            )
            await _set(
                client,
                PASSWORD_RECOVERIES_PATH,
                registered,
                recovery,
                new_password='CanchaAzul#Cusco8',
                new_password_confirmation='CanchaAzul#Cusco8',
            )

        codes = [notice['code'] for notice in notice_publisher.sent]
        secrets = [*codes, CURRENT_PASSWORD, NEW_PASSWORD, 'CanchaAzul#Cusco8']
        assert all(secret not in caplog.text for secret in secrets)
