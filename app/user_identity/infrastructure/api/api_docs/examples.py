from typing import Any

from app.user_identity.infrastructure.api.messages import UNEXPECTED_ERROR
from app.user_identity.infrastructure.api.schemas.api_response import ApiErrorResponse

# Realistic values shared by the examples of identity's APIs.
ACCESS_TOKEN = (
    'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3YzlmM2UxYS0yYjRkLTRlNmYtOGEwYi'
    '0xYzJkM2U0ZjVhNmIiLCJpc3MiOiJ0dXJmYm9vay1pZGVudGl0eSIsImlhdCI6MTc5MzcyMDgwMCwiZ'
    'XhwIjoxNzkzNzIxNzAwfQ.k3J9X2pQvB7mN1rT4sW8yZ0aC5dF6gH9jL2nP4qR7uV'
)
REFRESH_TOKEN = 'YbevJvLwCrT5OdFhiiVgGn7jm7m3mfq90l-sucYUtwE'
NEW_REFRESH_TOKEN = 'fSUridh1Nzl2v4SaZakRs9UMY71O3l5awGj2sq0tmlY'
EXPIRES_IN = 900


def example(summary: str, value: dict[str, Any]) -> dict[str, Any]:
    return {'summary': summary, 'value': value}


def error_example(
    summary: str, message: str, detail: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    value = {'success': False, 'message': message, 'detail': detail, 'data': None}
    return example(summary, value)


def json_content(**examples: dict[str, Any]) -> dict[str, Any]:
    return {'application/json': {'examples': examples}}


def error_response(description: str, **examples: dict[str, Any]) -> dict[str, Any]:
    return {
        'model': ApiErrorResponse,
        'description': description,
        'content': json_content(**examples),
    }


UNEXPECTED_ERROR_RESPONSE = error_response(
    'An error the service does not control (database, internal).',
    unexpected=error_example('Unexpected error', UNEXPECTED_ERROR),
)
