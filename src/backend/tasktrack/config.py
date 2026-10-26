from datetime import datetime
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TASKTRACK_", env_file=".env", extra="ignore")
    env: str = "development"
    database_url: str = "postgresql+psycopg://tasktrack:tasktrack@localhost:5432/tasktrack"
    redis_url: str = "redis://localhost:6379/0"
    public_origin: str = "http://localhost:5173"
    session_secret: str = "development-only-change-before-deployment-000000000"
    email_key: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False
    email_from: str = "tasktrack@localhost"
    email_enabled: bool = True
    session_hours: int = 24
    rate_limit: int = 20
    test_now: datetime | None = None

    @property
    def secure(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def production(self):
        if self.test_now is not None and (self.env != "test" or self.test_now.tzinfo is None):
            raise ValueError(
                "A fixed clock is allowed only in test mode and must include a timezone"
            )
        if self.secure and (
            not self.public_origin.startswith("https://")
            or self.session_secret.startswith("development-")
            or len(self.session_secret) < 48
            or not self.email_key
        ):
            raise ValueError("Production requires HTTPS and independent strong session/email keys")
        return self


@lru_cache
def settings() -> Settings:
    return Settings()
