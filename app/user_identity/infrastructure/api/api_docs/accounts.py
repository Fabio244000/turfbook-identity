from typing import Any

from app.user_identity.application.messages import ACCOUNT_NOT_FOUND
from app.user_identity.domain.messages import (
    ACCOUNT_ALREADY_BLOCKED,
    ACCOUNT_CLOSED,
    ACCOUNT_NOT_BLOCKED,
)
from app.user_identity.infrastructure.api.api_docs.examples import (
    UNEXPECTED_ERROR_RESPONSE,
    error_example,
    error_response,
    example,
    json_content,
)
from app.user_identity.infrastructure.api.messages import (
    BODY_NOT_JSON,
    FIELD_INVALID,
    FIELD_LABELS,
    NOT_AUTHORIZED,
    VALIDATION_FAILED,
)

_LUIS = '0b8e7a52-3c1d-4f6e-8a90-1d2c3b4a5e6f'

CHANGE_ACCOUNT_STATUS_REQUEST_EXAMPLES: dict[str, Any] = {
    'block': example('Block the account', {'operation': 'block'}),
    'unblock': example('Unblock the account', {'operation': 'unblock'}),
}


def _changed(status: str, changed_at: str) -> dict[str, Any]:
    data = {'user_uuid': _LUIS, 'status': status, 'changed_at': changed_at}
    return {'success': True, 'message': '', 'detail': None, 'data': data}


def _invalid(field: str) -> str:
    return FIELD_INVALID.format(label=FIELD_LABELS[field])


CHANGE_ACCOUNT_STATUS_DOCS: dict[str, Any] = {
    'summary': 'Block or unblock an account',
    'responses': {
        200: {
            'description': 'The account changed; its user gets a notice.',
            'content': json_content(
                blocked=example('Blocked', _changed('blocked', '2026-11-02T20:00:00Z')),
                unblocked=example(
                    'Unblocked', _changed('active', '2026-11-04T15:30:00Z')
                ),
            ),
        },
        401: error_response(
            "The X-Api-Key header is missing or is not TurfBook's key.",
            not_authorized=error_example('Not authorized', NOT_AUTHORIZED),
        ),
        404: error_response(
            'No account has that uuid.',
            not_found=error_example('Unknown account', ACCOUNT_NOT_FOUND),
        ),
        409: error_response(
            'The account cannot make that change: it is closed, already blocked '
            '(blocking again does not restart its 7 days) or not blocked.',
            closed=error_example('Closed account', ACCOUNT_CLOSED),
            already_blocked=error_example('Already blocked', ACCOUNT_ALREADY_BLOCKED),
            not_blocked=error_example('Not blocked', ACCOUNT_NOT_BLOCKED),
        ),
        422: error_response(
            'The uuid is not valid, or the operation is not block or unblock.',
            operation=error_example('Unknown operation', _invalid('operation')),
            user_uuid=error_example('Invalid uuid', _invalid('user_uuid')),
            both=error_example(
                'Invalid uuid and operation',
                VALIDATION_FAILED,
                [
                    {'field': 'user_uuid', 'error': _invalid('user_uuid')},
                    {'field': 'operation', 'error': _invalid('operation')},
                ],
            ),
            not_json=error_example('A body that is not JSON', BODY_NOT_JSON),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
