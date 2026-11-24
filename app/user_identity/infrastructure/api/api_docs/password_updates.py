from typing import Any

from app.user_identity.infrastructure.api.api_docs.password_processes import (
    REQUEST_CODE_REQUEST_EXAMPLES,
    UPDATE_CONFLICTS,
    UPDATE_REJECTIONS,
    VALIDATE_CODE_REQUEST_EXAMPLES,
    request_code_docs,
    set_password_docs,
    set_password_request_examples,
    validate_code_docs,
)

REQUEST_PASSWORD_UPDATE_REQUEST_EXAMPLES = REQUEST_CODE_REQUEST_EXAMPLES
REQUEST_PASSWORD_UPDATE_DOCS: dict[str, Any] = request_code_docs(
    'Request a code to update the password',
    'The process already sent 3 codes or its 60 minutes passed, the code was '
    'already validated, the password was updated less than 30 days ago, or an '
    'update failed today.',
    with_session=True,
    **UPDATE_CONFLICTS,
)

VALIDATE_PASSWORD_UPDATE_REQUEST_EXAMPLES = VALIDATE_CODE_REQUEST_EXAMPLES
VALIDATE_PASSWORD_UPDATE_DOCS: dict[str, Any] = validate_code_docs(
    'Validate the code to update the password', with_session=True
)

SET_UPDATED_PASSWORD_REQUEST_EXAMPLES = set_password_request_examples(with_current=True)
SET_UPDATED_PASSWORD_DOCS: dict[str, Any] = set_password_docs(
    'Set the updated password',
    'The new password is saved and the process completed; the session goes on.',
    with_session=True,
    **UPDATE_REJECTIONS,
)
