from typing import Any

from app.user_identity.domain.messages import ACCOUNT_BLOCKED, INVALID_CREDENTIALS
from app.user_identity.infrastructure.api.api_docs.examples import (
    ACCESS_TOKEN,
    EXPIRES_IN,
    REFRESH_TOKEN,
    UNEXPECTED_ERROR_RESPONSE,
    error_example,
    error_response,
    example,
    json_content,
)
from app.user_identity.infrastructure.api.messages import (
    BODY_NOT_JSON,
    FIELD_LABELS,
    FIELD_REQUIRED,
    VALIDATION_FAILED,
)

_ROSA = {'username': 'rosaquispe', 'password': 'GrassElSol2026!'}

START_SESSION_REQUEST_EXAMPLES: dict[str, Any] = {
    'valid': example('The username and password of the account', _ROSA),
    'wrong_password': example(
        'A wrong password (401)', {**_ROSA, 'password': 'GrassElSol2026'}
    ),
}

_STARTED = {
    'success': True,
    'message': '',
    'detail': None,
    'data': {
        'token': ACCESS_TOKEN,
        'refresh_token': REFRESH_TOKEN,
        'expires_in': EXPIRES_IN,
    },
}


def _required(field: str) -> str:
    return FIELD_REQUIRED.format(label=FIELD_LABELS[field])


START_SESSION_DOCS: dict[str, Any] = {
    'summary': 'Sign in',
    'responses': {
        201: {
            'description': 'Session started; the previous sessions of the user end.',
            'content': json_content(started=example('Signed in', _STARTED)),
        },
        401: error_response(
            'Wrong credentials, whatever failed: unknown username, wrong password, '
            'an account without password or a closed account. The fifth failure of '
            'the day in a row blocks the account and still answers this; the user '
            'learns it by email and SMS.',
            wrong=error_example('Incorrect username or password', INVALID_CREDENTIALS),
        ),
        403: error_response(
            'The account is blocked and the password is right.',
            blocked=error_example(
                'Account blocked',
                ACCOUNT_BLOCKED.format(
                    phone='+51 999999998', email='turfbook@gmail.com'
                ),
            ),
        ),
        422: error_response(
            'The username or the password is missing or is not text.',
            one_field=error_example('Without password', _required('password')),
            both_fields=error_example(
                'Without username and password',
                VALIDATION_FAILED,
                [
                    {'field': 'username', 'error': _required('username')},
                    {'field': 'password', 'error': _required('password')},
                ],
            ),
            not_json=error_example('A body that is not JSON', BODY_NOT_JSON),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
