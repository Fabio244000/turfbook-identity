class NotAuthorizedError(Exception):
    """The request did not bring the right API key: an input error of the API, answered
    before any use case runs."""
