class DomainError(Exception):
    """Base of every business error; the API maps each subclass to an HTTP status."""
