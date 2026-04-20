from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Help Desk Engine"
    VERSION: str = "0.1.0"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432  # ✅ Исправлено на порт PostgreSQL
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "helpdesk"

    @property
    def DATABASE_URL(self) -> str:
        auth = f"{self.DB_USER}:{self.DB_PASSWORD}" if self.DB_PASSWORD else self.DB_USER
        return f"postgresql+asyncpg://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
