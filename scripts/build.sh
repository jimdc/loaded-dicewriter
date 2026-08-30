#!/usr/bin/env bash
# Production frontend build → web/dist (served by FastAPI same-origin).
#
# APP_BASE_PATH (optional): Vite `base` + inlined asset/API prefix.
#   unset or /                 → root (local)
#   /loaded-dicewriter/        → reverse-proxy subpath (often strip-prefix gateway)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/node/bin:${HOME}/.local/bin:${PATH}"

export APP_BASE_PATH="${APP_BASE_PATH:-/}"
VERSION="$(tr -d '[:space:]' < VERSION)"
echo "Building loaded-dicewriter v${VERSION} APP_BASE_PATH=${APP_BASE_PATH}"

cd web
pnpm install --frozen-lockfile 2>/dev/null || pnpm install
pnpm build

test -f dist/index.html
# Record the base used for this dist so serve/docs can cross-check.
printf '%s\n' "$APP_BASE_PATH" > dist/.app_base_path
echo "Artifacts: web/dist/ (static shell + assets, base=${APP_BASE_PATH})"
