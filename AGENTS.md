# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

## Authoritative docs and gates

- Product/spec: `docs/spec.md` (build cards, watermark math, honesty guardrails).
- Default model mode is **fake** internally for any residual server paths; CI must never download weights. The **shipped UI is a static gallery** of frozen fixtures — no live generation surface.
- Full gate: `make ci` (lint + typecheck + test + production build).

## Generate-pair architecture (offline + optional API)

- Green-list / detector: `server/loaded_dicewriter/core/` + `watermark/kgw_inspectable.py`.
- Real model path: `inference/transformers_backend.py` — path-coupled CRN clean/loaded sampling with logit bias (required for KGW). Used by the **offline** gallery script; not by the browser.
- Teaching key fingerprint is `4ac2…` (`core/keys.py`); never send full key material to the browser.
- Honesty: user-facing copy must not claim closed-model or generic “AI-generated” detection.

## UX defaults (owner feedback)

- **Whole experience:** browsable gallery of frozen real-model English pairs (`web/src/data/demo-gallery.json`) — varied prompts + watermark strengths, clean vs watermarked with genuine detector numbers. Continuous prompt→continuation passage with subtle `tok--diff` highlights.
- **No live “generate your own” UI** — no Stop button, no spinner. How-it-works / try-it-yourself + honest-scope live in the README only (not on the page).
- **Offline fixture model:** `Qwen/Qwen2.5-0.5B` via HF transformers (default in `scripts/generate_demo_example.py`). Full logit access for KGW; Ollama cannot do per-step logit bias. Runtime stays weightless — only the frozen JSON ships. Escalate to Qwen2.5-1.5B offline if needed.
- **Single page:** brand bar + short concept intro + gallery. No Settings, no sidebar, no engine-status chrome, no how-it-works section on-page.
- Regenerate: `scripts/generate_demo_example.py` (see README). Documented for readers who want their own pairs.

## Maintaining this file

Keep this file for knowledge useful to almost every future session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
