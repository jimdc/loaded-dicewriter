# Running and deploying

Primary bind: **`127.0.0.1:8765`** (loopback). The gallery is a static shell plus a small FastAPI health surface — no model download at serve time.

## Prerequisites

- Python 3.11+ (`uv` recommended)
- Node 20+ and `pnpm`
- No GPU/model required to **view** the shipped gallery

## Install

```bash
make install
```

## Development

```bash
make dev
```

- Web UI: http://127.0.0.1:5173 (Vite proxies `/api` → backend)
- API: http://127.0.0.1:8765

## Production — root (local)

```bash
make build          # APP_BASE_PATH=/ → web/dist
./bin/serve         # 127.0.0.1:8765 (PORT=8765 HOST=127.0.0.1)
# or: make serve
```

Smoke (page + asset + `/api/*`):

```bash
make smoke
# or: bash scripts/smoke-test.sh http://127.0.0.1:8765
```

## Production — reverse-proxy subpath

If you put the app behind a reverse proxy under a path prefix (for example
`/loaded-dicewriter/`), build so asset and API URLs include that prefix. When the
proxy **strips** the prefix before forwarding, the app still serves at web root.

```bash
APP_BASE_PATH=/loaded-dicewriter/ make build
# or: make build-hub

APP_BASE_PATH=/loaded-dicewriter/ ./bin/serve
# PORT=8765 HOST=127.0.0.1
```

| Mode | Build | Browser sees | Proxy forwards to app |
| --- | --- | --- | --- |
| Root | `APP_BASE_PATH=/` | `/assets/…`, `/api/…` | n/a (hit :8765 directly) |
| Subpath (strip) | `APP_BASE_PATH=/loaded-dicewriter/` | `/loaded-dicewriter/assets/…`, `/loaded-dicewriter/api/…` | `/assets/…`, `/api/…` |

Runtime `APP_BASE_PATH` also enables optional ASGI prefix-stripping so a proxy that
forwards the full path still works without a redirect loop.

Local confirmation of subpath mode without your real proxy:

```bash
# with subpath build + serve already running on :8765
make smoke-subpath   # starts a strip-prefix proxy and checks page + asset + /api/status
```

## Process manager

Run `./bin/serve` from the repo root under any process manager you prefer
(systemd user unit, supervisord, or equivalent).

- **Command:** `./bin/serve` (or absolute path to `bin/serve`)
- **Port:** `8765` (`PORT` / `LDW_PORT` override)
- **Host:** `127.0.0.1` (`HOST` / `LDW_HOST` override)
- **Subpath env:** `APP_BASE_PATH=/loaded-dicewriter/` (must match the build)

CLI equivalent:

```bash
uv run loaded-dicewriter serve --host 127.0.0.1 --port 8765
```

Publishable artifact: **`web/dist/`** (static shell) plus the Python package serving `/api/*`.
Keep the process bound to loopback unless you deliberately open it through your own reverse proxy or network boundary.
