"""Асинхронный клиент Genius API.

Покрывает эндпоинты:
    /api/songs/{id}
    /api/albums/{id}
    /api/albums/{id}/tracks
    /api/artists/{id}
    /api/artists/{id}/albums
"""

import asyncio

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GeniusParser/1.0)"}

SONG_URL = "https://genius.com/api/songs/{id}"
ALBUM_URL = "https://genius.com/api/albums/{id}"
ALBUM_TRACKS_URL = "https://genius.com/api/albums/{id}/tracks"
ARTIST_URL = "https://genius.com/api/artists/{id}"
ARTIST_ALBUMS_URL = "https://genius.com/api/artists/{id}/albums"


async def fetch_song(client: httpx.AsyncClient, song_id: int) -> dict:
    response = await client.get(SONG_URL.format(id=song_id), headers=HEADERS)
    response.raise_for_status()
    return response.json()["response"]["song"]


async def fetch_album(client: httpx.AsyncClient, album_id: int) -> dict:
    response = await client.get(ALBUM_URL.format(id=album_id), headers=HEADERS)
    response.raise_for_status()
    return response.json()["response"]["album"]


async def fetch_album_tracks(client: httpx.AsyncClient, album_id: int) -> list[dict]:
    response = await client.get(ALBUM_TRACKS_URL.format(id=album_id), headers=HEADERS)
    response.raise_for_status()
    return response.json()["response"]["tracks"]


async def fetch_artist(client: httpx.AsyncClient, artist_id: int) -> dict:
    response = await client.get(ARTIST_URL.format(id=artist_id), headers=HEADERS)
    response.raise_for_status()
    return response.json()["response"]["artist"]


async def fetch_artist_albums(
    client: httpx.AsyncClient, artist_id: int, per_page: int = 50
) -> list[dict]:
    """Постранично собирает все альбомы артиста (элементы неполные — только для id)."""
    albums: list[dict] = []
    page = 1
    while True:
        response = await client.get(
            ARTIST_ALBUMS_URL.format(id=artist_id),
            headers=HEADERS,
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()
        batch = response.json()["response"]["albums"]
        if not batch:
            break
        albums.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return albums


async def fetch_songs_with_client(client: httpx.AsyncClient, song_ids: list[int]) -> list[dict]:
    """Параллельно запрашивает несколько песен через уже открытый client.
    Упавшие запросы не роняют остальные."""
    results = await asyncio.gather(
        *(fetch_song(client, song_id) for song_id in song_ids),
        return_exceptions=True,
    )
    songs = []
    for song_id, result in zip(song_ids, results):
        if isinstance(result, Exception):
            print(f"      ✗ песня {song_id}: ошибка — {result}")
            continue
        songs.append(result)
    return songs
