"""Сохранение объектов Genius API в БД. Логика 1:1 с исходным db.py,
но upsert/link-паттерны вынесены в helpers.py — вместо восьми почти
одинаковых блоков "get -> add или setattr" здесь только сами данные."""

import logging

from sqlmodel import Session

from ..database import new_session
from ..models import (
    Album,
    AlbumArtist,
    AlbumCoverArt,
    AlbumPerformance,
    AlbumRelationship,
    AlbumSong,
    Artist,
    ArtistAlternateName,
    Credit,
    Performance,
    Song,
    SongArtist,
    SongRelationship,
    Tag,
)
from .helpers import get_or_create, link, upsert

logger = logging.getLogger(__name__)

# ─────────── Учёт найденных сущностей (для догрузки полных данных) ───────────
# Любой артист/альбом, встреченный как вложенный объект (соавтор, фит, альбом из тела
# песни или из relationships), попадает в pending. commands.complete_discovered()
# забирает их и догружает через /api/artists/{id} и /api/albums/{id}.
# done — те, что уже получены полностью в этом запуске (повторно не тянем).
_pending_artists: set[int] = set()
_pending_albums: set[int] = set()
_done_artists: set[int] = set()
_done_albums: set[int] = set()


def mark_albums_handled(ids: list[int]) -> None:
    """Альбомы, которые вызывающий код загрузит сам (дискография в parse_full,
    с полными песнями), — чтобы load_related не тянул их дважды."""
    _done_albums.update(ids)


def take_pending_artists() -> list[int]:
    ids = sorted(_pending_artists - _done_artists)
    _pending_artists.clear()
    return ids


def take_pending_albums() -> list[int]:
    ids = sorted(_pending_albums - _done_albums)
    _pending_albums.clear()
    return ids


# Поля-массивы артистов, которые НЕ входят в custom_performances,
# но должны попасть в credits с соответствующей ролью.
ROLE_FIELDS = {
    "primary_artists": "Primary",
    "featured_artists": "Feature",
    "writer_artists": "Writer",
    "producer_artists": "Producer",
}


# ─────────────────────────── Upsert базовых сущностей ───────────────────────────


def upsert_artist(
    session: Session, data: dict, *, full: bool = False, complete: bool = False
) -> None:
    """Сохраняет всё, что пришло про артиста, — независимо от источника.

    full — отдельный флаг "у этого артиста спарсена вся дискография" (True только
    из save_artist, т.е. make parse artist/<id>). Он не про полноту данных карточки:
    артист, найденный как соавтор/фит/продюсер, тоже пишется целиком, просто с full=False.
    Флаг "липкий": повторное появление артиста как соавтора его не сбрасывает.

    Урезанная версия артиста не затирает уже сохранённые поля (skip_none), поэтому
    защита "если full — пропустить" больше не нужна.

    complete=True — данные получены из /api/artists/{id} (не вложенный объект), догружать
    не нужно. full=True подразумевает complete. Иначе артист попадает в pending.

    Логи сохранения артиста — только DEBUG, чтобы не шуметь поверх album/track логов."""
    name_components = data.get("name_components") or {}
    alternate_names = data.get("alternate_names") or []
    fields = dict(
        name=data.get("name"),
        url=data.get("url"),
        image_url=data.get("image_url"),
        header_image_url=data.get("header_image_url"),
        followers_count=data.get("followers_count"),
        base_name=name_components.get("base_name"),
        disambiguator=name_components.get("disambiguator"),
        # По умолчанию real_name = первое альтернативное имя из списка.
        real_name=alternate_names[0] if alternate_names else None,
        description_preview=data.get("description_preview"),
        translation_artist=data.get("translation_artist"),
    )
    if full:
        fields["full"] = True  # в остальных случаях не трогаем (новая строка = False)
    if full or complete:
        _done_artists.add(data["id"])
    else:
        _pending_artists.add(data["id"])
    upsert(session, Artist, {"id": data["id"]}, fields, skip_none=True)
    logger.debug("artist %s (%r) upserted: full=%s", data["id"], data.get("name"), full)

    for alt_name in alternate_names:
        link(session, ArtistAlternateName, artist_id=data["id"], name=alt_name)


def upsert_song(session: Session, data: dict, *, full: bool) -> None:
    """full=False — песня пришла только из song_relationships/треклиста (неполные данные).
    Уже полную запись (full=True) неполной версией не перезаписываем."""
    existing = session.get(Song, data["id"])
    if existing is not None and existing.full and not full:
        return  # уже есть полноценная запись — заглушкой не портим

    stats = data.get("stats") or {}
    fields = dict(
        title=data.get("title"),
        url=data.get("url"),
        release_date=data.get("release_date"),
        language=data.get("language"),
        lyrics_state=data.get("lyrics_state"),
        lyrics_updated_at=data.get("lyrics_updated_at"),
        lyrics_verified=data.get("lyrics_verified"),
        explicit=data.get("explicit"),
        hidden=data.get("hidden"),
        instrumental=data.get("instrumental"),
        is_music=data.get("is_music"),
        published=data.get("published"),
        recording_location=data.get("recording_location"),
        description_preview=data.get("description_preview"),
        header_image_url=data.get("header_image_url"),
        header_image_thumbnail_url=data.get("header_image_thumbnail_url"),
        song_art_image_url=data.get("song_art_image_url"),
        song_art_image_thumbnail_url=data.get("song_art_image_thumbnail_url"),
        song_art_primary_color=data.get("song_art_primary_color"),
        song_art_secondary_color=data.get("song_art_secondary_color"),
        soundcloud_url=data.get("soundcloud_url"),
        youtube_url=data.get("youtube_url"),
        youtube_start=data.get("youtube_start"),
        spotify_uuid=data.get("spotify_uuid"),
        pageviews=stats.get("pageviews"),
        updated_at=data.get("updated_at"),
        full=full,
    )
    upsert(session, Song, {"id": data["id"]}, fields)


def upsert_album(session: Session, data: dict, *, complete: bool = False) -> None:
    """Флага full у альбомов нет: любой альбом пишется тем, что пришло, а урезанная
    версия (вложенная в песню/relationships) не затирает уже сохранённые поля (skip_none).
    complete=True — данные из /api/albums/{id}; иначе альбом попадает в pending на догрузку."""
    if complete:
        _done_albums.add(data["id"])
    else:
        _pending_albums.add(data["id"])
    fields = dict(
        name=data.get("name"),
        full_title=data.get("full_title"),
        album_type=data.get("album_type"),
        url=data.get("url"),
        release_date=data.get("release_date"),
        language=data.get("language"),
        description_preview=data.get("description_preview"),
        cover_art_url=data.get("cover_art_url"),
        cover_art_thumbnail_url=data.get("cover_art_thumbnail_url"),
        album_art_primary_color=data.get("album_art_primary_color"),
        album_art_secondary_color=data.get("album_art_secondary_color"),
        song_pageviews=data.get("song_pageviews"),
        updated_at=data.get("updated_at"),
    )
    upsert(session, Album, {"id": data["id"]}, fields, skip_none=True)


def upsert_tags(session: Session, song_id: int, tags: list[dict]) -> None:
    for tag in tags:
        fields = dict(
            logical_name=tag.get("logical_name"),
            name=tag.get("name"),
            is_primary=tag.get("primary", False),
        )
        upsert(session, Tag, {"song_id": song_id, "tag_id": tag["id"]}, fields)


def upsert_album_cover_arts(session: Session, album_id: int, cover_arts: list[dict]) -> None:
    """label НЕ трогаем при обновлении — это поле для ручной правки (см. models.py)."""
    for cover in cover_arts:
        fields = dict(
            album_id=album_id,
            image_url=cover.get("image_url"),
            thumbnail_image_url=cover.get("thumbnail_image_url"),
            url=cover.get("url"),
        )
        existing = session.get(AlbumCoverArt, cover["id"])
        if existing is None:
            session.add(AlbumCoverArt(id=cover["id"], label="Cover", **fields))
        else:
            for key, value in fields.items():
                setattr(existing, key, value)


# Связи ─────────────────────────────────────────────────────────────────────────────────


def link_song_artists(session: Session, song_id: int, primary_artists: list[dict]) -> None:
    for artist in primary_artists:
        upsert_artist(session, artist)
        link(session, SongArtist, song_id=song_id, artist_id=artist["id"])


def link_album_artists(session: Session, album_id: int, primary_artists: list[dict]) -> None:
    for artist in primary_artists:
        upsert_artist(session, artist)
        link(session, AlbumArtist, album_id=album_id, artist_id=artist["id"])


def link_album_song(session: Session, album_id: int, song_id: int) -> None:
    """Пустая связь album<->song (без номеров), если её ещё нет. Номера
    заполняются отдельно через set_album_song_position() из /albums/{id}/tracks."""
    link(session, AlbumSong, album_id=album_id, song_id=song_id)


def set_album_song_position(
    session: Session,
    album_id: int,
    song_id: int,
    *,
    disc_number: int | None,
    disc_track_number: int | None,
    number: int | None,
) -> None:
    fields = dict(disc_number=disc_number, disc_track_number=disc_track_number, number=number)
    upsert(session, AlbumSong, {"album_id": album_id, "song_id": song_id}, fields)


def add_performances(session: Session, song_id: int, custom_performances: list[dict]) -> None:
    """custom_performances -> таблица performances (Distributor, Label, Video Director и т.д.)."""
    for entry in custom_performances:
        role = entry.get("label")
        for artist in entry.get("artists", []):
            upsert_artist(session, artist)
            get_or_create(session, Performance, song_id=song_id, artist_id=artist["id"], role=role)


def add_credits(session: Session, song_id: int, song: dict) -> None:
    """primary_artists / featured_artists / writer_artists / producer_artists -> таблица credits."""
    for field, role in ROLE_FIELDS.items():
        for artist in song.get(field, []) or []:
            upsert_artist(session, artist)
            get_or_create(session, Credit, song_id=song_id, artist_id=artist["id"], role=role)


def add_relationships(session: Session, song_id: int, song_relationships: list[dict]) -> None:
    for rel in song_relationships:
        rel_type = rel.get("relationship_type")
        for related_song in rel.get("songs", []):
            # связанная песня могла быть не спаршена полностью — сохраняем как заглушку
            upsert_song(session, related_song, full=False)
            link_song_artists(session, related_song["id"], related_song.get("primary_artists", []))
            get_or_create(
                session,
                SongRelationship,
                song_id=song_id,
                related_song_id=related_song["id"],
                relationship_type=rel_type,
            )


def add_album_performances(session: Session, album_id: int, song_performances: list[dict]) -> None:
    """song_performances альбома -> album_performances (Featuring, Producers, Writers, Label)."""
    for entry in song_performances:
        role = entry.get("label")
        for artist in entry.get("artists", []):
            upsert_artist(session, artist)
            get_or_create(
                session, AlbumPerformance, album_id=album_id, artist_id=artist["id"], role=role
            )


def add_album_relationships(
    session: Session, album_id: int, album_relationships: list[dict]
) -> None:
    for rel in album_relationships:
        rel_type = rel.get("relationship_type")
        for related_album in rel.get("albums", []):
            upsert_album(session, related_album)
            link_album_artists(
                session, related_album["id"], related_album.get("primary_artists", [])
            )
            get_or_create(
                session,
                AlbumRelationship,
                album_id=album_id,
                related_album_id=related_album["id"],
                relationship_type=rel_type,
            )


# ─────────────────────────── Главный конвейер ───────────────────────────


def ingest_song(session: Session, song: dict) -> None:
    """Полная загрузка одного объекта song (как из /api/songs/{id}) в БД."""
    upsert_song(session, song, full=True)
    link_song_artists(session, song["id"], song.get("primary_artists", []))
    upsert_tags(session, song["id"], song.get("tags", []))
    add_performances(session, song["id"], song.get("custom_performances", []))
    add_credits(session, song["id"], song)
    add_relationships(session, song["id"], song.get("song_relationships", []))

    for album in song.get("albums", []):
        # album здесь — урезанная версия из тела песни; skip_none в upsert_album
        # не даёт ей затереть уже сохранённый полный альбом пустыми полями.
        upsert_album(session, album)
        link_album_artists(session, album["id"], album.get("primary_artists", []))
        link_album_song(session, album["id"], song["id"])


def save_songs(songs: list[dict]) -> None:
    with new_session() as session:
        for song in songs:
            ingest_song(session, song)
        session.commit()


def ingest_album(session: Session, album: dict) -> None:
    """Полная загрузка одного объекта album (как из /api/albums/{id}) в БД."""
    upsert_album(session, album, complete=True)
    link_album_artists(session, album["id"], album.get("primary_artists", []))
    add_album_performances(session, album["id"], album.get("song_performances", []))
    add_album_relationships(session, album["id"], album.get("album_relationships", []))
    upsert_album_cover_arts(session, album["id"], album.get("cover_arts", []))


def save_album(album: dict) -> None:
    with new_session() as session:
        ingest_album(session, album)
        session.commit()


def ingest_album_tracks(session: Session, album_id: int, tracks: list[dict]) -> None:
    """Данные из /api/albums/{id}/tracks. Из каждого элемента используем только
    disc_number, disc_track_number, number — сама песня пишется как заглушка
    (full=False), только чтобы не сломать FK, остальные её поля не трогаем."""
    for item in tracks:
        song_stub = item["song"]
        upsert_song(session, song_stub, full=False)
        link_song_artists(session, song_stub["id"], song_stub.get("primary_artists", []))
        set_album_song_position(
            session,
            album_id=album_id,
            song_id=song_stub["id"],
            disc_number=item.get("disc_number"),
            disc_track_number=item.get("disc_track_number"),
            number=item.get("number"),
        )


def save_album_tracks(album_id: int, tracks: list[dict]) -> None:
    with new_session() as session:
        ingest_album_tracks(session, album_id, tracks)
        session.commit()


def save_artist_details(artist: dict) -> None:
    """Полная карточка артиста, найденного по ходу парсинга (НЕ явный парсинг):
    пишем все поля, но full (дискография) не трогаем."""
    with new_session() as session:
        upsert_artist(session, artist, complete=True)
        session.commit()


def save_artist(artist: dict) -> None:
    """Вызывается только из parse_artist/parse_full — то есть только когда это
    ЯВНЫЙ парсинг именно этого артиста, поэтому full=True (дискография спарсена)
    всегда обоснован."""
    with new_session() as session:
        upsert_artist(session, artist, full=True)
        session.commit()