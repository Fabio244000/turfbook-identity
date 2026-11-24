from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordChange:
    """The new password, twice, and the current one that authorizes the change."""

    new_password: str
    new_password_confirmation: str
    current_password: str
