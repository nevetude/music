from collections import defaultdict

from sqlmodel import Session, select

from ..models import Album, AlbumSong, Artist, Credit, Song, SongArtist, Tag


def get_song(session: Session, song_id: int) -> Song | None:
    return session.get(Song, song_id)


def get_song_artists(session: Session, song_id: int) -> list[Artist]:
    statement = (
        select(Artist)
        .join(SongArtist, SongArtist.artist_id == Artist.id)
        .where(SongArtist.song_id == song_id)
    )
    return list(session.exec(statement).all())


def get_song_genres(session: Session, song_id: int) -> list[str]:
    statement = select(Tag.name).where(Tag.song_id == song_id, Tag.is_primary == True)  # noqa: E712
    return list(session.exec(statement).all())


def get_song_credits(session: Session, song_id: int) -> dict[str, list[str]]:
    statement = (
        select(Credit.role, Artist.name)
        .join(Artist, Artist.id == Credit.artist_id)
        .where(Credit.song_id == song_id)
    )
    grouped: dict[str, list[str]] = defaultdict(list)
    for role, name in session.exec(statement).all():
        grouped[role].append(name)
    return dict(grouped)


def get_song_albums(session: Session, song_id: int) -> list[Album]:
    statement = (
        select(Album)
        .join(AlbumSong, AlbumSong.album_id == Album.id)
        .where(AlbumSong.song_id == song_id, Album.full == True)  # noqa: E712
    )
    return list(session.exec(statement).all())
