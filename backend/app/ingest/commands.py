"""Точки входа для `make parse`. Четыре режима:
- parse_artist  — только карточка артиста
- parse_song    — только одна песня (её related-песни попадут как заглушки — это нормально)
- parse_album   — альбом + треклист + полные данные каждой песни в нём
- parse_full    — весь цикл: артист -> все его альбомы -> треки -> песни

Сценарии async только ради сети (httpx + asyncio.gather в genius_client). Запись в БД
синхронная: она блокирует event loop, но это безопасно — к моменту записи gather уже
завершён, параллельных сетевых задач в этот момент нет.
"""

import time

import httpx

from ..database import init_db, new_session
from . import genius_client as client
from .pipeline import ingest_album, ingest_album_tracks, save_artist, save_songs


def log(text: str = "") -> None:
    print(text)


def log_header(text: str) -> None:
    line = "─" * 60
    log(f"\n{line}\n{text}\n{line}")


async def parse_artist(artist_id: int) -> None:
    """Только карточка артиста, без дискографии."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
    save_artist(artist)
    log(f"Артист {artist_id} сохранён: {artist['name']!r}")


async def parse_song(song_id: int) -> None:
    """Одна песня целиком. Песни из её song_relationships сохранятся как
    заглушки (full=False) — это ожидаемое поведение, не полноценный парсинг."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        song = await client.fetch_song(http_client, song_id)
    save_songs([song])
    log(f"Песня {song_id} сохранена: {song['title']!r}")


async def parse_album(album_id: int) -> None:
    """Альбом целиком: сам альбом + треклист + полные данные каждой песни в нём."""
    init_db()
    async with httpx.AsyncClient(timeout=15) as http_client:
        album = await client.fetch_album(http_client, album_id)
        with new_session() as session:
            ingest_album(session, album)
            session.commit()
        log(f"✓ альбом {album_id} сохранён: {album.get('name')!r}")

        tracks = await client.fetch_album_tracks(http_client, album_id)
        with new_session() as session:
            ingest_album_tracks(session, album_id, tracks)
            session.commit()
        log(f"✓ треков в альбоме: {len(tracks)}")

        song_ids = [t["song"]["id"] for t in tracks]
        songs = await client.fetch_songs_with_client(http_client, song_ids)

    save_songs(songs)
    log(f"✓ песен загружено полностью: {len(songs)}/{len(song_ids)}")


async def parse_full(artist_id: int) -> None:
    """Полный цикл: артист -> все его альбомы -> треки -> полные данные каждой песни."""
    started_at = time.monotonic()
    init_db()

    async with httpx.AsyncClient(timeout=15) as http_client:
        artist = await client.fetch_artist(http_client, artist_id)
        save_artist(artist)
        log_header(f"Артист: {artist['name']} (id={artist_id})")
        log("✓ карточка артиста сохранена")

        album_stubs = await client.fetch_artist_albums(http_client, artist_id)
        log(f"→ альбомов найдено: {len(album_stubs)}")

        total_albums_ok = 0
        total_songs_ok = 0
        total_songs_all = 0

        for i, album_stub in enumerate(album_stubs, start=1):
            album_id = album_stub["id"]
            try:
                album = await client.fetch_album(http_client, album_id)
            except Exception as exc:
                log(f"\n[{i}/{len(album_stubs)}] альбом id={album_id}: ✗ ошибка загрузки — {exc}")
                continue

            with new_session() as session:
                ingest_album(session, album)
                session.commit()
            log(f"\n[{i}/{len(album_stubs)}] {album.get('name')!r} (id={album_id})")
            log("   ✓ альбом сохранён")

            tracks = await client.fetch_album_tracks(http_client, album_id)
            with new_session() as session:
                ingest_album_tracks(session, album_id, tracks)
                session.commit()
            log(f"   ✓ треков в альбоме: {len(tracks)}")

            song_ids = [t["song"]["id"] for t in tracks]
            songs = await client.fetch_songs_with_client(http_client, song_ids)
            save_songs(songs)

            total_songs_all += len(song_ids)
            total_songs_ok += len(songs)
            total_albums_ok += 1
            log(f"   ✓ песен загружено полностью: {len(songs)}/{len(song_ids)}")

    elapsed = time.monotonic() - started_at
    log_header("Готово")
    log(f"Альбомов обработано: {total_albums_ok}/{len(album_stubs)}")
    log(f"Песен загружено:     {total_songs_ok}/{total_songs_all}")
    log(f"Время:               {elapsed:.1f}s")
