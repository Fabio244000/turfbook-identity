# Texts of the API layer: what the client reads when the error is not a domain rule.

VALIDATION_FAILED = 'There were problems with the submitted data.'
UNEXPECTED_ERROR = 'An unexpected error occurred. Please try again later.'
BODY_NOT_JSON = 'The request body is not valid JSON.'
FIELD_REQUIRED = '{label} is required.'
FIELD_INVALID = '{label} has an invalid value.'

# Readable names of the request fields, for the structure errors.
FIELD_LABELS = {
    'first_name': 'First name',
    'last_name': 'Last name',
    'cellphone': 'Cellphone',
    'username': 'Username',
    'password': 'Password',
    'email': 'Email',
    'refresh_token': 'Refresh token',
}

# Log message of an error the API does not control (never with tokens or secrets).
UNEXPECTED_ERROR_LOG = 'Unexpected error on %s %s'
