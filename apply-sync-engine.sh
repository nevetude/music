#!/usr/bin/env bash
# Применяет single-sync-engine.patch, когда pipeline.py изменён локально
# (обычный `git apply` в этом случае падает на pipeline.py).
#
# Запускать из корня репозитория:
#   bash apply-sync-engine.sh [путь/к/single-sync-engine.patch]
#
# Порядок безопасный: сначала всё проверяется, и только потом меняются файлы.
set -euo pipefail

PATCH="${1:-single-sync-engine.patch}"
PIPELINE="backend/app/ingest/pipeline.py"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

[ -f "$PATCH" ] || { echo "нет файла патча: $PATCH" >&2; exit 1; }
[ -f "$PIPELINE" ] || { echo "запускай из корня репозитория ($PIPELINE не найден)" >&2; exit 1; }

# 1. Всё, кроме pipeline.py, должно ложиться чисто. Проверяем до любых изменений.
git apply --check --exclude="$PIPELINE" "$PATCH"

# 2. pipeline.py преобразуем сами: правка механическая (async/await -> sync),
#    поэтому локальные незакоммиченные изменения в файле ей не мешают.
python3 - "$PIPELINE" "$TMP" <<'PY'
import pathlib
import re
import sys

src, dst = sys.argv[1:3]
s = pathlib.Path(src).read_text()

s = s.replace("from sqlmodel.ext.asyncio.session import AsyncSession\n", "from sqlmodel import Session\n")
s = s.replace("from .database import new_session\n", "from ..database import new_session\n")
s = (
    s.replace("AsyncSession", "Session")
    .replace("async with ", "with ")
    .replace("async def ", "def ")
    .replace("await ", "")
)

# Если в локальных правках появилось что-то async, чего скрипт не знает, не гадаем.
leftover = [
    line.strip()
    for line in s.splitlines()
    if re.search(r"\b(async|await|aiosqlite|asyncio)\b|\.database import", line)
    and "..database import" not in line
]
if leftover:
    print("В pipeline.py осталось async-кода, разберись руками:", file=sys.stderr)
    for line in leftover:
        print("  " + line, file=sys.stderr)
    sys.exit(1)

pathlib.Path(dst).write_text(s)
PY

# 3. Применяем остальное и подставляем преобразованный pipeline.py.
git apply --exclude="$PIPELINE" "$PATCH"
cp "$TMP" "$PIPELINE"

# 4. Зависимости (aiosqlite уйдёт), сортировка импортов и форматирование pipeline.py.
(
    cd backend
    uv sync
    uv run ruff check --fix app/ingest/pipeline.py
    uv run ruff format app/ingest/pipeline.py
)

echo
echo "Готово. Проверь свои правки в pipeline.py: git diff backend/app/ingest/pipeline.py"
