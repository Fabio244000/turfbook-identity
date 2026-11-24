"""The documentation shared by the two password processes (update and recovery): the
same three operations, with or without the session token."""

from typing import Any

from app.user_identity.application.messages import (
    PASSWORD_DEADLINE_EXPIRED,
    PROCESS_NOT_FOUND,
    RECOVERY_LIMIT,
    SECURITY_CODE_NOT_SENT,
)
from app.user_identity.domain.messages import (
    CURRENT_PASSWORD_INCORRECT,
    PASSWORD_ATTEMPTS_EXCEEDED,
    PASSWORD_LENGTH,
    PASSWORD_TOO_SIMILAR,
    PASSWORD_UNCHANGED,
    PASSWORD_UPDATE_INTERVAL,
    PASSWORDS_DO_NOT_MATCH,
    PROCESS_FAILED,
    PROCESS_NOT_ALLOWED,
    SECURITY_CODE_ALREADY_VALIDATED,
    SECURITY_CODE_EXHAUSTED,
    SECURITY_CODE_EXPIRED,
    SECURITY_CODE_INCORRECT,
    SECURITY_CODE_LIMIT,
    SECURITY_CODE_NOT_VALIDATED,
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

PROCESS = '8d2f4b6a-1c3e-4a5b-9f7d-2e6c8a0b4d1f'
CELLPHONE = '+51900000101'
EMAIL = 'rosa@gmail.com'
CURRENT_PASSWORD = 'GrassElSol2026!'
NEW_PASSWORD = 'CanchaVerde#Lima7'

_SESSION_TOKEN_RESPONSE = error_response(
    'The session token is missing, invalid or expired; answered before the data.',
    invalid_token=error_example('Invalid session token', SESSION_TOKEN_INVALID),
)
_SUCCESS = {'success': True, 'message': '', 'detail': None}


def _invalid(field: str) -> str:
    return FIELD_INVALID.format(label=FIELD_LABELS[field])


def _required(field: str) -> str:
    return FIELD_REQUIRED.format(label=FIELD_LABELS[field])


def _with_session(responses: dict[int, Any], with_session: bool) -> dict[int, Any]:
    if with_session:
        responses[401] = _SESSION_TOKEN_RESPONSE
    return dict(sorted(responses.items()))


REQUEST_CODE_REQUEST_EXAMPLES: dict[str, Any] = {
    'account': example(
        'The cellphone and email of the account',
        {'cellphone': CELLPHONE, 'email': EMAIL},
    ),
}

VALIDATE_CODE_REQUEST_EXAMPLES: dict[str, Any] = {
    'code': example('The code received by email and SMS', {'code': '482913'}),
}


def request_code_docs(
    summary: str, conflicts: str, with_session: bool, **conflict_examples: Any
) -> dict[str, Any]:
    responses: dict[int, Any] = {
        201: {
            'description': (
                'A code went by email and SMS, in the process in progress or in a new '
                'one; the code is never returned. Every answer takes at least 1 s.'
            ),
            'content': json_content(
                sent=example(
                    'Code sent',
                    _SUCCESS
                    | {
                        'data': {
                            'process_uuid': PROCESS,
                            'code_expires_at': '2026-11-20T15:05:00Z',
                        }
                    },
                )
            ),
        },
        409: error_response(
            conflicts,
            limit=error_example(
                'Three codes, or the 60 minutes of the process passed',
                SECURITY_CODE_LIMIT,
            ),
            validated=error_example(
                'The code was already validated', SECURITY_CODE_ALREADY_VALIDATED
            ),
            failed=error_example('A process failed today', PROCESS_FAILED),
            **conflict_examples,
        ),
        422: error_response(
            'The cellphone and email are not of one active account with credentials '
            '(the same answer in every case), or they are out of format.',
            not_allowed=error_example('Account that cannot start', PROCESS_NOT_ALLOWED),
            cellphone=error_example('Invalid cellphone', _invalid('cellphone')),
            email=error_example('Invalid email', _invalid('email')),
        ),
        500: error_response(
            'The code could not be sent (it does not count), or an error the service '
            'does not control.',
            not_sent=error_example('Code not sent', SECURITY_CODE_NOT_SENT),
            unexpected=error_example('Unexpected error', UNEXPECTED_ERROR),
        ),
    }
    return {'summary': summary, 'responses': _with_session(responses, with_session)}


UPDATE_CONFLICTS: dict[str, Any] = {
    'interval': error_example(
        'Updated less than 30 days ago', PASSWORD_UPDATE_INTERVAL
    ),
}
RECOVERY_CONFLICTS: dict[str, Any] = {
    'recoveries': error_example(
        'Four failed recoveries this week',
        RECOVERY_LIMIT.format(phone='+51 999999998', email='turfbook@gmail.com'),
    ),
}


def validate_code_docs(summary: str, with_session: bool) -> dict[str, Any]:
    responses: dict[int, Any] = {
        200: {
            'description': (
                'The code is used and the process validated: the new password is set '
                'before the deadline.'
            ),
            'content': json_content(
                validated=example(
                    'Code validated',
                    _SUCCESS | {'data': {'password_deadline': '2026-11-20T15:09:00Z'}},
                )
            ),
        },
        404: error_response(
            'The process does not exist, is not of this user or type, or is no longer '
            'in progress (it was abandoned, its day ended, or it was validated).',
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
            code_format=error_example('Code out of format', _invalid('code')),
            process_uuid=error_example(
                'Process that is not a UUID', _invalid('process_uuid')
            ),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    }
    return {'summary': summary, 'responses': _with_session(responses, with_session)}


def set_password_request_examples(with_current: bool) -> dict[str, Any]:
    value = {'new_password': NEW_PASSWORD, 'new_password_confirmation': NEW_PASSWORD}
    if with_current:
        value['current_password'] = CURRENT_PASSWORD
    return {'password': example('The new password, twice', value)}


def set_password_docs(
    summary: str, success: str, with_session: bool, **rejections: Any
) -> dict[str, Any]:
    responses: dict[int, Any] = {
        200: {
            'description': success,
            'content': json_content(
                set=example('Password set', _SUCCESS | {'data': None})
            ),
        },
        404: error_response(
            'The process does not exist, is not of this user or type, or is no longer '
            'in progress.',
            not_found=error_example('Unknown process', PROCESS_NOT_FOUND),
        ),
        409: error_response(
            'The code was not validated, the 5 minutes to set the password passed, '
            'the fifth rejection failed the process, or the process already failed.',
            not_validated=error_example(
                'Code not validated', SECURITY_CODE_NOT_VALIDATED
            ),
            deadline=error_example('Deadline passed', PASSWORD_DEADLINE_EXPIRED),
            attempts=error_example('Fifth rejection', PASSWORD_ATTEMPTS_EXCEEDED),
            failed=error_example('Process failed', PROCESS_FAILED),
        ),
        422: error_response(
            'A rule of the new password (it counts: at most 5), or a field missing or '
            'out of length (it does not).',
            mismatch=error_example('The entries differ', PASSWORDS_DO_NOT_MATCH),
            **rejections,
            length=error_example('Out of length', PASSWORD_LENGTH),
            missing=error_example('Field missing', _required('new_password')),
        ),
        500: UNEXPECTED_ERROR_RESPONSE,
    }
    return {'summary': summary, 'responses': _with_session(responses, with_session)}


UPDATE_REJECTIONS: dict[str, Any] = {
    'current': error_example('Wrong current password', CURRENT_PASSWORD_INCORRECT),
    'similar': error_example('Too similar', PASSWORD_TOO_SIMILAR),
}
RECOVERY_REJECTIONS: dict[str, Any] = {
    'unchanged': error_example('Equal to the current one', PASSWORD_UNCHANGED),
}
