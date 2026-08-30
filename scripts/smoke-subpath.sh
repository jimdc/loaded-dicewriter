#!/usr/bin/env bash
# End-to-end check: subpath mode through a stripping reverse proxy.
#
# Prerequisites:
#   APP_BASE_PATH=/loaded-dicewriter/ make build
#   APP_BASE_PATH=/loaded-dicewriter/ ./bin/serve   # or already running on :8765
#
# This script:
#   1. Starts a tiny HTTP reverse proxy that strips /loaded-dicewriter before
#      forwarding to the app (same behaviour as a strip-prefix gateway).
#   2. Asserts page HTML, a hashed asset, and /api/status all return 200 under
#      the /loaded-dicewriter/ prefix.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_PORT="${APP_PORT:-8765}"
PROXY_PORT="${PROXY_PORT:-18765}"
SLUG="${SLUG:-loaded-dicewriter}"
APP_BASE="http://127.0.0.1:${APP_PORT}"
PROXY_BASE="http://127.0.0.1:${PROXY_PORT}"

# Ensure app is up (root routes).
curl -sf "${APP_BASE}/api/healthz" >/dev/null

# Write + start stripping proxy.
PROXY_PY="$(mktemp -t ldw-strip-proxy.XXXXXX.py)"
cleanup() {
  if [[ -n "${PROXY_PID:-}" ]]; then kill "$PROXY_PID" 2>/dev/null || true; fi
  rm -f "$PROXY_PY"
}
trap cleanup EXIT INT TERM

cat >"$PROXY_PY" <<'PY'
"""Minimal strip-prefix reverse proxy: /{slug}/x -> backend /x."""
from __future__ import annotations

import http.client
import http.server
import sys
from urllib.parse import urlsplit

SLUG = sys.argv[1]
APP_PORT = int(sys.argv[2])
LISTEN_PORT = int(sys.argv[3])
PREFIX = f"/{SLUG}"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        return

    def _forward(self) -> None:
        path = self.path
        if path == PREFIX or path.startswith(PREFIX + "/"):
            path = path[len(PREFIX) :] or "/"
        elif path == PREFIX + "?":
            path = "/"
        conn = http.client.HTTPConnection("127.0.0.1", APP_PORT, timeout=10)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
        conn.request(self.command, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() in ("transfer-encoding", "connection"):
                continue
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)
        conn.close()

    def do_GET(self) -> None:  # noqa: N802
        self._forward()

    def do_HEAD(self) -> None:  # noqa: N802
        self._forward()

    def do_POST(self) -> None:  # noqa: N802
        self._forward()


httpd = http.server.ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler)
print(f"strip-proxy listening on :{LISTEN_PORT} slug=/{SLUG} -> :{APP_PORT}", flush=True)
httpd.serve_forever()
PY

python3 "$PROXY_PY" "$SLUG" "$APP_PORT" "$PROXY_PORT" &
PROXY_PID=$!

# Wait for proxy
for _ in $(seq 1 30); do
  if curl -sf "${PROXY_BASE}/${SLUG}/api/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

echo "smoke-subpath: ${PROXY_BASE}/${SLUG}/  (strip → :${APP_PORT})"

# Page
PAGE_CODE=$(curl -s -o /tmp/ldw-subpath-page.html -w "%{http_code}" "${PROXY_BASE}/${SLUG}/")
test "$PAGE_CODE" = "200"
grep -q "loaded-dicewriter\|root\|assets" /tmp/ldw-subpath-page.html

# Asset URL from HTML (absolute path under slug)
ASSET_PATH=$(python3 - <<'PY'
import re
from pathlib import Path
html = Path("/tmp/ldw-subpath-page.html").read_text()
# Prefer script src with assets/
m = re.search(r'(?:src|href)="([^"]*assets/[^"]+)"', html)
if not m:
    raise SystemExit("no asset reference in index.html")
print(m.group(1))
PY
)
# Asset path may be absolute (/loaded-dicewriter/assets/...) or root (/assets/...)
if [[ "$ASSET_PATH" == /* ]]; then
  ASSET_URL="${PROXY_BASE}${ASSET_PATH}"
else
  ASSET_URL="${PROXY_BASE}/${SLUG}/${ASSET_PATH}"
fi
ASSET_CODE=$(curl -s -o /tmp/ldw-subpath-asset.bin -w "%{http_code}" "$ASSET_URL")
test "$ASSET_CODE" = "200"
test -s /tmp/ldw-subpath-asset.bin

# API sample
curl -sf "${PROXY_BASE}/${SLUG}/api/status" | tee /tmp/ldw-subpath-status.json
python3 - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/ldw-subpath-status.json").read_text())
assert body.get("name") == "loaded-dicewriter", body
assert body.get("telemetry") is False, body
print("smoke-subpath ok (page + asset + /api/status via stripping proxy)")
PY
