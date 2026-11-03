from typing import Any

from app.user_identity.domain.messages import SESSION_EXPIRED
from app.user_identity.infrastructure.api.api_docs.examples import (
    ACCESS_TOKEN,
    EXPIRES_IN,
    NEW_REFRESH_TOKEN,
    REFRESH_TOKEN,
    UNEXPECTED_ERROR_RESPONSE,
    error_example,
    error_response,
    example,
    json_content,
)
from app.user_identity.infrastructure.api.messages import FIELD_LABELS, FIELD_REQUIRED

REFRESH_TOKEN_REQUEST_EXAMPLES: dict[str, Any] = {
    'valid': example(
        'The refresh token of the session', {'refresh_token': REFRESH_TOKEN}
    ),
}

_MISSING_REFRESH_TOKEN = error_response(
    'The body has no refresh token.',
    missing=error_example(
        'Without refresh token',
        FIELD_REQUIRED.format(label=FIELD_LABELS['refresh_token']),
    ),
)

_RENEWED = {
    'success': True,
    'message': '',
    'detail': None,
    'data': {
        'token': ACCESS_TOKEN,
        'refresh_token': NEW_REFRESH_TOKEN,
        'expires_in': EXPIRES_IN,
    },
}

REFRESH_SESSION_DOCS: dict[str, Any] = {
    'summary': 'Renew the session',
    'responses': {
        200: {
            'description': 'A new pair; the refresh token sent can no longer be used.',
            'content': json_content(renewed=example('Renewed', _RENEWED)),
        },
        401: error_response(
            'The refresh token is unknown, expired, revoked or already used: the '
            'user signs in again. One text whatever the cause.',
            expired=error_example('Session expired', SESSION_EXPIRED),
        ),
        422: _MISSING_REFRESH_TOKEN,
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}

REVOKE_SESSION_DOCS: dict[str, Any] = {
    'summary': 'Sign out',
    'responses': {
        204: {
            'description': 'Session closed; also when it was already closed, expired '
            'or the token is unknown.'
        },
        422: _MISSING_REFRESH_TOKEN,
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
