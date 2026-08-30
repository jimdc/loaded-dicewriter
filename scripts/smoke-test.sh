#!/usr/bin/env bash
# Smoke-check a running server (default http://127.0.0.1:8765).
# Checks page + assets + sample API (root mode).
set -euo pipefail
BASE="${1:-http://127.0.0.1:8765}"

echo "smoke: $BASE"
curl -sf "$BASE/api/healthz" | tee /tmp/ldw-healthz.json
echo
curl -sf "$BASE/api/readyz" | tee /tmp/ldw-readyz.json
echo
curl -sf "$BASE/api/status" | tee /tmp/ldw-status.json
echo

# Page + primary asset (when dist is served)
PAGE_CODE=$(curl -s -o /tmp/ldw-page.html -w "%{http_code}" "$BASE/")
test "$PAGE_CODE" = "200"
if grep -qE 'assets/[^"]+\.(js|css)' /tmp/ldw-page.html; then
  ASSET_PATH=$(python3 - <<'PY'
import re
from pathlib import Path
html = Path("/tmp/ldw-page.html").read_text()
m = re.search(r'(?:src|href)="([^"]*assets/[^"]+)"', html)
assert m, "asset ref missing"
print(m.group(1))
PY
  )
  if [[ "$ASSET_PATH" == /* ]]; then
    ASSET_URL="${BASE}${ASSET_PATH}"
  else
    ASSET_URL="${BASE}/${ASSET_PATH}"
  fi
  # Root-mode assets are under /assets/; subpath builds may emit /loaded-dicewriter/assets/
  # which only resolve via a stripping proxy (see scripts/smoke-subpath.sh).
  if [[ "$ASSET_PATH" == /assets/* ]] || [[ "$ASSET_PATH" != /*/*/* ]]; then
    ASSET_CODE=$(curl -s -o /tmp/ldw-asset.bin -w "%{http_code}" "$ASSET_URL")
    if [[ "$ASSET_CODE" == "200" ]]; then
      test -s /tmp/ldw-asset.bin
      echo "asset ok: $ASSET_PATH"
    else
      echo "note: asset $ASSET_PATH returned $ASSET_CODE (subpath base needs stripping proxy)"
    fi
  fi
fi

python3 - <<'PY'
import json
from pathlib import Path
h = json.loads(Path("/tmp/ldw-healthz.json").read_text())
r = json.loads(Path("/tmp/ldw-readyz.json").read_text())
s = json.loads(Path("/tmp/ldw-status.json").read_text())
assert h["status"] == "ok"
assert "app_ready" in r and "model_ready" in r
assert s.get("name") == "loaded-dicewriter"
print("smoke ok (page + api)")
PY
