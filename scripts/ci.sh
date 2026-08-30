#!/usr/bin/env bash
# Offline CI: no model download, no external network beyond already-cached deps.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/node/bin:${HOME}/.local/bin:${PATH}"
export LDW_MODEL_MODE=fake

echo "== install =="
uv sync --all-extras
cd web && pnpm install && cd ..

echo "== lint =="
uv run ruff check server
cd web && pnpm lint && cd ..

echo "== typecheck =="
uv run mypy server/loaded_dicewriter
cd web && pnpm typecheck && cd ..

echo "== test =="
uv run pytest -q
cd web && pnpm test && cd ..

echo "== build =="
bash scripts/build.sh

echo "CI passed (fake mode, no model download)"
