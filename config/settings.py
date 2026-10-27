from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 15
    database_url: str
    test_database_url: str | None = None
    # A Lambda execution environment serves one request at a time, so one connection
    # is enough; it also caps connections to the shared RDS at one per environment.
    db_pool_size: int = 1
    db_max_overflow: int = 0
    # Replaces connections that went stale while the environment was idle.
    db_pool_pre_ping: bool = True
    api_prefix: str = '/api'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
