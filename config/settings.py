from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PEM (PKCS#8) of the RSA key that signs the session token.
    jwt_private_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_token_bytes: int = 32
    # Account lock (R7): failed sign-ins of one business day that block the account.
    max_failed_attempts: int = 5
    business_timezone: str = 'America/Lima'
    # TurfBook's contact, shown in the 403 and in the notices.
    turfbook_contact_phone: str = '+51 999999998'
    turfbook_contact_email: str = 'turfbook@gmail.com'
    # Notices topic of turfbook-notifications; a publish waits at most this, no retries.
    notices_topic_arn: str
    notice_publish_timeout_seconds: float = 1.0

    database_url: str
    # A Lambda execution environment serves one request at a time, so one connection
    # is enough; it also caps connections to the shared RDS at one per environment.
    db_pool_size: int = 1
    db_max_overflow: int = 0
    # Replaces connections that went stale while the environment was idle.
    db_pool_pre_ping: bool = True
    api_prefix: str = '/api'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
