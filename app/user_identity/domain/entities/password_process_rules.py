from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordProcessRules:
    """The limits of the password processes; their values are configuration."""

    update_interval_minutes: int
    max_failed_recoveries_per_week: int
    max_password_attempts: int
    min_difference: int
