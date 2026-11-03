from typing import Any

from app.user_identity.application.messages import USER_ALREADY_EXISTS
from app.user_identity.domain.messages import (
    CELLPHONE_INVALID,
    EMAIL_INVALID,
    EMAIL_REQUIRED,
    IDENTIFIER_REQUIRED,
    PASSWORD_LENGTH,
)
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
    VALIDATION_FAILED,
)

_ROSA = {
    'first_name': 'rosa',
    'last_name': 'quispe huamán',
    'cellphone': '+51987654321',
    'username': 'rosaq',
    'password': 'GrassElSol2026!',
    'email': 'rosa.quispe@gmail.com',
}

REGISTER_USER_REQUEST_EXAMPLES: dict[str, Any] = {
    'valid': example('A valid registration', _ROSA),
    'invalid_cellphone': example(
        'Cellphone with a space (422)', {**_ROSA, 'cellphone': '+51 987654321'}
    ),
    'short_password': example(
        'Password shorter than 15 characters (422)',
        {**_ROSA, 'password': 'grass2026'},
    ),
}

_REGISTERED = {
    'success': True,
    'message': '',
    'detail': None,
    'data': {
        'token': ACCESS_TOKEN,
        'refresh_token': REFRESH_TOKEN,
        'expires_in': EXPIRES_IN,
        'user': {
            'first_name': 'rosa',
            'last_name': 'quispe huamán',
            'cellphone': '+51987654321',
            'username': 'rosaq',
            'email': 'rosa.quispe@gmail.com',
            'uuid': '7c9f3e1a-2b4d-4e6f-8a0b-1c2d3e4f5a6b',
            'created_at': '2026-11-03T15:00:00Z',
            'updated_at': '2026-11-03T15:00:00Z',
        },
    },
}


def _taken(field: str, value: str) -> dict[str, Any]:
    message = USER_ALREADY_EXISTS.format(field=field, value=value)
    return error_example(f'The {field} is taken', message)


REGISTER_USER_DOCS: dict[str, Any] = {
    'summary': 'Register a user',
    'responses': {
        201: {
            'description': 'User registered; its session starts.',
            'content': json_content(registered=example('Registered', _REGISTERED)),
        },
        409: error_response(
            'A unique field is already registered.',
            username=_taken('username', 'rosaq'),
            email=_taken('email', 'rosa.quispe@gmail.com'),
            cellphone=_taken('cellphone', '+51987654321'),
        ),
        422: error_response(
            'Invalid structure or a broken rule of the input.',
            one_rule=error_example('One broken rule', PASSWORD_LENGTH),
            several_rules=error_example(
                'Several broken rules',
                VALIDATION_FAILED,
                [
                    {'field': 'cellphone', 'error': CELLPHONE_INVALID},
                    {'field': 'email', 'error': EMAIL_INVALID},
                ],
            ),
            missing_email=error_example('Without email', EMAIL_REQUIRED),
            no_identifier=error_example(
                'Without username and password, or a social token',
                IDENTIFIER_REQUIRED,
            ),
            not_json=error_example('A body that is not JSON', BODY_NOT_JSON),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
