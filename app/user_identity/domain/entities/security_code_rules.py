from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityCodeRules:
    """The limits of the security codes and of the life of a process; their values
    are configuration."""

    code_minutes: int
    max_user_codes: int
    max_support_codes: int
    max_attempts: int
    support_grace_minutes: int
    # The user requests and validates codes within this window of the process.
    user_window_minutes: int
    # A validated process sets the new password within this deadline.
    password_deadline_minutes: int
