from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings

# aiosqlite вместо обычного sqlite3-драйвера, который использует sync-часть (app/database.py).
# Физически — один и тот же файл БД, просто два разных способа с ним говорить.
_async_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)

async_engine = create_async_engine(_async_url, echo=False)


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def new_session() -> AsyncSession:
    return AsyncSession(async_engine)
