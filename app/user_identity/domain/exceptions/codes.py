from enum import StrEnum


class DomainErrorCode(StrEnum):
    """One code per broken rule, or per failure a driven port declares; the use case
    translates each into its application error."""

    ACCOUNT_CLOSED = 'account_closed'
    ACCOUNT_ALREADY_BLOCKED = 'account_already_blocked'
    ACCOUNT_NOT_BLOCKED = 'account_not_blocked'
    NOTICE_NOT_PUBLISHED = 'notice_not_published'
    PROCESS_NOT_ALLOWED = 'process_not_allowed'
    EMAIL_ALREADY_VERIFIED = 'email_already_verified'
    SECURITY_CODE_LIMIT = 'security_code_limit'
    PROCESS_FAILED = 'process_failed'
    PROCESS_NOT_IN_PROGRESS = 'process_not_in_progress'
    SECURITY_CODE_INCORRECT = 'security_code_incorrect'
    SECURITY_CODE_EXPIRED = 'security_code_expired'
    SECURITY_CODE_EXHAUSTED = 'security_code_exhausted'
    SUPPORT_CODE_LIMIT = 'support_code_limit'
    SECURITY_CODE_DELIVERED = 'security_code_delivered'
    SECURITY_CODE_ALREADY_VALIDATED = 'security_code_already_validated'
    PASSWORD_UPDATE_INTERVAL = 'password_update_interval'
    RECOVERY_LIMIT = 'recovery_limit'
    SECURITY_CODE_NOT_VALIDATED = 'security_code_not_validated'
    INVALID_NEW_PASSWORD = 'invalid_new_password'
    PASSWORDS_DO_NOT_MATCH = 'passwords_do_not_match'
    CURRENT_PASSWORD_INCORRECT = 'current_password_incorrect'
    PASSWORD_TOO_SIMILAR = 'password_too_similar'
    PASSWORD_UNCHANGED = 'password_unchanged'
    PASSWORD_ATTEMPTS_EXCEEDED = 'password_attempts_exceeded'
