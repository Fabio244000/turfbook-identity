from pydantic import BaseModel


class SessionRequest(BaseModel):
    """Only compared with what is stored: no format is checked, so any value that
    does not match is a wrong credential (401), not an invalid input."""

    username: str
    password: str
