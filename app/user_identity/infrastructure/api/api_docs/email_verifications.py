from typing import Any

from app.user_identity.application.messages import (
    PROCESS_NOT_FOUND,
    SECURITY_CODE_NOT_SENT,
)
from app.user_identity.domain.messages import (
    EMAIL_ALREADY_VERIFIED,
    PROCESS_FAILED,
    PROCESS_NOT_ALLOWED,
    SECURITY_CODE_EXHAUSTED,
    SECURITY_CODE_EXPIRED,
    SECURITY_CODE_INCORRECT,
    SECURITY_CODE_LIMIT,
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
    FIELD_REQUIRED,
    SESSION_TOKEN_INVALID,
    UNEXPECTED_ERROR,
)

_PROCESS = '8d2f4b6a-1c3e-4a5b-9f7d-2e6c8a0b4d1f'

_SESSION_TOKEN_RESPONSE = error_response(
    'The session token is missing, invalid or expired; answered before the data.',
    invalid_token=error_example('Invalid session token', SESSION_TOKEN_INVALID),
)


def _label(field: str) -> str:
    return FIELD_LABELS[field]


REQUEST_EMAIL_VERIFICATION_DOCS: dict[str, Any] = {
    'summary': 'Request a code to verify the email',
    'responses': {
        201: {
            'description': (
                'A code went to the email of the account, in the process of the day '
                'or in a new one; the code is never returned.'
            ),
            'content': json_content(
                sent=example(
                    'Code sent',
                    {
                        'success': True,
                        'message': '',
                        'detail': None,
                        'data': {
                            'process_uuid': _PROCESS,
                            'code_expires_at': '2026-11-20T15:05:00Z',
                        },
                    },
                )
            ),
        },
        401: _SESSION_TOKEN_RESPONSE,
        409: error_response(
            'The email is verified, the process already sent 3 codes, or a process '
            'failed today.',
            verified=error_example('Email already verified', EMAIL_ALREADY_VERIFIED),
            limit=error_example('Three codes requested', SECURITY_CODE_LIMIT),
            failed=error_example('A process failed today', PROCESS_FAILED),
        ),
        422: error_response(
            'The account has no email, or is blocked or closed.',
            not_allowed=error_example('Account that cannot start', PROCESS_NOT_ALLOWED),
        ),
        500: error_response(
            'The code could not be sent (it does not count), or an error the service '
            'does not control.',
            not_sent=error_example('Code not sent', SECURITY_CODE_NOT_SENT),
            unexpected=error_example('Unexpected error', UNEXPECTED_ERROR),
        ),
    },
}

VALIDATE_EMAIL_VERIFICATION_REQUEST_EXAMPLES: dict[str, Any] = {
    'code': example('The code received by email', {'code': '482913'}),
}

VALIDATE_EMAIL_VERIFICATION_DOCS: dict[str, Any] = {
    'summary': 'Verify the email with its code',
    'responses': {
        200: {
            'description': 'The email is verified; the code is used and the process '
            'completed.',
            'content': json_content(
                verified=example(
                    'Email verified',
                    {'success': True, 'message': '', 'detail': None, 'data': None},
                )
            ),
        },
        401: _SESSION_TOKEN_RESPONSE,
        404: error_response(
            'The process does not exist, is not of the user of the session, or is no '
            'longer in progress (its day ended, or it was completed).',
            not_found=error_example('Unknown process', PROCESS_NOT_FOUND),
        ),
        409: error_response(
            'The code spent its 3 attempts, or the process failed.',
            exhausted=error_example('Attempts spent', SECURITY_CODE_EXHAUSTED),
            failed=error_example('Process failed', PROCESS_FAILED),
        ),
        422: error_response(
            'The code is wrong (it counts an attempt) or expired (it does not), or '
            'the data is out of format.',
            incorrect=error_example('Wrong code', SECURITY_CODE_INCORRECT),
            expired=error_example('Expired code', SECURITY_CODE_EXPIRED),
            code_format=error_example(
                'Code out of format', FIELD_INVALID.format(label=_label('code'))
            ),
            code_missing=error_example(
                'Code missing', FIELD_REQUIRED.format(label=_label('code'))
            ),
            process_uuid=error_example(
                'Process that is not a UUID',
                FIELD_INVALID.format(label=_label('process_uuid')),
            ),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    },
}
