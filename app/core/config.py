from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ✅ Pydantic v2 конфигурация
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ✅ Игнорировать неизвестные переменные (DATABASE_URL и др.)
        case_sensitive=False  # ✅ DB_HOST и db_host будут считаться одним полем
    )

    # Project
    PROJECT_NAME: str = "Help Desk Engine"
    VERSION: str = "0.1.0"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "helpdesk"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ✅ Вычисляемое свойство — не поле, не будет конфликтовать с окружением
    @property
    def DATABASE_URL(self) -> str:
        auth = f"{self.DB_USER}:{self.DB_PASSWORD}" if self.DB_PASSWORD else self.DB_USER
        return f"postgresql+asyncpg://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()