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
from .pipeline import ingest_album, ingest_album_tracks, save_artist, save_songs

logger = logging.getLogger(__name__)


def log(text: str = "", *, indent: int = 0) -> None:
    """indent — nesting level (0 = top level, 1 = step inside an album, 2 = a track),
    rendered by the formatter as a '  ↳ ' branch."""
    logger.info(text, extra={"indent": indent})


def log_header(text: str) -> None:
    logger.info(text, extra={"header": True})


async def parse_artist(artist_id: int) -> None:
    """Только карточка артиста, без дискографии."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
    save_artist(artist)
    log(f"artist saved: {artist.get('url', artist_id)}")


async def parse_song(song_id: int) -> None:
    """Одна песня целиком. Песни из её song_relationships сохранятся как
    заглушки (full=False) — это ожидаемое поведение, не полноценный парсинг."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        song = await client.fetch_song(http_client, song_id)
    save_songs([song])
    log(f"track saved: {song.get('url', song_id)}")


async def parse_album(album_id: int) -> None:
    """Альбом целиком: сам альбом + треклист + полные данные каждой песни в нём."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        album = await client.fetch_album(http_client, album_id)
        with new_session() as session:
            ingest_album(session, album)
            session.commit()
        log(f"album saved: {album.get('url', album_id)}")

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


async def parse_full(artist_id: int) -> None:
    """Полный цикл: артист -> все его альбомы -> треки -> полные данные каждой песни."""
    started_at = time.monotonic()
    init_db()

    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
        save_artist(artist)
        log_header(artist.get("url", f"artist {artist_id}"))

        album_stubs = await client.fetch_artist_albums(http_client, artist_id)
        log(f"albums found: {len(album_stubs)}")

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

            total_songs_all += len(song_ids)
            total_songs_ok += len(songs)
            total_albums_ok += 1

    elapsed = time.monotonic() - started_at
    log_header("done")
    log(f"albums: {total_albums_ok}/{len(album_stubs)}")
    log(f"tracks: {total_songs_ok}/{total_songs_all}")
    log(f"time: {elapsed:.1f}s")
