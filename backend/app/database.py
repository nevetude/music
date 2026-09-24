from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, create_engine

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
