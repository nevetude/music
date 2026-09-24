# `make parse ...` принимает позиционные аргументы (не переменные) —
# слова после "parse" не мейк-таргеты, а аргументы CLI-парсера.
# Стандартный трюк: перехватываем их через MAKECMDGOALS и глушим
# как no-op таргеты, чтобы make не пытался их "собрать".
ifeq (parse,$(firstword $(MAKECMDGOALS)))
  PARSE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(PARSE_ARGS):;@:)
endif

.PHONY: install dev web parse lint help

help:
	@echo "make install             — поставить зависимости backend (uv) и frontend (npm)"
	@echo "make dev                 — поднять FastAPI (http://127.0.0.1:8000)"
	@echo "make web                 — поднять Vite dev-сервер (http://localhost:5173)"
	@echo "make parse <artist_id>   — полный пайплайн: артист -> альбомы -> треки -> песни"
	@echo "make parse artist <id>   — только карточка артиста"
	@echo "make parse song <id>     — только одна песня"
	@echo "make parse album <id>    — альбом + треклист + все его песни"
	@echo "make lint                — ruff check backend"

install:
	cd backend && uv sync
	cd frontend && npm install

dev:
	cd backend && uv run uvicorn app.main:app --reload

web:
	cd frontend && npm run dev

parse:
	cd backend && uv run python -m app.ingest.cli $(PARSE_ARGS)

lint:
	cd backend && uv run ruff check .
