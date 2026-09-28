"""Точки входа для `make parse`. Четыре режима:
- parse_artist  — только карточка артиста
- parse_song    — только одна песня (её related-песни попадут как заглушки — это нормально)
- parse_album   — альбом + треклист + полные данные каждой песни в нём
- parse_full    — весь цикл: артист -> все его альбомы -> треки -> песни

Сценарии async только ради сети (httpx + asyncio.gather в genius_client). Запись в БД
синхронная: она блокирует event loop, но это безопасно — к моменту записи gather уже
завершён, параллельных сетевых задач в этот момент нет.

Логи здесь — только album/track уровня, на английском, минималистичные, со ссылками
вместо числовых id. Сохранение отдельных артистов (co-artist/feature/producer) в лог
не попадает — см. DEBUG-логи в pipeline.upsert_artist, если нужна детализация.
"""

import logging
import time

import httpx

from ..database import init_db, new_session
from . import genius_client as client
from .pipeline import (
    ingest_album,
    ingest_album_tracks,
    mark_albums_handled,
    save_artist,
    save_artist_details,
    save_songs,
    take_pending_albums,
    take_pending_artists,
)

# Имя нужно режиму логов `--log entities` (см. log_format.LOG_MODES)
logger = logging.getLogger("ingest.entities")


def log(text: str = "", *, indent: int = 0) -> None:
    """indent — nesting level (0 = top level, 1 = step inside an album, 2 = a track),
    rendered by the formatter as a '  ↳ ' branch."""
    logger.info(text, extra={"indent": indent})


def log_header(text: str) -> None:
    logger.info(text, extra={"header": True})


async def load_related(http_client: httpx.AsyncClient, indent: int = 0) -> None:
    """Сразу загружает полные данные артистов и альбомов, которые только что
    встретились как вложенные объекты. Вызывается после каждого шага сохранения
    (артист, альбом, песни), а не одним проходом в конце. Альбомы — карточка +
    треклист (песни остаются заглушками, полностью песни не тянем). Повторяется,
    пока появляются новые (альбом из relationships может привести к новым
    артистам/альбомам)."""
    while True:
        album_ids = take_pending_albums()
        artist_ids = take_pending_artists()
        if not album_ids and not artist_ids:
            return

        if album_ids:
            log(f"related albums: {len(album_ids)}", indent=indent)
            for album in await client.fetch_albums_with_client(http_client, album_ids):
                with new_session() as session:
                    ingest_album(session, album)
                    session.commit()
                try:
                    tracks = await client.fetch_album_tracks(http_client, album["id"])
                except Exception as exc:
                    logger.error("album %s tracks: failed — %s", album.get("url"), exc)
                else:
                    with new_session() as session:
                        ingest_album_tracks(session, album["id"], tracks)
                        session.commit()
                log(f"album: {album.get('url', album['id'])}", indent=indent + 1)

        if artist_ids:
            artists = await client.fetch_artists_with_client(http_client, artist_ids)
            for artist in artists:
                save_artist_details(artist)
            log(f"related artists: {len(artists)}/{len(artist_ids)}", indent=indent)


async def parse_artist(artist_id: int) -> None:
    """Только карточка артиста, без дискографии."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
        save_artist(artist)
        log(f"artist saved: {artist.get('url', artist_id)}")
        await load_related(http_client)


async def parse_song(song_id: int) -> None:
    """Одна песня целиком. Песни из её song_relationships сохранятся как
    заглушки (full=False) — это ожидаемое поведение, не полноценный парсинг."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        song = await client.fetch_song(http_client, song_id)
        save_songs([song])
        log(f"track saved: {song.get('url', song_id)}")
        await load_related(http_client)


async def parse_album(album_id: int) -> None:
    """Альбом целиком: сам альбом + треклист + полные данные каждой песни в нём."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        album = await client.fetch_album(http_client, album_id)
        with new_session() as session:
            ingest_album(session, album)
            session.commit()
        log(f"album saved: {album.get('url', album_id)}")
        await load_related(http_client, indent=1)

        tracks = await client.fetch_album_tracks(http_client, album_id)
        with new_session() as session:
            ingest_album_tracks(session, album_id, tracks)
            session.commit()

        song_ids = [t["song"]["id"] for t in tracks]
        songs = await client.fetch_songs_with_client(http_client, song_ids)

        save_songs(songs)
        for song in songs:
            log(f"track: {song.get('url', song.get('id'))}", indent=1)
        log(f"tracks saved: {len(songs)}/{len(song_ids)}", indent=1)
        await load_related(http_client, indent=1)


async def parse_full(artist_id: int) -> None:
    """Полный цикл: артист -> все его альбомы -> треки -> полные данные каждой песни."""
    started_at = time.monotonic()
    init_db()

    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
        save_artist(artist)
        log_header(artist.get("url", f"artist {artist_id}"))
        await load_related(http_client)

        album_stubs = await client.fetch_artist_albums(http_client, artist_id)
        log(f"albums found: {len(album_stubs)}")
        mark_albums_handled([a["id"] for a in album_stubs])

        total_albums_ok = 0
        total_songs_ok = 0
        total_songs_all = 0

        for i, album_stub in enumerate(album_stubs, start=1):
            album_id = album_stub["id"]
            try:
                album = await client.fetch_album(http_client, album_id)
            except Exception as exc:
                logger.error(
                    "[%s/%s] %s: failed — %s",
                    i,
                    len(album_stubs),
                    album_stub.get("url", album_id),
                    exc,
                )
                continue

            with new_session() as session:
                ingest_album(session, album)
                session.commit()
            log(f"[{i}/{len(album_stubs)}] {album.get('url', album_id)}")
            await load_related(http_client, indent=1)

            tracks = await client.fetch_album_tracks(http_client, album_id)
            with new_session() as session:
                ingest_album_tracks(session, album_id, tracks)
                session.commit()

            song_ids = [t["song"]["id"] for t in tracks]
            songs = await client.fetch_songs_with_client(http_client, song_ids)
            save_songs(songs)

            for song in songs:
                log(f"track: {song.get('url', song.get('id'))}", indent=1)
            log(f"tracks saved: {len(songs)}/{len(song_ids)}", indent=1)
            await load_related(http_client, indent=1)

            total_songs_all += len(song_ids)
            total_songs_ok += len(songs)
            total_albums_ok += 1

    elapsed = time.monotonic() - started_at
    log_header("done")
    log(f"albums: {total_albums_ok}/{len(album_stubs)}")
    log(f"tracks: {total_songs_ok}/{total_songs_all}")
    log(f"time: {elapsed:.1f}s")
