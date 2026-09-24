from collections import defaultdict

from sqlmodel import Session, select

from ..models import (
    Album,
    AlbumArtist,
    AlbumCoverArt,
    AlbumPerformance,
    AlbumSong,
    Artist,
    Credit,
    Song,
    Tag,
)


def get_album(session: Session, album_id: int) -> Album | None:
    return session.get(Album, album_id)


def get_album_artists(session: Session, album_id: int) -> list[Artist]:
    statement = (
        select(Artist)
        .join(AlbumArtist, AlbumArtist.artist_id == Artist.id)
        .where(AlbumArtist.album_id == album_id)
    )
    return list(session.exec(statement).all())


def get_album_genres(session: Session, album_id: int) -> list[str]:
    """Жанры альбома = теги его песен, помеченные как primary (без повторов)."""
    statement = (
        select(Tag.name)
        .join(AlbumSong, AlbumSong.song_id == Tag.song_id)
        .where(AlbumSong.album_id == album_id, Tag.is_primary == True)  # noqa: E712
        .distinct()
    )
    return list(session.exec(statement).all())


def get_album_performances(session: Session, album_id: int) -> dict[str, list[str]]:
    """AlbumPerformance -> {role: [имена]}, сохраняя роли из Genius как есть (Producers, Featuring, Label...)."""
    statement = (
        select(AlbumPerformance.role, Artist.name)
        .join(Artist, Artist.id == AlbumPerformance.artist_id)
        .where(AlbumPerformance.album_id == album_id)
    )
    grouped: dict[str, list[str]] = defaultdict(list)
    for role, name in session.exec(statement).all():
        grouped[role].append(name)
    return dict(grouped)


def get_album_cover_arts(session: Session, album_id: int) -> list[AlbumCoverArt]:
    statement = select(AlbumCoverArt).where(AlbumCoverArt.album_id == album_id)
    return list(session.exec(statement).all())


def get_album_tracks(session: Session, album_id: int) -> list[dict]:
    """Треки альбома в порядке диска/номера, с полным Song и списком продюсеров/фитов."""
    statement = (
        select(AlbumSong, Song)
        .join(Song, Song.id == AlbumSong.song_id)
        .where(AlbumSong.album_id == album_id)
        .order_by(AlbumSong.disc_number, AlbumSong.number)
    )
    rows = session.exec(statement).all()

    song_ids = [song.id for _, song in rows]
    credits_by_song = _credits_by_song(session, song_ids)

    tracks = []
    for album_song, song in rows:
        credits = credits_by_song.get(song.id, {})
        tracks.append(
            {
                "song_id": song.id,
                "number": album_song.number,
                "disc_number": album_song.disc_number,
                "title": song.title,
                "url": song.url,
                "cover_thumbnail_url": song.song_art_image_thumbnail_url,
                "pageviews": song.pageviews,
                "instrumental": song.instrumental,
                "producers": credits.get("Producer", []),
                "featuring": credits.get("Feature", []),
            }
        )
    return tracks


def _credits_by_song(session: Session, song_ids: list[int]) -> dict[int, dict[str, list[str]]]:
    if not song_ids:
        return {}
    statement = (
        select(Credit.song_id, Credit.role, Artist.name)
        .join(Artist, Artist.id == Credit.artist_id)
        .where(Credit.song_id.in_(song_ids))
    )
    result: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for song_id, role, name in session.exec(statement).all():
        result[song_id][role].append(name)
    return {song_id: dict(roles) for song_id, roles in result.items()}
