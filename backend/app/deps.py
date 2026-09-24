"""FastAPI-зависимости. Лежат отдельно от database.py, чтобы парсер (ingest)
использовал общий Engine, не импортируя FastAPI."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from .database import get_session

SessionDep = Annotated[Session, Depends(get_session)]
