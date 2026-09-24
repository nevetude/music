"""Сохранение объектов Genius API в БД. Логика 1:1 с исходным db.py,
но upsert/link-паттерны вынесены в helpers.py — вместо восьми почти
одинаковых блоков "get -> add или setattr" здесь только сами данные."""

from sqlmodel.ext.asyncio.session import AsyncSession

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
from .database import new_session
from .helpers import get_or_create, link, upsert

# Поля-массивы артистов, которые НЕ входят в custom_performances,
# но должны попасть в credits с соответствующей ролью.
ROLE_FIELDS = {
    "primary_artists": "Primary",
    "featured_artists": "Feature",
    "writer_artists": "Writer",
    "producer_artists": "Producer",
}


# ─────────────────────────── Upsert базовых сущностей ───────────────────────────


async def upsert_artist(session: AsyncSession, data: dict, *, full: bool = False) -> None:
    """full=True — ТОЛЬКО когда карточка пришла из явного парсинга артиста
    (make parse artist <id> либо корневой артист в make parse <id>, см. save_artist).
    Во всех остальных местах (артист как соавтор/фит/продюсер чужой сущности)
    full остаётся False по умолчанию, даже если пришедших полей достаточно много.
    Уже полную карточку неполными данными не перезаписываем — та же защита, что у Song/Album."""
    existing = await session.get(Artist, data["id"])
    if existing is not None and existing.full and not full:
        return

    name_components = data.get("name_components") or {}
    fields = dict(
        name=data.get("name"),
        slug=data.get("slug"),
        url=data.get("url"),
        image_url=data.get("image_url"),
        header_image_url=data.get("header_image_url"),
        is_verified=data.get("is_verified"),
        is_meme_verified=data.get("is_meme_verified"),
        followers_count=data.get("followers_count"),
        base_name=name_components.get("base_name"),
        disambiguator=name_components.get("disambiguator"),
        description=data.get("description"),
        description_preview=data.get("description_preview"),
        translation_artist=data.get("translation_artist"),
        full=full,
    )
    await upsert(session, Artist, {"id": data["id"]}, fields)

    for alt_name in data.get("alternate_names", []) or []:
        await link(session, ArtistAlternateName, artist_id=data["id"], name=alt_name)


async def upsert_song(session: AsyncSession, data: dict, *, full: bool) -> None:
    """full=False — песня пришла только из song_relationships/треклиста (неполные данные).
    Уже полную запись (full=True) неполной версией не перезаписываем."""
    existing = await session.get(Song, data["id"])
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
        description=data.get("description"),
        description_preview=data.get("description_preview"),
        header_image_url=data.get("header_image_url"),
        header_image_thumbnail_url=data.get("header_image_thumbnail_url"),
        song_art_image_url=data.get("song_art_image_url"),
        song_art_image_thumbnail_url=data.get("song_art_image_thumbnail_url"),
        song_art_primary_color=data.get("song_art_primary_color"),
        song_art_secondary_color=data.get("song_art_secondary_color"),
        song_art_text_color=data.get("song_art_text_color"),
        soundcloud_url=data.get("soundcloud_url"),
        youtube_url=data.get("youtube_url"),
        youtube_start=data.get("youtube_start"),
        spotify_uuid=data.get("spotify_uuid"),
        pageviews=stats.get("pageviews"),
        updated_at=data.get("updated_at"),
        full=full,
    )
    await upsert(session, Song, {"id": data["id"]}, fields)


async def upsert_album(session: AsyncSession, data: dict, *, full: bool) -> None:
    """full=False — альбом пришёл только из album_relationships/тела песни (неполные данные)."""
    existing = await session.get(Album, data["id"])
    if existing is not None and existing.full and not full:
        return  # уже есть полноценная запись — заглушкой не портим

    fields = dict(
        name=data.get("name"),
        full_title=data.get("full_title"),
        album_type=data.get("album_type"),
        url=data.get("url"),
        release_date=data.get("release_date"),
        language=data.get("language"),
        description_preview=data.get("description_preview"),
        custom_header_image_url=data.get("custom_header_image_url"),
        header_image_url=data.get("header_image_url"),
        cover_art_url=data.get("cover_art_url"),
        cover_art_thumbnail_url=data.get("cover_art_thumbnail_url"),
        album_art_primary_color=data.get("album_art_primary_color"),
        album_art_secondary_color=data.get("album_art_secondary_color"),
        album_art_text_color=data.get("album_art_text_color"),
        song_pageviews=data.get("song_pageviews"),
        updated_at=data.get("updated_at"),
        full=full,
    )
    await upsert(session, Album, {"id": data["id"]}, fields)


async def upsert_tags(session: AsyncSession, song_id: int, tags: list[dict]) -> None:
    for tag in tags:
        fields = dict(
            logical_name=tag.get("logical_name"),
            name=tag.get("name"),
            is_primary=tag.get("primary", False),
        )
        await upsert(session, Tag, {"song_id": song_id, "tag_id": tag["id"]}, fields)


async def upsert_album_cover_arts(
    session: AsyncSession, album_id: int, cover_arts: list[dict]
) -> None:
    """label НЕ трогаем при обновлении — это поле для ручной правки (см. models.py)."""
    for cover in cover_arts:
        fields = dict(
            album_id=album_id,
            image_url=cover.get("image_url"),
            thumbnail_image_url=cover.get("thumbnail_image_url"),
            url=cover.get("url"),
        )
        existing = await session.get(AlbumCoverArt, cover["id"])
        if existing is None:
            session.add(AlbumCoverArt(id=cover["id"], label="Cover", **fields))
        else:
            for key, value in fields.items():
                setattr(existing, key, value)


# ─────────────────────────── Связи ───────────────────────────


async def link_song_artists(
    session: AsyncSession, song_id: int, primary_artists: list[dict]
) -> None:
    for artist in primary_artists:
        await upsert_artist(session, artist)
        await link(session, SongArtist, song_id=song_id, artist_id=artist["id"])


async def link_album_artists(
    session: AsyncSession, album_id: int, primary_artists: list[dict]
) -> None:
    for artist in primary_artists:
        await upsert_artist(session, artist)
        await link(session, AlbumArtist, album_id=album_id, artist_id=artist["id"])


async def link_album_song(session: AsyncSession, album_id: int, song_id: int) -> None:
    """Пустая связь album<->song (без номеров), если её ещё нет. Номера
    заполняются отдельно через set_album_song_position() из /albums/{id}/tracks."""
    await link(session, AlbumSong, album_id=album_id, song_id=song_id)


async def set_album_song_position(
    session: AsyncSession,
    album_id: int,
    song_id: int,
    *,
    disc_number: int | None,
    disc_track_number: int | None,
    number: int | None,
) -> None:
    fields = dict(disc_number=disc_number, disc_track_number=disc_track_number, number=number)
    await upsert(session, AlbumSong, {"album_id": album_id, "song_id": song_id}, fields)


async def add_performances(
    session: AsyncSession, song_id: int, custom_performances: list[dict]
) -> None:
    """custom_performances -> таблица performances (Distributor, Label, Video Director и т.д.)."""
    for entry in custom_performances:
        role = entry.get("label")
        for artist in entry.get("artists", []):
            await upsert_artist(session, artist)
            await get_or_create(
                session, Performance, song_id=song_id, artist_id=artist["id"], role=role
            )


async def add_credits(session: AsyncSession, song_id: int, song: dict) -> None:
    """primary_artists / featured_artists / writer_artists / producer_artists -> таблица credits."""
    for field, role in ROLE_FIELDS.items():
        for artist in song.get(field, []) or []:
            await upsert_artist(session, artist)
            await get_or_create(session, Credit, song_id=song_id, artist_id=artist["id"], role=role)


async def add_relationships(
    session: AsyncSession, song_id: int, song_relationships: list[dict]
) -> None:
    for rel in song_relationships:
        rel_type = rel.get("relationship_type")
        for related_song in rel.get("songs", []):
            # связанная песня могла быть не спаршена полностью — сохраняем как заглушку
            await upsert_song(session, related_song, full=False)
            await link_song_artists(
                session, related_song["id"], related_song.get("primary_artists", [])
            )
            await get_or_create(
                session,
                SongRelationship,
                song_id=song_id,
                related_song_id=related_song["id"],
                relationship_type=rel_type,
            )


async def add_album_performances(
    session: AsyncSession, album_id: int, song_performances: list[dict]
) -> None:
    """song_performances альбома -> album_performances (Featuring, Producers, Writers, Label)."""
    for entry in song_performances:
        role = entry.get("label")
        for artist in entry.get("artists", []):
            await upsert_artist(session, artist)
            await get_or_create(
                session, AlbumPerformance, album_id=album_id, artist_id=artist["id"], role=role
            )


async def add_album_relationships(
    session: AsyncSession, album_id: int, album_relationships: list[dict]
) -> None:
    for rel in album_relationships:
        rel_type = rel.get("relationship_type")
        for related_album in rel.get("albums", []):
            # связанный альбом мог быть не спаршен полностью — сохраняем как заглушку
            await upsert_album(session, related_album, full=False)
            await link_album_artists(
                session, related_album["id"], related_album.get("primary_artists", [])
            )
            await get_or_create(
                session,
                AlbumRelationship,
                album_id=album_id,
                related_album_id=related_album["id"],
                relationship_type=rel_type,
            )


# ─────────────────────────── Главный конвейер ───────────────────────────


async def ingest_song(session: AsyncSession, song: dict) -> None:
    """Полная загрузка одного объекта song (как из /api/songs/{id}) в БД."""
    await upsert_song(session, song, full=True)
    await link_song_artists(session, song["id"], song.get("primary_artists", []))
    await upsert_tags(session, song["id"], song.get("tags", []))
    await add_performances(session, song["id"], song.get("custom_performances", []))
    await add_credits(session, song["id"], song)
    await add_relationships(session, song["id"], song.get("song_relationships", []))

    for album in song.get("albums", []):
        # ВАЖНО: album здесь — урезанная версия из тела песни (не /api/albums/{id}),
        # поэтому full=False — иначе она затирает уже сохранённый полный альбом
        # почти пустыми полями (баг, который был здесь раньше).
        await upsert_album(session, album, full=False)
        await link_album_artists(session, album["id"], album.get("primary_artists", []))
        await link_album_song(session, album["id"], song["id"])


async def save_songs(songs: list[dict]) -> None:
    async with new_session() as session:
        for song in songs:
            await ingest_song(session, song)
        await session.commit()


async def ingest_album(session: AsyncSession, album: dict) -> None:
    """Полная загрузка одного объекта album (как из /api/albums/{id}) в БД."""
    await upsert_album(session, album, full=True)
    await link_album_artists(session, album["id"], album.get("primary_artists", []))
    await add_album_performances(session, album["id"], album.get("song_performances", []))
    await add_album_relationships(session, album["id"], album.get("album_relationships", []))
    await upsert_album_cover_arts(session, album["id"], album.get("cover_arts", []))


async def save_album(album: dict) -> None:
    async with new_session() as session:
        await ingest_album(session, album)
        await session.commit()


async def ingest_album_tracks(session: AsyncSession, album_id: int, tracks: list[dict]) -> None:
    """Данные из /api/albums/{id}/tracks. Из каждого элемента используем только
    disc_number, disc_track_number, number — сама песня пишется как заглушка
    (full=False), только чтобы не сломать FK, остальные её поля не трогаем."""
    for item in tracks:
        song_stub = item["song"]
        await upsert_song(session, song_stub, full=False)
        await link_song_artists(session, song_stub["id"], song_stub.get("primary_artists", []))
        await set_album_song_position(
            session,
            album_id=album_id,
            song_id=song_stub["id"],
            disc_number=item.get("disc_number"),
            disc_track_number=item.get("disc_track_number"),
            number=item.get("number"),
        )


async def save_album_tracks(album_id: int, tracks: list[dict]) -> None:
    async with new_session() as session:
        await ingest_album_tracks(session, album_id, tracks)
        await session.commit()


async def save_artist(artist: dict) -> None:
    """Вызывается только из parse_artist/parse_full — то есть только когда это
    ЯВНЫЙ парсинг именно этого артиста, поэтому full=True всегда обоснован."""
    async with new_session() as session:
        await upsert_artist(session, artist, full=True)
        await session.commit()
