.PHONY: help install dev test lint typecheck build build-hub serve ci smoke smoke-subpath clean

SHELL := /bin/bash
export PATH := $(HOME)/.local/node/bin:$(HOME)/.local/bin:$(PATH)

# Fixed production port (loopback serve default).
PORT ?= 8765
HOST ?= 127.0.0.1
APP_BASE_PATH ?= /

help:
	@echo "loaded-dicewriter targets:"
	@echo "  make install      - Python (uv) + frontend (pnpm) deps"
	@echo "  make dev          - API :8765 + Vite :5173 (proxy /api)"
	@echo "  make test         - backend + frontend unit tests"
	@echo "  make lint         - ruff + frontend eslint"
	@echo "  make typecheck    - mypy + tsc --noEmit"
	@echo "  make build        - production frontend → web/dist (APP_BASE_PATH=/)"
	@echo "  make build-hub    - same with APP_BASE_PATH=/loaded-dicewriter/"
	@echo "  make serve        - production server $(HOST):$(PORT) via bin/serve"
	@echo "  make ci           - lint + typecheck + test + build (no model download)"
	@echo "  make smoke        - page + assets + /api on running server (root)"
	@echo "  make smoke-subpath - /loaded-dicewriter/ via stripping proxy"

install:
	uv sync --all-extras
	cd web && pnpm install

dev:
	bash scripts/dev.sh

test:
	uv run pytest -q
	cd web && pnpm test

lint:
	uv run ruff check server
	cd web && pnpm lint

typecheck:
	uv run mypy server/loaded_dicewriter
	cd web && pnpm typecheck

build:
	APP_BASE_PATH=$(APP_BASE_PATH) bash scripts/build.sh

build-hub:
	APP_BASE_PATH=/loaded-dicewriter/ bash scripts/build.sh

serve:
	APP_BASE_PATH=$(APP_BASE_PATH) HOST=$(HOST) PORT=$(PORT) bash bin/serve

ci:
	bash scripts/ci.sh

smoke:
	bash scripts/smoke-test.sh http://$(HOST):$(PORT)

smoke-subpath:
	bash scripts/smoke-subpath.sh

clean:
	rm -rf web/dist web/node_modules .venv server/.pytest_cache server/**/__pycache__
	rm -rf .mypy_cache .ruff_cache web/coverage
