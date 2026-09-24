from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

# Один Engine на весь проект: им пользуются и read-API, и парсер (ingest).
# check_same_thread=False нужен SQLite, потому что FastAPI гоняет sync-эндпоинты в пуле потоков.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Создаёт таблицы, которых ещё нет. Вызывается парсером при старте."""
    from . import models  # noqa: F401  — регистрирует таблицы в SQLModel.metadata

    SQLModel.metadata.create_all(engine)


def new_session() -> Session:
    return Session(engine)


def get_session() -> Generator[Session]:
    with new_session() as session:
        yield session
