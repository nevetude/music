from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Переопределяются через .env или переменные окружения
    с префиксом APP_ (например APP_DATABASE_URL=...)."""

    database_url: str = "sqlite:///./genius.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Genius.com иногда отдаёт 403 на genius.com/api/... анонимным запросам
    # (отдельные треки требуют залогиненной сессии). Если задать APP_GENIUS_COOKIE=
    # значением заголовка Cookie из залогиненного браузера, ingest будет
    # представляться этой сессией. См. ingest/genius_client.py.
    genius_cookie: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")


settings = Settings()
