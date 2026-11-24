from typing import Any

from app.user_identity.infrastructure.api.api_docs.password_processes import (
    RECOVERY_CONFLICTS,
    RECOVERY_REJECTIONS,
    REQUEST_CODE_REQUEST_EXAMPLES,
    VALIDATE_CODE_REQUEST_EXAMPLES,
    request_code_docs,
    set_password_docs,
    set_password_request_examples,
    validate_code_docs,
)

REQUEST_PASSWORD_RECOVERY_REQUEST_EXAMPLES = REQUEST_CODE_REQUEST_EXAMPLES
REQUEST_PASSWORD_RECOVERY_DOCS: dict[str, Any] = request_code_docs(
    'Request a code to recover the password',
    'The process already sent 3 codes or its 60 minutes passed, the code was '
    'already validated, 4 recoveries failed this week, or one failed today.',
    with_session=False,
    **RECOVERY_CONFLICTS,
)

VALIDATE_PASSWORD_RECOVERY_REQUEST_EXAMPLES = VALIDATE_CODE_REQUEST_EXAMPLES
VALIDATE_PASSWORD_RECOVERY_DOCS: dict[str, Any] = validate_code_docs(
    'Validate the code to recover the password', with_session=False
)

SET_RECOVERED_PASSWORD_REQUEST_EXAMPLES = set_password_request_examples(
    with_current=False
)
SET_RECOVERED_PASSWORD_DOCS: dict[str, Any] = set_password_docs(
    'Set the recovered password',
    'The new password is saved and the process completed; the session of the user '
    'is closed: it signs in with the new password.',
    with_session=False,
    **RECOVERY_REJECTIONS,
)
