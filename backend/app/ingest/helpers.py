"""Универсальные хелперы для upsert-паттернов. Вместо того чтобы в каждой
save_* функции руками писать "session.get -> если None add иначе setattr",
это делается тут один раз."""

from typing import Any

from sqlmodel import Session, SQLModel, select


def upsert[ModelT: SQLModel](
    session: Session, model: type[ModelT], pk: dict[str, Any], fields: dict[str, Any]
) -> ModelT:
    """Обновляет строку по первичному ключу или создаёт новую.
    pk — словарь полей первичного ключа, например {"id": 42} или {"song_id": 1, "tag_id": 2}."""
    pk_value = tuple(pk.values())
    obj = session.get(model, pk_value if len(pk_value) > 1 else pk_value[0])
    if obj is None:
        obj = model(**pk, **fields)
        session.add(obj)
    else:
        for key, value in fields.items():
            setattr(obj, key, value)
    return obj


def link[ModelT: SQLModel](session: Session, model: type[ModelT], **pk_fields: Any) -> None:
    """Создаёт строку в чистой linking-таблице (составной PK, без доп. полей),
    если такой связи ещё нет. Идемпотентно."""
    pk_value = tuple(pk_fields.values())
    obj = session.get(model, pk_value if len(pk_value) > 1 else pk_value[0])
    if obj is None:
        session.add(model(**pk_fields))


def get_or_create[ModelT: SQLModel](
    session: Session, model: type[ModelT], **match_fields: Any
) -> None:
    """Для таблиц с суррогатным id, где уникальность — это комбинация полей
    (Performance, Credit, AlbumPerformance, *Relationship). Ищет через SELECT,
    а не по PK, поэтому дороже, чем link(), но здесь иначе никак."""
    statement = select(model).filter_by(**match_fields)
    existing = (session.exec(statement)).first()
    if existing is None:
        session.add(model(**match_fields))
