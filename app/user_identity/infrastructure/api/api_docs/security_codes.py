from typing import Any

from app.user_identity.application.messages import (
    NO_PROCESS_IN_PROGRESS,
    SUPPORT_PROCESS_VALIDATED,
    USER_NOT_FOUND,
)
from app.user_identity.domain.messages import (
    SECURITY_CODE_DELIVERED,
    SUPPORT_CODE_LIMIT,
)
from app.user_identity.infrastructure.api.api_docs.examples import (
    UNEXPECTED_ERROR_RESPONSE,
    error_example,
    error_response,
    example,
    json_content,
)
from app.user_identity.infrastructure.api.messages import (
    FIELD_INVALID,
    FIELD_LABELS,
    NOT_AUTHORIZED,
    VALIDATION_FAILED,
)


def _code(code: str, expires_at: str) -> dict[str, Any]:
    data = {
        'process_uuid': '8d2f4b6a-1c3e-4a5b-9f7d-2e6c8a0b4d1f',
        'code': code,
        'code_expires_at': expires_at,
    }
    return {'success': True, 'message': '', 'detail': None, 'data': data}


def _invalid(field: str) -> str:
    return FIELD_INVALID.format(label=FIELD_LABELS[field])


GET_SECURITY_CODE_REQUEST_EXAMPLES: dict[str, Any] = {
    'email_verification': example(
        'Code of an email verification',
        {'cellphone': '+51900000101', 'process_type': 'email_verification'},
    ),
}

GET_SECURITY_CODE_DOCS: dict[str, Any] = {
    'summary': 'Get the security code of a process in progress',
    'responses': {
        200: {
            'description': 'The code in force of the process (even if support '
            'generated it).',
            'content': json_content(
                shown=example('Code in force', _code('482913', '2026-11-20T15:05:00Z'))
            ),
        },
        201: {
            'description': 'No code was in force: one was generated for support. It '
            'is never sent to the user nor counts among the user codes.',
            'content': json_content(
                generated=example(
                    'Code generated', _code('735120', '2026-11-20T15:45:00Z')
                )
            ),
        },
        401: error_response(
            "The X-Api-Key header is missing or is not TurfBook's key.",
            not_authorized=error_example('Not authorized', NOT_AUTHORIZED),
        ),
        404: error_response(
            'No user has that cellphone, or the user has no process of that type in '
            'progress (the grace period after its last code ended, it failed, or its '
            'day ended).',
            no_user=error_example('Unknown cellphone', USER_NOT_FOUND),
            no_process=error_example('No process in progress', NO_PROCESS_IN_PROGRESS),
        ),
        409: error_response(
            'No code is in force and support cannot generate one: it already '
            'generated 2, the last code spent its attempts, or the user already '
            'validated the code of a password process.',
            limit=error_example('Two codes generated', SUPPORT_CODE_LIMIT),
            delivered=error_example('Attempts spent', SECURITY_CODE_DELIVERED),
            validated=error_example(
                'Code already validated', SUPPORT_PROCESS_VALIDATED
            ),
        ),
        422: error_response(
            'The cellphone or the process type is out of format.',
            cellphone=error_example('Invalid cellphone', _invalid('cellphone')),
            process_type=error_example(
                'Unknown process type', _invalid('process_type')
            ),
            both=error_example(
                'Both invalid',
                VALIDATION_FAILED,
                [
                    {'field': 'cellphone', 'error': _invalid('cellphone')},
                    {'field': 'process_type', 'error': _invalid('process_type')},
                ],
            ),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
