from sqlmodel import Session, select

from ..models import Album, AlbumArtist, Artist, ArtistAlternateName, Song, SongArtist
from . import albums as albums_repo


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


def get_artist_alternate_names(session: Session, artist_id: int) -> list[str]:
    statement = select(ArtistAlternateName.name).where(ArtistAlternateName.artist_id == artist_id)
    return list(session.exec(statement).all())


def get_artist_top_tracks(session: Session, artist_id: int, limit: int = 10) -> list[dict]:
    """Топ-N треков артиста по pageviews среди его прямых primary_artists (SongArtist).
    Заглушки (full=False) исключаем — у них может не быть ни обложки, ни pageviews,
    ни нормального названия (см. flag full в models.py)."""
    statement = (
        select(Song)
        .join(SongArtist, SongArtist.song_id == Song.id)
        .where(SongArtist.artist_id == artist_id, Song.full == True)  # noqa: E712
        .order_by(Song.pageviews.desc().nulls_last())
        .limit(limit)
    )
    songs = list(session.exec(statement).all())

    credits = albums_repo.credits_by_song(session, [song.id for song in songs])

    tracks = []
    for rank, song in enumerate(songs, start=1):
        song_credits = credits.get(song.id, {})
        tracks.append(
            {
                "song_id": song.id,
                "number": rank,
                "disc_number": None,
                "title": song.title,
                "url": song.url,
                "cover_thumbnail_url": song.song_art_image_thumbnail_url,
                "pageviews": song.pageviews,
                "instrumental": song.instrumental,
                "producers": song_credits.get("Producer", []),
                "featuring": song_credits.get("Feature", []),
            }
        )
    return tracks


def list_artist_albums(session: Session, artist_id: int) -> list[Album]:
    statement = (
        select(Album)
        .join(AlbumArtist, AlbumArtist.album_id == Album.id)
        .where(AlbumArtist.artist_id == artist_id, Album.full == True)  # noqa: E712
        .order_by(Album.release_date.desc())
    )
    return list(session.exec(statement).all())
