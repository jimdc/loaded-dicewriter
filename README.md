# loaded-dicewriter

A quiet, local-first **intuition pump** for one family of statistical text watermarks
(green-list / logit-bias / KGW): clean vs watermarked continuations side by side, with
measured detector scores.

**What you get in the browser:** a curated gallery of frozen real-model English pairs.
No live generation UI, no spinner, no model download at runtime — only the precomputed
text and scores ship.

**Live demo:** [bottomry.github.io/loaded-dicewriter](https://bottomry.github.io/loaded-dicewriter/)

**Stack:** React + TypeScript (strict) + Vite · Python 3.11+ · FastAPI (static shell +
health) · local-first, loopback default, no telemetry.

Build contract: [`docs/spec.md`](docs/spec.md).

## Quick start (view the gallery)

```bash
make install   # uv sync + pnpm install
make build
make serve     # 127.0.0.1:8765 — static gallery + /api/healthz
```

Open **http://127.0.0.1:8765**

For frontend HMR during shell work:

```bash
make dev       # Vite :5173 (proxies /api if you need health)
```

| Command | Purpose |
| --- | --- |
| `make install` | Python + frontend deps |
| `make test` | Backend pytest + frontend vitest |
| `make lint` / `make typecheck` | ruff, eslint, mypy, tsc |
| `make build` | Production frontend → `web/dist` |
| `make serve` | Static gallery on **127.0.0.1:8765** |
| `make ci` | lint + typecheck + test + build (**no model download**) |

## How the watermark works (short)

1. **Secret key + context** — at each generation step, a keyed PRF and the last *h*
   tokens define a **green list** of roughly fraction *γ* of the vocabulary.
2. **Logit bias** — favored (green) logits get a small additive δ before sampling.
   Alone those choices look ordinary; together they accumulate a statistical signal.
3. **Detector** — counts green hits among scored tokens and reports a **z-score**.
   This app only scores text produced under a **matching key** — it does **not**
   detect Claude, GPT, or generic “AI-generated” prose.
4. **Coupled sampling (gallery)** — clean and watermarked share **common random
   numbers** on the watermarked path, so the two strings stay near-identical except
   where the bias flips a token. Flip-rates and z-scores are **measured**, not authored.

Implementation pointers: `server/loaded_dicewriter/watermark/`,
`server/loaded_dicewriter/inference/transformers_backend.py`,
`scripts/generate_demo_example.py`.

## Honest scope

- This is a **microscope for one watermark family** (KGW-style green-list / logit bias)
  under a **known key** — not a general “AI detector.”
- User-facing copy must not claim closed-model or generic “AI-generated” detection.
- Scores and token texts in the gallery are **real model + KGW + detector** output
  (frozen offline). Do not hand-edit fixture strings to look better.

## Try it yourself — offline fixture generator

The browser never runs a real LM. To **produce your own** clean/loaded gallery pairs
(or regenerate the shipped ones), run the offline script against a **local** Hugging
Face causal LM that exposes **logits** (required for KGW bias).

### Why not Ollama?

Ollama’s generate API cannot apply **dynamic per-step logit bias**. KGW needs to
recompute the green list and add δ to favored logits every token. Use
**transformers + torch** on a local model directory.

### Recommended model

Default: **`Qwen/Qwen2.5-0.5B`** (small, coherent English for its size, full logit
access). If continuations still feel weak, try **`Qwen/Qwen2.5-1.5B`** offline
(larger download; still not shipped with the app).

```bash
# Example: place weights once (not committed to the repo)
HF_HUB_DISABLE_XET=1 huggingface-cli download Qwen/Qwen2.5-0.5B \
  --local-dir /tmp/ldw-models/Qwen2.5-0.5B

# Install offline-only deps into the project venv (not required for viewing the gallery)
uv pip install --python .venv/bin/python torch transformers accelerate huggingface_hub

# Regenerate web/src/data/demo-gallery.json (measured flip-rates + z-scores)
LDW_DEMO_MODEL_PATH=/tmp/ldw-models/Qwen2.5-0.5B \
LDW_DEMO_MODEL_ID=Qwen2.5-0.5B \
LDW_DEMO_HF_ID=Qwen/Qwen2.5-0.5B \
LDW_DEMO_DEVICE=mps \   # or cpu
  .venv/bin/python scripts/generate_demo_example.py
```

Useful env vars (all optional):

| Variable | Role |
| --- | --- |
| `LDW_DEMO_MODEL_PATH` | Local model directory (default `/tmp/ldw-models/Qwen2.5-0.5B`) |
| `LDW_DEMO_MODEL_ID` / `LDW_DEMO_HF_ID` | Labels stamped into the JSON |
| `LDW_DEMO_DEVICE` | `mps` / `cpu` / `cuda` |
| `LDW_DEMO_TEMPERATURE` | Sampling temperature (default `0.45` — lower → fewer CRN flips) |
| `LDW_DEMO_MAX_NEW` | Max new tokens per branch (default `48`) |
| `LDW_DEMO_ONLY_ID` | Regenerate a single gallery slot id |

The script writes:

- `web/src/data/demo-gallery.json` — full gallery
- `web/src/data/demo-example.json` — first-example alias

Rebuild the frontend after regenerating so the static shell embeds the new JSON.

## Deploy (optional)

```bash
# Local root
make build && ./bin/serve          # 127.0.0.1:8765

# Behind a reverse proxy under /loaded-dicewriter/ (prefix-stripping gateway)
APP_BASE_PATH=/loaded-dicewriter/ make build
APP_BASE_PATH=/loaded-dicewriter/ ./bin/serve
```

- Static shell: **`web/dist/`** (Vite `base` from `APP_BASE_PATH`)
- Optional health: `/api/healthz`, `/api/readyz`, `/api/status`
- Fixed bind: **`127.0.0.1:8765`** via `./bin/serve`
- Details: [`docs/deployment-macos.md`](docs/deployment-macos.md)

## Layout

```text
server/loaded_dicewriter/   Python package (FastAPI, watermark, transformers backend)
web/                        React gallery (frozen demo-gallery.json)
scripts/generate_demo_example.py   Offline CRN fixture generator
config/                     Example TOML
docs/spec.md                Product/implementation spec
docs/screenshots/           Visual baseline
```

## Guardrails

- Loopback bind by default (`127.0.0.1`)
- Telemetry forced off
- Local assets only (system fonts; no CDN)
- CI never downloads model weights (`make ci`)

## License

[MIT](LICENSE)
