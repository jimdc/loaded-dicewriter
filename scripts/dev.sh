#!/usr/bin/env bash
# One-command local development: FastAPI + Vite with same-origin /api proxy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/node/bin:${HOME}/.local/bin:${PATH}"

if [[ ! -d .venv ]] && [[ ! -f uv.lock ]]; then
  echo "Run: make install" >&2
  exit 1
fi

API_HOST="${LDW_HOST:-127.0.0.1}"
API_PORT="${LDW_PORT:-8765}"
WEB_PORT="${LDW_WEB_PORT:-5173}"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
  if [[ -n "${WEB_PID:-}" ]]; then kill "$WEB_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

echo "loaded-dicewriter dev"
echo "  API  http://${API_HOST}:${API_PORT}"
echo "  Web  http://127.0.0.1:${WEB_PORT}  (proxies /api → API)"
echo "  Fake model mode — no GPU/weights required"

uv run uvicorn loaded_dicewriter.app:app \
  --host "$API_HOST" \
  --port "$API_PORT" \
  --reload \
  --app-dir server &
API_PID=$!

# Wait briefly for API
for _ in $(seq 1 30); do
  if curl -sf "http://${API_HOST}:${API_PORT}/api/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

cd web
pnpm exec vite --host 127.0.0.1 --port "$WEB_PORT" &
WEB_PID=$!

wait
