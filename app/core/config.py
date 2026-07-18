import logging
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smart Training"
    app_env: str = "development"
    app_debug: bool = False
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    admin_email: str = "admin@smarttraining.com"
    admin_password: str = "Admin123!"
    upload_max_size_mb: int = 5
    upload_dir: str = "uploads"
    cors_origins: str = "*"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        url = value.strip()
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
            logger.warning("DATABASE_URL ajustado para mysql+pymysql:// (driver PyMySQL)")
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
