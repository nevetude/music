"""Асинхронный клиент Genius API.

ВАЖНО: это не официальный api.genius.com (тот, что описан на docs.genius.com
и требует Bearer-токен через genius.com/api-clients) — здесь используется
внутренний, недокументированный API самого сайта genius.com, которым
пользуется его собственный фронтенд. У него нет понятия "API-ключ":
для большинства треков он открыт анонимно, но часть контента (например,
непроверенные/спорные лирики) отдаётся только залогиненной сессии — тогда
анонимный запрос получает 403, хотя в браузере с активной сессией или
через тестер на docs.genius.com (который есть отдельный, официальный API)
всё открывается. Также 403/429 может прилетать от анти-бот защиты
Cloudflare на подозрительный трафик (много параллельных запросов с
непохожим на браузер User-Agent) — от этого помогает не cookie, а более
"браузерные" заголовки, троттлинг и повтор попытки.

Покрывает эндпоинты:
    /api/songs/{id}
    /api/albums/{id}
    /api/albums/{id}/tracks
    /api/artists/{id}
    /api/artists/{id}/albums
"""

import asyncio
import logging
import random
import time

import httpx

from ..config import settings

# Один логгер на весь клиент: запросы (INFO) и ошибки. Имя нужно режиму логов
# `--log api` (см. log_format.LOG_MODES).
logger = logging.getLogger("ingest.api")

# Отдельный от дефолтного httpx/только-цифры User-Agent — часть 403 у Genius
# это анти-бот реакция на явно нечеловеческие заголовки, а не запрет доступа.
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://genius.com/",
}

SONG_URL = "https://genius.com/api/songs/{id}"
ALBUM_URL = "https://genius.com/api/albums/{id}"
ALBUM_TRACKS_URL = "https://genius.com/api/albums/{id}/tracks"
ARTIST_URL = "https://genius.com/api/artists/{id}"
ARTIST_ALBUMS_URL = "https://genius.com/api/artists/{id}/albums"

# Сколько песен качаем параллельно за раз. Полный asyncio.gather по всем
# треклистам альбома/дискографии выглядит для Cloudflare как скан — часть
# 403 была именно из-за этого, а не из-за конкретных "защищённых" песен.
MAX_CONCURRENT_SONG_REQUESTS = 5

RETRY_STATUS_CODES = {403, 429}


def _headers() -> dict[str, str]:
    """Cookie подставляется, только если задан APP_GENIUS_COOKIE — см. config.py."""
    headers = dict(BASE_HEADERS)
    if settings.genius_cookie:
        headers["Cookie"] = settings.genius_cookie
    return headers


def _path(url: str) -> str:
    return url.removeprefix("https://genius.com")


async def _request(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """Один HTTP-запрос + строка лога: `GET /api/songs/1 200 0.31s`."""
    started = time.monotonic()
    try:
        response = await client.get(url, headers=_headers(), **kwargs)
    except httpx.HTTPError as exc:
        logger.warning("GET %s failed: %s", _path(url), exc or type(exc).__name__)
        raise
    logger.info(
        "GET %s %s %.2fs",
        response.request.url.raw_path.decode(),
        response.status_code,
        time.monotonic() - started,
    )
    return response


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """GET с одним повтором при 403/429 после паузы — это часто временная
    анти-бот реакция, а не постоянный запрет. Если залогиненная cookie задана
    в settings, она используется сразу, без ожидания первого отказа."""
    response = await _request(client, url, **kwargs)
    if response.status_code in RETRY_STATUS_CODES:
        await asyncio.sleep(1.5 + random.random())
        response = await _request(client, url, **kwargs)
    response.raise_for_status()
    return response


async def fetch_song(client: httpx.AsyncClient, song_id: int) -> dict:
    response = await _get(client, SONG_URL.format(id=song_id))
    return response.json()["response"]["song"]


async def fetch_album(client: httpx.AsyncClient, album_id: int) -> dict:
    response = await _get(client, ALBUM_URL.format(id=album_id))
    return response.json()["response"]["album"]


async def fetch_album_tracks(client: httpx.AsyncClient, album_id: int) -> list[dict]:
    response = await _get(client, ALBUM_TRACKS_URL.format(id=album_id))
    return response.json()["response"]["tracks"]


async def fetch_artist(client: httpx.AsyncClient, artist_id: int) -> dict:
    response = await _get(client, ARTIST_URL.format(id=artist_id))
    return response.json()["response"]["artist"]


async def fetch_artist_albums(
    client: httpx.AsyncClient, artist_id: int, per_page: int = 50
) -> list[dict]:
    """Постранично собирает все альбомы артиста (элементы неполные — только для id)."""
    albums: list[dict] = []
    page = 1
    while True:
        response = await _get(
            client,
            ARTIST_ALBUMS_URL.format(id=artist_id),
            params={"page": page, "per_page": per_page},
        )
        batch = response.json()["response"]["albums"]
        if not batch:
            break
        albums.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return albums


async def _fetch_many(fetch, client: httpx.AsyncClient, ids: list[int], label: str) -> list[dict]:
    """Параллельно (не больше MAX_CONCURRENT_SONG_REQUESTS) вызывает fetch(client, id)
    для каждого id. Упавшие запросы логируются и не роняют остальные."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SONG_REQUESTS)

    async def _one(entity_id: int) -> dict:
        async with semaphore:
            return await fetch(client, entity_id)

    results = await asyncio.gather(*(_one(i) for i in ids), return_exceptions=True)
    items = []
    for entity_id, result in zip(ids, results, strict=True):
        if isinstance(result, Exception):
            logger.error("%s %s: failed — %s", label, entity_id, result)
            continue
        items.append(result)
    return items


async def fetch_artists_with_client(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    return await _fetch_many(fetch_artist, client, ids, "artist")


async def fetch_albums_with_client(client: httpx.AsyncClient, ids: list[int]) -> list[dict]:
    return await _fetch_many(fetch_album, client, ids, "album")


async def fetch_songs_with_client(client: httpx.AsyncClient, song_ids: list[int]) -> list[dict]:
    """Параллельно запрашивает несколько песен через уже открытый client, но не
    больше MAX_CONCURRENT_SONG_REQUESTS одновременно. Упавшие запросы не роняют
    остальные."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SONG_REQUESTS)

    async def _fetch(song_id: int) -> dict:
        async with semaphore:
            return await fetch_song(client, song_id)

    results = await asyncio.gather(
        *(_fetch(song_id) for song_id in song_ids),
        return_exceptions=True,
    )
    songs = []
    for song_id, result in zip(song_ids, results, strict=True):
        if isinstance(result, Exception):
            logger.error("song %s: failed — %s", song_id, result)
            continue
        songs.append(result)
    return songs
