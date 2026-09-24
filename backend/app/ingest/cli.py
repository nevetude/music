"""Запуск через `make parse`:
make parse 123          -> полный пайплайн по артисту 123 (как раньше)
make parse artist 123   -> только карточка артиста
make parse song 124     -> только одна песня
make parse album 125    -> альбом + треклист + все его песни
"""

import argparse
import asyncio
import sys
from collections.abc import Coroutine
from typing import Any

from . import commands

MODES: dict[str, Any] = {
    "artist": commands.parse_artist,
    "song": commands.parse_song,
    "album": commands.parse_album,
}


def build_coroutine(mode_or_id: str, entity_id: int | None) -> Coroutine:
    if mode_or_id in MODES:
        if entity_id is None:
            raise ValueError(f"режим '{mode_or_id}' требует id, например: {mode_or_id} 123")
        return MODES[mode_or_id](entity_id)

    try:
        artist_id = int(mode_or_id)
    except ValueError as exc:
        raise ValueError("первым аргументом укажи id артиста или режим artist/song/album") from exc
    return commands.parse_full(artist_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузка данных Genius в БД")
    parser.add_argument(
        "mode_or_id", help="id артиста (полный парсинг) или режим artist/song/album"
    )
    parser.add_argument(
        "id", nargs="?", type=int, help="id сущности, если первым аргументом указан режим"
    )
    args = parser.parse_args()

    try:
        coro = build_coroutine(args.mode_or_id, args.id)
    except ValueError as exc:
        parser.error(str(exc))
        return

    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
        sys.exit(1)


if __name__ == "__main__":
    main()
