"""Единая схема БД: пишет ingest (парсер), читает read-API.
Один файл моделей — единственный источник правды о структуре БД."""

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Artist(SQLModel, table=True):
    __tablename__ = "artists"

    id: int = Field(primary_key=True)
    name: str
    slug: str | None = None
    url: str | None = None
    image_url: str | None = None
    header_image_url: str | None = None
    is_verified: bool | None = None
    is_meme_verified: bool | None = None
    followers_count: int | None = None
    base_name: str | None = None
    disambiguator: str | None = None
    description: dict | None = Field(default=None, sa_column=Column(JSON))
    description_preview: str | None = None
    translation_artist: bool | None = None
    # True — только когда карточка загружена явным парсингом артиста
    # (make parse artist <id> или make parse <id> для полного пайплайна).
    # Артист, попавший в базу только как соавтор/фит/продюсер другой сущности,
    # остаётся full=False, даже если его данные при этом достаточно подробные.
    full: bool = False


class ArtistAlternateName(SQLModel, table=True):
    """Альтернативные имена/псевдонимы артиста, из alternate_names."""

    __tablename__ = "artist_alternate_names"

    artist_id: int = Field(foreign_key="artists.id", primary_key=True)
    name: str = Field(primary_key=True)


class Song(SQLModel, table=True):
    __tablename__ = "songs"

    id: int = Field(primary_key=True)
    title: str
    url: str | None = None
    release_date: str | None = None
    language: str | None = None
    lyrics_state: str | None = None
    lyrics_updated_at: int | None = None
    lyrics_verified: bool | None = None
    explicit: bool | None = None
    hidden: bool | None = None
    instrumental: bool | None = None
    is_music: bool | None = None
    published: bool | None = None
    recording_location: str | None = None
    description: dict | None = Field(default=None, sa_column=Column(JSON))
    description_preview: str | None = None
    header_image_url: str | None = None
    header_image_thumbnail_url: str | None = None
    song_art_image_url: str | None = None
    song_art_image_thumbnail_url: str | None = None
    song_art_primary_color: str | None = None
    song_art_secondary_color: str | None = None
    song_art_text_color: str | None = None
    soundcloud_url: str | None = None
    youtube_url: str | None = None
    youtube_start: str | None = None
    spotify_uuid: str | None = None
    pageviews: int | None = None
    updated_at: int | None = None
    full: bool = False  # True = данные полные (пришли из /api/songs/{id}), не заглушка


class Album(SQLModel, table=True):
    __tablename__ = "albums"

    id: int = Field(primary_key=True)
    name: str
    full_title: str | None = None
    album_type: str | None = None
    url: str | None = None
    release_date: str | None = None
    language: str | None = None
    description_preview: str | None = None
    custom_header_image_url: str | None = None
    header_image_url: str | None = None
    cover_art_url: str | None = None
    cover_art_thumbnail_url: str | None = None
    album_art_primary_color: str | None = None
    album_art_secondary_color: str | None = None
    album_art_text_color: str | None = None
    song_pageviews: int | None = None
    updated_at: int | None = None
    full: bool = False  # True = данные полные (пришли из /api/albums/{id}), не заглушка


class AlbumSong(SQLModel, table=True):
    """Порядок треков в альбоме. disc_number/disc_track_number/number
    заполняются отдельно через /albums/{id}/tracks."""

    __tablename__ = "album_songs"

    album_id: int = Field(foreign_key="albums.id", primary_key=True)
    song_id: int = Field(foreign_key="songs.id", primary_key=True)
    disc_number: int | None = None
    disc_track_number: int | None = None
    number: int | None = None


class SongArtist(SQLModel, table=True):
    """Прямая связь песня <-> primary_artists (для быстрых выборок)."""

    __tablename__ = "songs_artists"

    song_id: int = Field(foreign_key="songs.id", primary_key=True)
    artist_id: int = Field(foreign_key="artists.id", primary_key=True)


class AlbumArtist(SQLModel, table=True):
    __tablename__ = "album_artists"

    album_id: int = Field(foreign_key="albums.id", primary_key=True)
    artist_id: int = Field(foreign_key="artists.id", primary_key=True)


class Tag(SQLModel, table=True):
    """Тег песни. Объединяет справочные данные тега со связью song<->tag."""

    __tablename__ = "tags"

    song_id: int = Field(foreign_key="songs.id", primary_key=True)
    tag_id: int = Field(primary_key=True)  # genius tag id
    logical_name: str | None = None
    name: str
    is_primary: bool = False


class SongRelationship(SQLModel, table=True):
    """Направленная связь между песнями: samples, remix_of, interpolates и т.д."""

    __tablename__ = "relationships"

    id: int | None = Field(default=None, primary_key=True)
    song_id: int = Field(foreign_key="songs.id")
    related_song_id: int = Field(foreign_key="songs.id")
    relationship_type: str


class Performance(SQLModel, table=True):
    """Роль артиста/компании при песне из custom_performances (Distributor, Label и т.д.)."""

    __tablename__ = "performances"

    id: int | None = Field(default=None, primary_key=True)
    song_id: int = Field(foreign_key="songs.id")
    artist_id: int = Field(foreign_key="artists.id")
    role: str


class Credit(SQLModel, table=True):
    """Роль артиста вне custom_performances: Primary, Feature, Writer, Producer и т.д."""

    __tablename__ = "credits"

    id: int | None = Field(default=None, primary_key=True)
    song_id: int = Field(foreign_key="songs.id")
    artist_id: int = Field(foreign_key="artists.id")
    role: str


class AlbumPerformance(SQLModel, table=True):
    """Роль артиста/компании при альбоме из song_performances (Featuring, Producers, Label...)."""

    __tablename__ = "album_performances"

    id: int | None = Field(default=None, primary_key=True)
    album_id: int = Field(foreign_key="albums.id")
    artist_id: int = Field(foreign_key="artists.id")
    role: str


class AlbumRelationship(SQLModel, table=True):
    """Направленная связь между альбомами: deluxe_edition_of, reissue_of, remix_version_of и т.д."""

    __tablename__ = "album_relationships"

    id: int | None = Field(default=None, primary_key=True)
    album_id: int = Field(foreign_key="albums.id")
    related_album_id: int = Field(foreign_key="albums.id")
    relationship_type: str


class AlbumCoverArt(SQLModel, table=True):
    """Альтернативные обложки альбома, из поля cover_arts."""

    __tablename__ = "album_cover_arts"

    id: int = Field(primary_key=True)  # genius id обложки
    album_id: int = Field(foreign_key="albums.id")
    image_url: str | None = None
    thumbnail_image_url: str | None = None
    url: str | None = None
    # Подпись под обложкой в UI. Ставится по умолчанию при первом сохранении
    # и НЕ перезаписывается парсером при повторном заходе — редактируется руками
    # напрямую в БД (Tracklist / Alt. cover / и т.д.).
    label: str | None = "Cover"
