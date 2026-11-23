from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityCodeRules:
    """The limits of the security codes; their values are configuration."""

    code_minutes: int
    max_user_codes: int
    max_support_codes: int
    max_attempts: int
    support_grace_minutes: int
