# Genius app

Полный проект: парсер Genius → БД → FastAPI read-API → Svelte SPA.

## Структура

```
Makefile
backend/
  app/
    models.py         # SQLModel-схема — общий контракт для записи и чтения
    database.py        # sync engine + Session — для read-API
    config.py           # pydantic-settings
    schemas.py           # Pydantic v2 — response-модели
    repository/           # read-only запросы (используются роутерами)
    routers/                # FastAPI эндпоинты
    ingest/                  # write-путь: бывшие db.py + genius_parser.py
      helpers.py              # generic upsert()/link()/get_or_create()
      database.py               # async engine (aiosqlite) — та же БД, другой драйвер
      genius_client.py            # HTTP-запросы к Genius API
      pipeline.py                  # upsert_*, ingest_song/album, save_*
      commands.py                   # parse_artist/parse_song/parse_album/parse_full
      cli.py                          # точка входа для `make parse`
frontend/
  src/                    # Svelte 5 + Vite, svelte-spa-router (SPA, без перезагрузок)
```

Модели теперь одни на весь проект: `app/models.py` пишет `ingest/pipeline.py`
(асинхронно, через `ingest/database.py`) и читает `repository/*`
(синхронно, через `app/database.py`). Это два разных `Engine` на один и
тот же файл БД — SQLite это позволяет, разные драйверы (`sqlite3` vs
`aiosqlite`) просто открывают одно и то же соединение с диском.

## Установка

```bash
make install
```
Эквивалент `cd backend && uv sync` + `cd frontend && bun install`.

Требования: [uv](https://docs.astral.sh/uv/) (сам скачает Python 3.14 по `.python-version`) и [bun](https://bun.sh/).

Положи файлы шрифтов в `frontend/public/fonts/`
(Roboto-Regular.ttf, Roboto-Medium.ttf, Roboto-Bold.ttf).

## Парсер — загрузка в БД

```bash
make parse 1994624            # полный пайплайн: артист -> альбомы -> треки -> песни
make parse artist 1994624     # только карточка артиста
make parse song 581415        # только одна песня (её related-песни попадут как заглушки — это ок)
make parse album 581407       # альбом + треклист + полные данные каждой песни в нём
```

Всё это — обёртки над `cd backend && uv run python -m app.ingest.cli ...`.
Первый запуск сам создаст таблицы (`init_db()`) в файле, который указан в
`APP_DATABASE_URL` (по умолчанию `sqlite:///./genius.db`, см.
`backend/.env.example`).

## Запуск

```bash
make dev   # FastAPI  — http://127.0.0.1:8000
make web   # Vite dev — http://localhost:5173 (проксирует /api на 8000)
```

- `GET /api/artists`
- `GET /api/artists/{id}` — артист + его альбомы
- `GET /api/albums/{id}` — альбом целиком (треки, жанры, credits, страна/язык, обложки)
- `GET /api/songs/{id}` — трек целиком (артисты, жанры, credits, альбомы, где встречается)

`make lint` — `ruff check` и `ruff format --check` для backend; `make fix` — автоисправление и форматирование.

## Почему так мало переходов между страницами

Роутинг полностью на клиенте (`svelte-spa-router`, хэш-адреса вида
`#/albums/1`): переход между страницами не перезагружает документ —
меняется только компонент внутри `<main>`, данные подгружаются через
`fetch` к `/api/*`. Полная загрузка документа — только один раз.

## Что сознательно не сделано (как просили)

- Нет тестов, нет Alembic-миграций, нет пагинации/фильтров на бэке.
- Нет данных о длительности трека и числовом рейтинге альбома — их нет в
  исходной схеме Genius API, поэтому соответствующие элементы макета не
  рендерятся, если данных нет.
- Секция «Physical releases» из макета переиспользована под
  `AlbumCoverArt` (альтернативные обложки) — единственные похожие
  данные, которые реально приходят из API.

## Исправленный баг: альбомы теряли поля

`ingest_song()` для каждой песни дописывает связь с её альбомом — но
объект `album`, который приходит внутри тела песни (`song["albums"]`),
урезанный: там нет большинства полей, это просто ссылка "эта песня
входит в такой-то альбом". Раньше `upsert_album(session, album)`
вызывался тут без `full=False`, и т.к. запись с `full=True`
разрешено перезаписывать чем угодно — этот урезанный объект **затирал**
уже сохранённый через `/api/albums/{id}` полный альбом почти пустыми
полями. Каждый раз, когда после загрузки альбома парсер шёл по его
трекам и сохранял песни, альбом лысел. Починено — теперь `full=False`.

(Примечание: на момент починки этого бага поле называлось `is_stub`
с обратной логикой; позже переименовано в `full`, см. раздел про
`full` ниже — суть фикса та же.)

## Флаг `full`

У `Artist`, `Song` и `Album` есть булево поле `full`:

- `full=True` — данные пришли из выделенного эндпоинта именно для этой
  сущности (`/api/artists/{id}`, `/api/songs/{id}`, `/api/albums/{id}`),
  то есть загружены целиком.
- `full=False` (по умолчанию) — запись попала в базу только как
  побочный продукт другой загрузки: артист как соавтор/фит/продюсер,
  альбом как ссылка внутри тела песни, песня как элемент треклиста или
  song_relationships. Полей там немного, и `full=False` защищает такую
  запись от перезаписи, а уже полноценную запись — от порчи (см. раздел
  про баг выше).

Для артиста `full=True` ставится ТОЛЬКО при явном `make parse artist <id>`
или как часть `make parse <id>` (полный пайплайн) — то есть когда это
явно "наш" артист, а не чей-то кредит. Это поле использует и главная
страница: артисты группируются на «Fully parsed» (full=True) → «With
albums» (не full, но есть хотя бы один альбом) → «Other artists» (всё
остальное).

## Известное упрощение

`ingest/commands.py` (`parse_full`, `parse_album`) открывает отдельную
`AsyncSession` на каждый альбом (несколько commit'ов за прогон), а не
одну сессию на весь запуск — чтобы частичный сбой на середине
дискографии не терял уже загруженные альбомы. Это тот же компромисс,
что был в исходном `db.py`/`genius_parser.py`, просто явно вынесенный
наружу.
