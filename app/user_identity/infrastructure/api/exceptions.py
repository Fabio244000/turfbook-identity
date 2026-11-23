class NotAuthorizedError(Exception):
    """The request did not bring the right API key: an input error of the API, answered
    before any use case runs."""


class InvalidSessionTokenError(Exception):
    """The request did not bring a session token in force: an input error of the API,
    answered before the data is validated."""
