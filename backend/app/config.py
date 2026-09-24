from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Переопределяются через .env или переменные окружения
    с префиксом APP_ (например APP_DATABASE_URL=...)."""

    database_url: str = "sqlite:///./genius.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")


settings = Settings()
