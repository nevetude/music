from sqlmodel import Session, select

from ..models import Album, AlbumArtist, Artist


def list_artists(session: Session) -> list[Artist]:
    return list(session.exec(select(Artist).order_by(Artist.name)).all())


def artist_ids_with_albums(session: Session) -> set[int]:
    """id артистов, у которых есть хотя бы один полноценный (full=True) альбом —
    то есть который реально покажется у них на карточке. Для группировки на главной."""
    statement = (
        select(AlbumArtist.artist_id)
        .join(Album, Album.id == AlbumArtist.album_id)
        .where(Album.full == True)  # noqa: E712
        .distinct()
    )
    return set(session.exec(statement).all())


def get_artist(session: Session, artist_id: int) -> Artist | None:
    return session.get(Artist, artist_id)


def list_artist_albums(session: Session, artist_id: int) -> list[Album]:
    statement = (
        select(Album)
        .join(AlbumArtist, AlbumArtist.album_id == Album.id)
        .where(AlbumArtist.artist_id == artist_id, Album.full == True)  # noqa: E712
        .order_by(Album.release_date.desc())
    )
    return list(session.exec(statement).all())
