# loaded-dicewriter

**Private, local-first visual laboratory for statistical text watermarking**  
**Product and implementation specification — v0.1**

> Build the smallest interface that makes the entire causal chain legible:
>
> **ordinary logits → secret green list → logit bias → sampled token → accumulated evidence → degradation under editing**

This document is intended to be handed directly to a coding agent. Implement the build cards in order. Every completed card must leave the app runnable, demonstrable, and testable. Do not front-load future abstractions, infrastructure, or algorithms merely because they may become useful later.

---

## 1. Product thesis

`loaded-dicewriter` is not an “AI detector.” It is a microscope for one specific family of statistical text watermarks.

The user gives a local language model a prompt. The app produces two completions:

- **Control:** ordinary sampling.
- **Loaded:** the same model, but a keyed watermark algorithm slightly favors a pseudorandom subset of tokens at each generation step.

The app then exposes the mechanism without turning the screen into a research cockpit. It should let the user answer five questions in one continuous interaction:

1. **What tokens could the model have chosen here?**
2. **Which candidates were secretly favored?**
3. **How much did the watermark alter their probabilities?**
4. **How did weak token-level biases accumulate into strong statistical evidence?**
5. **How much editing destroys or preserves that evidence?**

The core “aha” moment is:

> Click a generated token, see its probability before and after the watermark, then edit the prose and watch the detector’s z-score fall in real time.

### Product promise

After one session, a technically curious user should understand that:

- the watermark is not hidden Unicode or metadata;
- no individual “AI word” proves anything;
- the signal lives in a distribution of choices across many positions;
- detection requires the matching scheme, tokenizer, parameters, and key;
- the p-value is evidence under a null model, not a posterior probability that “AI wrote this”;
- short, repetitive, low-entropy, translated, or heavily rewritten text can be difficult or impossible to detect.

### Explicit boundary

The app **must never imply that it can detect Claude’s private watermark** or determine whether arbitrary prose was written by Claude, ChatGPT, or any other closed model. It detects only watermarks generated with a supported local algorithm and a matching key/configuration.

---

## 2. Intended user and deployment

Primary user: one technically curious owner running the app privately on an always-on machine (Apple Silicon is first-class), reachable from their own devices on a private network.

Default deployment assumptions:

- one human user;
- one machine hosting the model and app;
- local model inference only;
- no external analytics;
- no cloud database;
- no public endpoint;
- backend bound to `127.0.0.1` (loopback); expose only through your own reverse proxy or private network boundary if needed;
- a single resident model and one active generation job at a time.

The application should also run on CUDA or CPU machines, but Apple Silicon is the first-class private deployment target.

---

## 3. Non-goals

Do **not** turn v1 into any of the following:

- a universal AI-text classifier;
- a production watermarking service for third parties;
- a public website;
- a benchmark suite for every watermark paper;
- a multi-user application;
- an identity or permissions system;
- a model-training project;
- a paraphrase-detector product;
- an Electron or native mobile app;
- a Gradio research demo with every parameter permanently visible;
- a Kubernetes, Redis, queue-worker, or microservice exercise;
- a vector database project;
- a live integration with proprietary model APIs.

A quiet, exact microscope beats a crowded “platform.”

---

## 4. The whole interface

The main Lab screen should contain almost the entire product. Secondary screens exist only for prior sessions and settings.

### Desktop layout

```text
┌──────────────┬──────────────────────────────────────────────────────────────┐
│ ◈            │ loaded-dicewriter                         model: ready       │
│ Lab          │ A microscope for statistical text watermarks.              │
│ Sessions     │                                                              │
│              │ ┌──────────────────────────────────────────────────────────┐ │
│              │ │ Explain why New York has so many bodegas.              │ │
│              │ └──────────────────────────────────────────────────────────┘ │
│              │  γ .25 · δ 2 · h 1 · key 4ac2…             Generate pair  │
│              │                                                              │
│              │ CONTROL                         LOADED                        │
│              │ ┌──────────────────────────┐   ┌──────────────────────────┐  │
│              │ │ New York has a large…   │   │ New York has a large…   │  │
│              │ │                         │   │ subtle token annotation │  │
│              │ └──────────────────────────┘   └──────────────────────────┘  │
│              │ 56 scored · z .31              36 scored · z 7.40           │
│              │ no evidence                     detected                     │
│              │                                                              │
│              │ EVIDENCE     0 ─────── 4.0 threshold ───────────── 7.40      │
│              │                                                              │
│              │ TOKEN 27 · “large”                                            │
│              │ before watermark       after watermark                       │
│              │ large        18%        large         31%  favored            │
│              │ substantial  14%        substantial    9%                     │
│              │ significant  11%        significant   19%  favored            │
│              │                                                              │
│              │ EDIT THE LOADED OUTPUT                                        │
│              │ ┌──────────────────────────────────────────────────────────┐ │
│              │ │ editable text                                            │ │
│              │ └──────────────────────────────────────────────────────────┘ │
│              │ 5 tokens changed · z 4.66 · still detected   Automate edits │
│              │                                                              │
│ Settings     │                                                              │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

### Sidebar

The sidebar is navigation, not a control console.

Visible items:

- logo/die mark;
- **Lab**;
- **Sessions**;
- bottom-aligned **Settings**;
- a tiny model-status dot.

No sliders, charts, keys, attack controls, or model parameters live permanently in the sidebar. The earlier noisy-dashboard failure mode comes from making every possible control visible at once.

Desktop width:

- 152–168 px expanded;
- optional 56 px collapsed mode;
- main content centered with a maximum width around 1120–1200 px.

### Mobile layout

On narrow screens:

- collapse the sidebar into a compact top bar or three-item bottom navigation;
- display **Control / Loaded** with a segmented switch rather than simultaneous columns;
- open the token inspector as an inline section or bottom sheet;
- keep the edit lab full-width;
- preserve all numerical labels, not just charts.

The phone experience is for supervision and experimentation, not merely read-only viewing.

---

## 5. Visual and interaction principles

### 5.1 Progressive disclosure

The default screen exposes only:

- prompt;
- compact watermark-profile summary;
- generate/stop;
- two outputs;
- one evidence indicator;
- token inspector after selection;
- edit lab after generation.

Everything else belongs in disclosures or settings:

- gamma;
- delta;
- context width;
- threshold;
- generation seed;
- sampling mode;
- key rotation;
- repeated-ngram policy;
- model revision;
- attack history;
- raw diagnostics.

### 5.2 Color is annotation, not wallpaper

Use quiet neutral surfaces. Green and red appear only as token annotations and status accents.

Do not render paragraphs as fully saturated blocks. Token states should use:

- favored token: faint green tint plus solid underline;
- non-favored token: faint warm tint plus dotted underline;
- excluded/unscored token: neutral gray underline or no annotation;
- selected token: clear focus ring independent of class.

Because red/green cannot be the only distinction, expose accessible labels such as `favored`, `not favored`, and `excluded` to screen readers and in tooltips.

### 5.3 Numerical honesty

Use these words:

- `z-score`;
- `p under null` or `p-value`;
- `detected at threshold z ≥ 4.0`;
- `insufficient scored tokens`;
- `no evidence under this key/configuration`.

Do not say:

- `99.9999% confidence it was AI-generated`;
- `proof of AI authorship`;
- `Claude detected`;
- `human probability`;
- `AI likelihood`.

### 5.4 One causal story, vertically

The screen reads from top to bottom:

1. prompt;
2. ordinary versus loaded output;
3. evidence accumulation;
4. one-token counterfactual;
5. editing and robustness.

Do not split these into unrelated dashboard panels.

### 5.5 Motion

Allow only purposeful motion:

- tokens appearing during generation;
- the evidence marker moving as tokens arrive;
- a short transition when an inspector opens.

Respect `prefers-reduced-motion`. Do not pulse, glow, continuously animate charts, or announce every token to assistive technology.

---

## 6. Primary user flow

### 6.1 Empty state

The Lab opens with:

- model readiness indicator;
- prompt box;
- one sentence explaining the experiment;
- three optional example prompts;
- compact profile pill, for example `Teaching KGW · γ .25 · δ 2 · h 1 · key 4ac2…`;
- `Generate pair` button.

Example prompts should encourage enough output entropy and length:

- “Explain why cities develop many small neighborhood stores.”
- “Describe three competing explanations for why people join recurring social groups.”
- “Write a short argument for and against open-source software.”

Avoid prompts with one canonical answer or a very short completion.

### 6.2 Generation

After `Generate pair`:

- replace the action with `Stop`;
- stream both branches;
- update each branch’s token count and score;
- update the single evidence strip;
- disable profile/model changes until the job ends;
- preserve page responsiveness.

The loaded branch should not scream “green” from the first token. Use subtle annotations, with a `Reveal token classes` toggle enabled by default only after at least a few scored tokens exist. The user can turn annotation on during generation.

### 6.3 Completion

After completion:

- show compact result lines under both branches;
- expose token clicking;
- automatically select the first loaded token whose before/after probability shift is pedagogically interesting;
- populate the edit lab with the loaded output;
- retain the evidence trace for replay.

### 6.4 Token inspection

Clicking a token opens a single full-width inspector below the outputs.

Show:

- token text and token ID;
- output position and scored position;
- preceding context used by the PRF;
- favored/not favored/excluded state;
- raw/base probability;
- probability after watermark bias;
- final sampling probability after temperature/top-p filters;
- entropy of the base distribution;
- selected token’s logit change;
- top 5–8 candidates before and after watermarking.

The inspector must make clear that “before” and “after” refer to the **same loaded-branch context**. It is a true local counterfactual. The separate control completion is not treated as a word-for-word counterfactual after the two branches diverge.

### 6.5 Editing

The loaded output appears in an editable text area.

On edit:

- debounce for roughly 200–300 ms;
- tokenize the entire edited text with the matching tokenizer;
- rescore under the original key and profile;
- update z-score, p-value, scored-token count, and threshold status;
- show token-edit distance from the original;
- ignore stale responses if the user keeps typing;
- make `Reset` immediate.

The dominant feedback is one line:

```text
5 tokens changed · z 4.66 · detected at z ≥ 4.0
```

A compact horizontal evidence bar can accompany it. Do not add a second dashboard.

### 6.6 Automated edits

`Automate edits` opens a small drawer or popover containing:

- delete words;
- insert neutral words;
- substitute words;
- normalize punctuation/case;
- local-model paraphrase, after the simpler attacks work.

Each attack has an intensity and seed. Applying it creates a new edit revision and adds one row to a collapsible history:

```text
Original       0% changed   z 7.40   detected
Substitute    10% changed   z 4.23   detected
Substitute    20% changed   z 2.11   no evidence
```

The history is hidden until an attack has been run.

---

## 7. Watermarking model

### 7.1 Canonical v1 algorithm

Implement the Kirchenbauer/Geiping/Wen et al. green-list family, commonly called KGW:

1. At generation position `t`, derive pseudorandomness from a secret key and a context of prior token IDs.
2. Use it to define a green/favored subset `G_t` containing fraction `γ` of the vocabulary.
3. Add logit bias `δ` to tokens in `G_t`.
4. Sample normally from the modified distribution.
5. During detection, recreate `G_t` and count whether each observed token belongs to it.

For `T` eligible scored tokens and `K` green tokens:

```text
expected green count = γT
z = (K - γT) / sqrt(Tγ(1-γ))
```

Use a one-sided standard-normal survival function for the displayed approximate p-value so the UI remains comparable to the paper and reference implementation.

### 7.2 Profiles

Ship named profiles instead of opening every parameter by default.

#### Teaching KGW — default for the first usable release

- scheme: simple context-seeded green list;
- `gamma = 0.25`;
- `delta = 2.0`;
- `context_width = 1`;
- `ignore_repeated_ngrams = true`;
- `z_threshold = 4.0`.

Reason: it is easy to inspect, fast, and faithful to the central intuition.

#### Robust KGW — later card

- scheme: reference-compatible minhash or self-hash profile;
- `gamma = 0.25`;
- `delta = 2.0`;
- moderate context width, default `h = 4`;
- repeated n-grams ignored;
- threshold configurable.

Reason: it reflects the authors’ later recommendations, but it is a worse starting point for a transparent implementation because self-hashing and broader contexts complicate inspection.

#### Custom — advanced disclosure

Expose bounded controls:

- gamma: 0.10–0.75;
- delta: 0.0–5.0;
- context width: 1–8;
- threshold: 2.0–8.0;
- repeated-ngram policy;
- PRF/seeding scheme.

Changing a profile invalidates the current detection context and must be explicit.

### 7.3 Portable detection versus generation-aware scoring

The prompt may affect the green list for the earliest generated tokens, but an external detector may possess only the generated text.

Therefore use **portable detection** as the primary score:

- tokenize only the generated completion;
- skip the first `h` completion tokens if their required context is unavailable;
- score later positions from completion-internal context;
- label skipped prefix tokens as `context unavailable`.

The engine may separately compute generation-aware diagnostics using prompt context, but those belong behind an advanced disclosure and must not replace the portable score shown in the main interface.

### 7.4 Repeated n-grams

Repeated local contexts violate the detector’s simple independence assumption. By default:

- define the scored unit as `(context tokens, observed token)`;
- score only the first occurrence of an identical unit;
- mark later occurrences `excluded: repeated n-gram`;
- report both total output tokens and eligible scored tokens.

### 7.5 Too-short text

Do not force a binary verdict on tiny samples.

Suggested UI logic:

- fewer than 20 eligible tokens: `insufficient scored tokens`;
- 20 or more: show z and p;
- threshold crossing remains visible, but include token count beside it.

This is a UX guardrail, not a theorem. Keep the minimum configurable in Settings.

### 7.6 Key behavior

The same scheme/configuration with a different key should produce approximately null behavior.

The app should support a deliberate wrong-key experiment:

- score loaded text with the generating key;
- score it with a newly generated comparison key;
- show the collapse from strong evidence to chance-level evidence.

This belongs in a compact “Key experiment” disclosure, not on the default screen.

---

## 8. Generation and sampling design

### 8.1 Local model requirement

The watermark must operate before token sampling, so v1 requires a local model backend that exposes logits. Closed text APIs are not suitable for the generation half of this app.

First backend:

- Hugging Face Transformers;
- PyTorch;
- Apple MPS, CUDA, and CPU device selection;
- decoder-only causal language models first;
- model and tokenizer pinned by ID plus revision;
- `trust_remote_code = false` by default.

### 8.2 Model profile

Store model configuration in `config/models.toml`:

```toml
[[models]]
id = "local-instruct-small"
hf_id = "ORG/MODEL"
revision = "PINNED_REVISION"
backend = "transformers"
dtype = "auto"
chat_template = true
max_context_tokens = 4096
recommended_max_new_tokens = 160
```

Do not hardwire the product to one fashionable model name. Provide:

- a tiny test model for CI and smoke tests;
- one documented 1–3B instruct-model profile for actual use;
- user-editable model registry.

### 8.3 Sampling pipeline

For the loaded branch at each position:

```text
model logits
→ generation penalties shared by both branches
→ snapshot “before watermark” distribution
→ add δ to favored token logits
→ snapshot “after watermark” distribution
→ temperature/top-k/top-p warping
→ sample token
→ update detector trace
→ emit event
```

For the control branch, skip the watermark-bias step but classify the sampled output under the same detector key so the user sees chance green hits.

Keep the initial generation controls deliberately small:

- maximum new tokens;
- temperature;
- top-p;
- seed.

Hide top-k, repetition penalty, stop sequences, and chat-template details in Advanced Settings.

### 8.4 Paired sampling

Support two modes:

#### Independent — implementation baseline

Each branch receives a deterministic branch-specific RNG derived from the session seed.

#### Shared-randomness — educational enhancement

Use a shared Gumbel-noise vector or another coupling that preserves each branch’s marginal categorical distribution while making branch differences easier to attribute to probability changes.

Label this `paired randomness`. It is a visualization aid, not part of the watermark itself.

Do not block the first end-to-end release on shared-randomness sampling. Add it only after independent generation is correct and tested.

### 8.5 Inspectable generation loop

Do not rely solely on a black-box `model.generate()` call for the final engine. The app needs exact per-token traces.

Implement an explicit autoregressive loop using:

- `torch.inference_mode()`;
- model KV cache;
- one resident model;
- per-step logits;
- a watermark processor function;
- a sampling function;
- event emission after each sampled token.

The official watermark repository can remain the correctness oracle and compatibility source, but the app’s main generation path must expose enough internal state for inspection.

---

## 9. Technical architecture

### 9.1 Stack

**Frontend**

- React;
- TypeScript with strict mode;
- Vite;
- Tailwind or plain CSS variables for layout, but no stock dashboard theme;
- Radix primitives only where accessibility behavior is valuable;
- native SVG for the evidence line/strip;
- no general charting library in v1;
- Playwright for end-to-end tests.

**Backend**

- Python 3.11+;
- FastAPI;
- Pydantic models;
- WebSockets for token streams;
- PyTorch + Transformers;
- SciPy for normal survival function and optional exact diagnostics;
- SQLite for local session storage;
- `uv` for environment and lockfile;
- pytest, Ruff, and mypy/pyright.

**Deployment**

- frontend compiled into static assets served by the FastAPI process;
- one backend process and one model instance;
- optional process-manager unit on the host OS;
- private HTTPS via the operator’s reverse proxy or network boundary if remote access is needed.

Avoid Docker for the primary Apple Silicon deployment because it complicates direct accelerator use and adds little value to a single-user local app. A container recipe can be added later for CPU/CUDA hosts.

### 9.2 Repository structure

```text
loaded-dicewriter/
├── README.md
├── Makefile
├── pyproject.toml
├── uv.lock
├── package.json
├── pnpm-lock.yaml
├── config/
│   ├── app.example.toml
│   └── models.toml
├── data/
│   └── .gitkeep
├── docs/
│   ├── algorithm-notes.md
│   ├── deployment-macos.md
│   └── screenshots/
├── server/
│   ├── loaded_dicewriter/
│   │   ├── app.py
│   │   ├── settings.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── generations.py
│   │   │   ├── detection.py
│   │   │   ├── sessions.py
│   │   │   └── settings.py
│   │   ├── core/
│   │   │   ├── types.py
│   │   │   ├── prf.py
│   │   │   ├── stats.py
│   │   │   ├── repeated_ngrams.py
│   │   │   └── profiles.py
│   │   ├── watermark/
│   │   │   ├── base.py
│   │   │   ├── kgw_inspectable.py
│   │   │   └── kgw_reference.py
│   │   ├── inference/
│   │   │   ├── base.py
│   │   │   ├── model_registry.py
│   │   │   └── transformers_backend.py
│   │   ├── generation/
│   │   │   ├── engine.py
│   │   │   ├── sampler.py
│   │   │   ├── trace.py
│   │   │   └── events.py
│   │   ├── attacks/
│   │   │   ├── base.py
│   │   │   ├── delete.py
│   │   │   ├── insert.py
│   │   │   ├── substitute.py
│   │   │   └── paraphrase.py
│   │   ├── persistence/
│   │   │   ├── db.py
│   │   │   ├── migrations/
│   │   │   └── repositories.py
│   │   └── security/
│   │       ├── keys.py
│   │       └── origin.py
│   └── tests/
├── web/
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── app/
│   │   ├── routes/
│   │   │   ├── Lab.tsx
│   │   │   ├── Sessions.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   │   ├── AppShell.tsx
│   │   │   ├── PromptComposer.tsx
│   │   │   ├── OutputPair.tsx
│   │   │   ├── TokenText.tsx
│   │   │   ├── EvidenceStrip.tsx
│   │   │   ├── TokenInspector.tsx
│   │   │   ├── EditLab.tsx
│   │   │   └── ProfileDrawer.tsx
│   │   ├── state/
│   │   ├── api/
│   │   ├── styles/
│   │   └── types/
│   └── tests/
└── scripts/
    ├── dev.sh
    ├── build.sh
    └── smoke-test.sh
```

### 9.3 Backend interfaces

#### Watermark algorithm protocol

```python
class WatermarkAlgorithm(Protocol):
    profile_id: str

    def favored_mask(
        self,
        *,
        context_ids: Sequence[int],
        vocab_size: int,
    ) -> Tensor: ...

    def bias_logits(
        self,
        *,
        context_ids: Sequence[int],
        logits: Tensor,
    ) -> BiasResult: ...

    def score_tokens(
        self,
        *,
        token_ids: Sequence[int],
        portable: bool = True,
    ) -> DetectionTrace: ...
```

#### Inference backend protocol

```python
class InferenceBackend(Protocol):
    tokenizer: TokenizerLike
    model_info: ModelInfo

    async def load(self) -> None: ...
    async def unload(self) -> None: ...
    def encode_prompt(self, prompt: PromptSpec) -> EncodedPrompt: ...
    def next_logits(self, state: DecodeState) -> NextTokenLogits: ...
```

Keep the interface narrow. Do not create a generic distributed inference abstraction.

### 9.4 Streaming event protocol

Use versioned JSON messages.

```json
{
  "v": 1,
  "type": "token",
  "generation_id": "...",
  "seq": 27,
  "branch": "loaded",
  "position": 26,
  "token_id": 3186,
  "text": " large",
  "favored": true,
  "eligible": true,
  "z_score": 4.81,
  "p_value": 0.00000075,
  "green_count": 18,
  "scored_count": 27,
  "latency_ms": 43
}
```

Other event types:

- `generation_accepted`;
- `model_loading`;
- `branch_started`;
- `token`;
- `branch_finished`;
- `generation_finished`;
- `generation_stopped`;
- `warning`;
- `error`.

Large inspector data should not be included in every token event. Store only a compact token event during streaming. Fetch the full candidate trace when the user selects a token, or retain top-k traces server-side and return them through a dedicated endpoint.

### 9.5 API surface

```text
GET    /api/healthz
GET    /api/readyz
GET    /api/config
GET    /api/models
POST   /api/generations
GET    /api/generations/{id}
WS     /api/generations/{id}/stream?after_seq=0
POST   /api/detect
GET    /api/generations/{id}/tokens/{branch}/{position}
POST   /api/attacks/preview
POST   /api/attacks/apply
GET    /api/sessions
GET    /api/sessions/{id}
DELETE /api/sessions/{id}
POST   /api/keys/rotate
```

The generation stream should support replay from `after_seq` so a phone or laptop can reconnect without losing the run. A simple in-memory event buffer is enough initially; persist the final trace after completion.

### 9.6 Concurrency

Default policy:

- one model loaded;
- one active generation job;
- detection/edit scoring may run concurrently on CPU if it does not interfere with generation;
- a second generation request receives a clear `busy` response rather than silently loading a second model;
- model switching unloads the current model deliberately and reports progress.

Never run multiple Uvicorn workers with a resident model; that would duplicate model memory.

---

## 10. Data model

### 10.1 Session

```text
Session
- id
- created_at
- updated_at
- title / prompt excerpt
- prompt_text
- prompt_mode
- model_id
- model_revision
- tokenizer_id
- generation_config_json
- watermark_profile_json
- key_id
- persistence_mode
- status
```

### 10.2 Generation branch

```text
GenerationBranch
- id
- session_id
- branch: control | loaded
- output_text
- output_token_ids_json
- finish_reason
- generation_ms
- portable_detection_json
- generation_aware_detection_json nullable
```

### 10.3 Token trace

```text
TokenTrace
- branch_id
- position
- token_id
- token_text
- context_hash
- favored
- eligible
- exclusion_reason nullable
- base_logit
- biased_logit nullable
- base_probability
- biased_probability nullable
- final_sampling_probability
- entropy
- green_count_after
- scored_count_after
- z_score_after
- p_value_after
- top_candidates_before_json
- top_candidates_after_json
- latency_ms
```

Do not persist full-vocabulary logits. Persist only the selected token metrics and top 5–8 candidates. This keeps sessions inspectable without turning SQLite into a tensor store.

### 10.4 Edit revision

```text
EditRevision
- id
- session_id
- parent_revision_id nullable
- created_at
- source: manual | attack
- attack_type nullable
- attack_params_json nullable
- text
- token_ids_json
- token_edit_distance
- detection_json
```

### 10.5 Key record

```text
KeyRecord
- id
- fingerprint
- created_at
- retired_at nullable
- algorithm_family
```

Store the secret outside SQLite. On macOS, use Keychain through a small key-storage adapter. In development and CI, permit an environment-variable key backend.

---

## 11. Key and privacy design

### 11.1 Key generation

On first run:

- generate a 256-bit random master key;
- store it in macOS Keychain;
- derive an algorithm-specific integer/byte seed with HMAC or HKDF;
- display only an 8–12 character fingerprint;
- associate every generation session with a key ID.

For exact compatibility tests with the reference implementation, permit a fixed integer base key in test configuration. Never use the reference repository’s demonstration key as the user’s default production key.

### 11.2 Rotation

Rotating a key:

- creates a new active key;
- preserves old keys so old sessions remain inspectable;
- never silently rescores old sessions with the new key;
- shows the old and new fingerprints in a confirmation dialog.

### 11.3 Runtime privacy

Default rules:

- no prompt/output logging;
- no analytics SDK;
- no error-reporting SaaS;
- model inference and detection remain local;
- redact prompt/output from structured logs;
- export contains configuration and traces but never the secret key;
- bind to loopback only;
- same-origin frontend/API;
- strict CORS and origin checks;
- disable or protect interactive API docs in the packaged deployment.

### 11.4 Persistence mode

Allow two modes:

- **Save session** — default for a personal lab;
- **Ephemeral** — delete text and traces after the browser session or generation ends.

The current mode should be visible near the session overflow menu, not as a permanent large control.

---

## 12. Statistics and detector behavior

### 12.1 Main outputs

Return:

```text
num_tokens_total
num_tokens_scored
num_green
expected_green
green_fraction
z_score
p_value
detected
threshold
excluded_prefix_count
excluded_repeated_count
```

### 12.2 Stable numerical behavior

- handle zero scored tokens without division by zero;
- use float64 for detector aggregation;
- cap display precision without truncating stored values;
- display very small p-values in scientific notation;
- test normal survival function values against SciPy;
- keep threshold comparison exact and centralized.

### 12.3 Per-token trace

A detection trace should distinguish:

- `favored and scored`;
- `not favored and scored`;
- `excluded: missing context`;
- `excluded: repeated n-gram`;
- `excluded: special token`.

### 12.4 Null checks

The test suite should empirically verify that:

- control text scored with a random key centers near the null expectation over many runs;
- loaded text shows elevated green fraction under the correct key;
- loaded text scored with the wrong key returns toward the null;
- the observed favored-set fraction across many random contexts approximates gamma.

Do not assert that every single short control generation has a z-score near zero. Statistical behavior must be tested over batches.

---

## 13. Token inspector specification

This is the distinctive product feature. Treat it as a first-class causal-debugging tool, not a decorative table.

### 13.1 Header

```text
Token 27 · “large”
Favored at this position · context: “has a” · entropy 3.82 bits
```

### 13.2 Candidate table

Columns:

```text
candidate | class | base probability | after bias | final sampling probability | change
```

Rules:

- show selected token first, then highest-probability candidates;
- include candidates that entered or fell out of the top list due to bias;
- use token-rendering helpers so whitespace is visible, e.g. `␠large` in diagnostics;
- tooltip explains that token probabilities depend on the tokenizer and current context;
- selected-token row gets a focus treatment, not a brighter class color.

### 13.3 Explanation copy

Below the table, generate one concise sentence from deterministic rules, not an LLM:

```text
“large” was in the favored set, so the algorithm added δ = 2.0 to its logit, increasing its probability from 18.1% to 31.4% before final sampling filters.
```

For a non-favored selected token:

```text
“substantial” was not favored. Its logit was unchanged, but its probability fell because favored alternatives received extra mass.
```

### 13.4 Context and key experiment

An advanced disclosure may show:

- context token IDs;
- context hash;
- key fingerprint;
- favored-set size;
- same position rescored under a comparison key.

Never send or display the full secret key.

---

## 14. Evidence visualization

Use one restrained visualization.

### 14.1 Evidence strip

Default:

```text
CONTROL  z 0.31       threshold 4.0                         LOADED  z 7.40
──────────●──────────────────────│──────────────────────────────────●────
```

This can be rendered as a small SVG with:

- zero/reference mark;
- threshold mark;
- control marker;
- loaded marker;
- accessible text equivalent.

### 14.2 Evidence over time

A `Show accumulation` disclosure reveals a small line chart of z-score by scored token position for the loaded branch, optionally with the control line.

Do not display it by default. The default strip is enough for the main causal story; the line chart is for the user who asks “when did the detector become confident?”

### 14.3 Replay

After generation, allow a subtle playhead scrubber to replay evidence accumulation. This is a later enhancement, not an initial dependency.

---

## 15. Automated attacks

Implement attacks as deterministic text transformations with explicit seeds. They are demonstrations, not adversarial claims.

### 15.1 Word deletion

- tokenize into words while preserving punctuation;
- remove a seeded fraction of eligible words;
- avoid deleting all words in a sentence;
- report actual changed-token percentage after model tokenization.

### 15.2 Insertion

- insert from a small local neutral-word/phrase set;
- place at seeded grammatical boundaries where possible;
- label quality limitations clearly.

### 15.3 Substitution

Start with a small curated local synonym map rather than a network service. Preserve capitalization and basic morphology where possible.

Later, optionally integrate a local lexical resource. Do not silently call a remote LLM.

### 15.4 Punctuation/case normalization

Useful as a negative control because many tokenizers can still change tokenization when punctuation or capitalization changes.

### 15.5 Local paraphrase

Add only after the core app works:

- use the already loaded local model;
- clearly mark it as a separate generation;
- keep original, paraphrase prompt, model, and seed;
- do not present one paraphrase run as a general robustness result.

### 15.6 Attack comparison

The app should compare:

- actual token edit distance;
- percentage of original model tokens retained;
- scored-token count;
- z-score before/after;
- threshold outcome.

Avoid a simplistic “10% words changed” label when retokenization produced a materially different token-level change.

---

## 16. Sessions screen

The Sessions screen is intentionally boring.

Each row shows:

- timestamp;
- prompt excerpt;
- model;
- watermark profile;
- loaded z-score;
- strongest edit revision z-score or number of revisions.

Actions:

- open;
- duplicate prompt/config;
- export JSON;
- delete.

No global analytics dashboard is needed in v1. A later research view may compare runs, but the main product is individual causal inspection.

---

## 17. Settings screen

Sections:

### Model

- active model;
- load/unload;
- device;
- revision;
- memory status;
- model registry path.

### Watermark defaults

- active profile;
- detection threshold;
- minimum scored tokens;
- repeated-ngram policy.

### Key

- fingerprint;
- creation date;
- rotate;
- wrong-key experiment defaults.

### Privacy

- default persistence mode;
- export directory;
- log level;
- confirm no telemetry.

### Deployment diagnostics

- app version;
- database path;
- health status;
- local deployment notes link in docs;
- copy sanitized diagnostics.

---

## 18. Failure states

### Model missing

```text
The configured model is not available locally.
Download it during setup or select another local model.
```

Do not automatically download multi-gigabyte weights without confirmation.

### Unsupported tokenizer/model

```text
This model does not expose a compatible causal-LM vocabulary and logits interface.
```

### Accelerator out of memory

- stop generation cleanly;
- release temporary tensors;
- retain the prompt and configuration;
- offer a smaller model or shorter output;
- do not repeatedly retry automatically.

### Short output

```text
Only 12 tokens were eligible for scoring. That is too little evidence for a useful verdict.
```

### Repetitive output

```text
18 repeated n-grams were excluded because repeated contexts would overstate the detector’s evidence.
```

### Stream disconnect

- reconnect with last sequence number;
- replay buffered events;
- show `reconnecting…` without discarding output;
- mark the job unknown only after a bounded timeout.

### Key unavailable

```text
The key used for this session is no longer available, so the original detection result cannot be reproduced.
```

Never silently use the current key.

---

## 19. Testing strategy

### 19.1 Unit tests

Required:

- deterministic PRF output for fixed key/context;
- favored-mask size equals the configured gamma fraction within rounding rules;
- only favored logits receive delta;
- non-favored logits remain bitwise/effectively unchanged before normalization;
- z-score formula;
- p-value values;
- repeated-ngram exclusion;
- portable prefix exclusion;
- exact threshold boundary;
- key fingerprint stability;
- attack determinism by seed.

### 19.2 Property tests

Use Hypothesis or equivalent:

- same key + same context produces same partition;
- different keys produce different partitions with high probability;
- aggregate favored frequency approximates gamma;
- increasing delta does not decrease the total favored probability mass before truncation;
- wrong-key scoring approaches null behavior over many generated sequences;
- serialization/deserialization preserves configuration and traces.

### 19.3 Golden/reference tests

Use the official KGW implementation as a correctness oracle for at least one supported seeding profile.

Pin:

- tokenizer;
- vocabulary;
- context tokens;
- base key;
- gamma/delta;
- device behavior where relevant.

Verify:

- favored sets;
- selected-token classifications;
- detector counts and z-score;
- repeated-ngram handling.

Keep the reference adapter isolated so upstream implementation changes cannot silently alter the app.

### 19.4 Integration tests

- model loads once;
- control generation completes;
- loaded generation completes;
- stop cancels cleanly;
- event sequence is monotonic;
- reconnect replays missing events;
- token inspector returns the correct position;
- edited text rescoring ignores stale requests;
- session persists and reloads.

### 19.5 Frontend tests

- keyboard-only prompt to generation flow;
- token selection and inspector;
- control/loaded switch on mobile;
- screen-reader labels for token classes;
- evidence strip text equivalent;
- reduced-motion behavior;
- error messages;
- no red/green-only semantics.

### 19.6 Deterministic fake engine

Create a fake generation backend that emits a known token trace. Use it for frontend development, CI, and screenshots so tests do not require model weights.

The fake engine should demonstrate:

- a control sequence near null;
- a loaded sequence crossing threshold;
- one strongly shifted token;
- an edit sequence that falls below threshold.

---

## 20. Performance budgets

Model speed is model/hardware-dependent, so distinguish app overhead from inference latency.

App-level goals:

- first shell paint: under 1 second on local network after assets are cached;
- token event rendering overhead: under 16 ms per event on desktop;
- detection of 500 tokens: target under 100 ms on the host CPU;
- edit-lab response perceived within 300 ms including debounce;
- token inspector response: under 100 ms when trace is already stored;
- session open: under 200 ms for ordinary runs;
- no full-vocabulary probability arrays sent to the browser;
- model loaded exactly once;
- bounded in-memory event buffer per active run.

Instrumentation:

- model load duration;
- time to first token;
- inter-token latency;
- watermark processing overhead;
- detector latency;
- WebSocket reconnect count;
- peak process memory.

Logs must not include prompt or generated text by default.

---

## 21. Accessibility

Target WCAG 2.2 AA behavior.

Required:

- visible focus states;
- keyboard-selectable tokens;
- `aria-label` describing token text and class;
- favored/non-favored distinction beyond color;
- chart text alternatives;
- logical heading order;
- no token-by-token live-region spam;
- completion and error summaries announced;
- minimum 44px touch targets for mobile controls where practical;
- zoom to 200% without horizontal page scrolling except inside deliberate code/data regions;
- system light/dark theme support;
- reduced motion.

Token text can be rendered as focusable spans only when inspection is enabled; otherwise avoid producing hundreds of unnecessary tab stops. Provide arrow-key navigation within the token region.

---

## 22. Deployment on a private host

### 22.1 Native service

Build frontend assets and serve them from FastAPI.

Run one command locally:

```text
loaded-dicewriter serve --host 127.0.0.1 --port 8765
```

Under a process manager of your choice (systemd user unit, supervisord, or equivalent):

- start after login / boot as appropriate;
- restart on crash with backoff;
- write sanitized logs to a local logs directory;
- use explicit working/data directories;
- inherit no secret key through command-line arguments.

### 22.2 Private network access

Keep the backend bound to loopback by default. If you need access from other devices, terminate TLS and proxy at your own reverse proxy or private network boundary — do not expose the process as a public endpoint.

### 22.3 Backups

Back up:

- SQLite database;
- configuration;
- model registry;
- app version metadata.

Do not back up Keychain secrets into plain files. Provide a diagnostic warning that session reproducibility depends on preserving the key.

### 22.4 Updates

A release update should:

- stop the launch agent;
- back up the database;
- apply forward-only migrations;
- rebuild frontend;
- restart;
- run `/readyz` smoke test;
- preserve the prior version for quick rollback.

---

# 23. Build-order cards

The cards below are sequential. A card is complete only when its user-visible result and acceptance criteria are satisfied. Do not claim completion because files or placeholder components exist.

---

## LDW-000 — Repository foundation and guardrails

**Goal**  
Create a reproducible monorepo with a fake backend and one-command development startup.

**User-visible result**  
Opening the local URL shows a plain `loaded-dicewriter` page with backend/model status and no broken controls.

**Implement**

- Python project with `uv` lockfile;
- React/TypeScript/Vite frontend;
- shared version number;
- `make dev`, `make test`, `make lint`, `make build`;
- FastAPI health and readiness endpoints;
- static frontend serving in production mode;
- deterministic fake generation engine;
- environment/config loader;
- no telemetry and loopback binding by default;
- CI that runs without downloading a real model.

**Acceptance criteria**

- fresh clone plus documented prerequisites starts with one command;
- `/api/healthz` returns process health;
- `/api/readyz` distinguishes app readiness from model readiness;
- frontend can call backend through same origin;
- fake mode works on a machine without GPU/model files;
- lint, type-check, unit tests, and production build pass.

**Do not build yet**

- real watermarking;
- SQLite;
- WebSocket generation;
- attack lab.

---

## LDW-001 — Quiet application shell

**Goal**  
Implement the final information architecture before adding algorithmic complexity.

**User-visible result**  
The app looks like the intended quiet product: narrow sidebar, prompt area, empty output pair, evidence placeholder, hidden inspector, hidden edit lab.

**Implement**

- desktop sidebar and mobile navigation;
- Lab, Sessions, Settings routes;
- prompt composer;
- compact profile pill;
- empty output cards;
- theme tokens and system light/dark mode;
- responsive stacked/segmented mobile behavior;
- skeleton/error/loading states;
- accessibility baseline.

**Acceptance criteria**

- no more than six primary controls are visible in the empty Lab state;
- sidebar contains navigation only;
- 320px-wide mobile viewport remains usable;
- keyboard focus order is logical;
- contrast and non-color token-state design are documented;
- visual-regression screenshot establishes the quiet baseline.

**Demo checkpoint**  
This should already look like a real private app, even though the engine is fake.

---

## LDW-002 — Toy loaded-dice engine

**Goal**  
Make the mechanism visible without involving a language model.

**User-visible result**  
A `Toy mode` example generates words from a tiny fixed vocabulary, with ordinary and biased probabilities shown in the inspector.

**Implement**

- deterministic keyed PRF;
- favored subset selection from a toy vocabulary;
- gamma and delta;
- logit/probability bias;
- seeded categorical sampling;
- per-token trace;
- simple fake sentences or token sequences;
- token selection and before/after candidate table.

**Acceptance criteria**

- same key/context yields identical favored set;
- changing key changes favored set;
- only favored logits receive delta;
- probabilities normalize correctly;
- selected token is traceable to its sampling distribution;
- the UI can explain one favored and one non-favored selected token.

**Why this card exists**  
It separates watermark correctness and UI legibility from model-inference bugs.

---

## LDW-003 — Statistical detector and evidence trace

**Goal**  
Implement scoring, p-values, exclusions, and evidence accumulation independently of model generation.

**User-visible result**  
Toy output shows green count, expected count, z-score, p-value, threshold status, and a live accumulation strip.

**Implement**

- detector result types;
- z-score formula;
- normal survival-function p-value;
- minimum-token UX state;
- portable-prefix exclusion;
- repeated-ngram exclusion;
- per-position score trace;
- evidence strip and optional accumulation disclosure;
- wrong-key toy comparison.

**Acceptance criteria**

- known numerical fixtures match expected z/p values;
- zero/short input returns a typed non-error result;
- repeated units are excluded once and labeled;
- wrong-key toy scoring approaches null across a batch test;
- UI never converts p-value into “AI confidence.”

---

## LDW-004 — Real local model loading and control generation

**Goal**  
Load a local Hugging Face causal model once and stream an ordinary completion.

**User-visible result**  
The user selects a configured local model, enters a prompt, and watches the Control branch generate.

**Implement**

- model registry from TOML;
- tokenizer/model loading;
- MPS/CUDA/CPU selection;
- pinned revision reporting;
- prompt encoding and chat-template handling;
- explicit autoregressive loop with KV cache;
- stop/cancel;
- model-load progress and errors;
- generation timing;
- tiny-model integration test profile.

**Acceptance criteria**

- model is loaded once per process;
- no gradients are allocated;
- control generation is deterministic for fixed config/seed;
- stop releases the job without corrupting future runs;
- prompt and completion token boundaries are correct;
- no prompt text appears in logs.

**Do not build yet**

- paired simultaneous generation;
- full watermark reference compatibility;
- persistence.

---

## LDW-005 — Inspectable KGW watermark generation

**Goal**  
Apply the green-list watermark to real model logits and produce a fully inspectable loaded completion.

**User-visible result**  
The Loaded branch generates from the local model, crosses the detector threshold on sufficiently long/entropic text, and exposes token classes.

**Implement**

- `WatermarkAlgorithm` interface;
- inspectable KGW Teaching profile;
- favored-mask generation from context/key;
- delta application;
- loaded-branch token trace;
- portable detector on generated output;
- generation-aware diagnostics behind disclosure;
- selected-token probability snapshots;
- configuration fingerprint.

**Acceptance criteria**

- favored masks are deterministic;
- loaded generation has elevated favored-token frequency over a batch;
- correct-key detector shows materially stronger aggregate evidence than control/wrong-key;
- selected-token before/after probabilities are exact within tolerance;
- first portable-unscorable tokens are labeled rather than incorrectly scored;
- full-vocabulary tensors are not retained after top-k trace extraction.

---

## LDW-006 — Paired generation and resilient streaming

**Goal**  
Run control and loaded branches as one session and stream them reliably to multiple private devices.

**User-visible result**  
Both outputs appear live in the same Lab session. Reloading or briefly losing the connection resumes the run.

**Implement**

- generation job model;
- REST job creation;
- WebSocket event stream;
- monotonic sequence numbers;
- bounded event replay buffer;
- reconnect from `after_seq`;
- branch lifecycle events;
- one-job concurrency guard;
- branch-specific deterministic RNG;
- clear busy/stopped/failed states.

**Acceptance criteria**

- no duplicate or reordered tokens after reconnect;
- both branches preserve their own token contexts;
- browser reload can reconstruct active output from replay;
- second generation request receives a clear busy response;
- stopping from one device updates another connected device;
- stream errors do not lose the completed partial text.

**Demo checkpoint**  
This is the first complete “watch the loaded dice roll” version.

---

## LDW-007 — Final quiet compare view

**Goal**  
Replace fake/static states with the polished live comparison interface.

**User-visible result**  
The main screen now matches the target wireframe and remains calm during generation.

**Implement**

- live Control and Loaded cards;
- compact result lines;
- subtle token annotation;
- `Reveal token classes` toggle;
- evidence strip;
- completion summary;
- automatic pedagogically useful token selection;
- mobile Control/Loaded segmented view;
- reduced-motion behavior.

**Acceptance criteria**

- default generation view has no permanent parameter sidebar or attack dashboard;
- token colors remain subtle and accessible;
- evidence metrics remain readable while streaming;
- mobile user can switch branches without losing scroll position;
- completion gives a clear explanation without modal interruption;
- screenshot comparison confirms visual density remains within the quiet baseline.

---

## LDW-008 — Counterfactual token inspector

**Goal**  
Deliver the defining microscope interaction.

**User-visible result**  
Clicking any eligible loaded token reveals exactly how the watermark changed the local candidate distribution.

**Implement**

- token-detail endpoint;
- before/after/final probability table;
- top-candidate union logic;
- selected-token deterministic explanation;
- whitespace-aware token display;
- context display;
- entropy display;
- keyboard token navigation;
- advanced context/key fingerprint disclosure.

**Acceptance criteria**

- inspector values match server trace and recomputation;
- favored selected token shows +delta logit;
- non-favored token shows unchanged logit but possible probability reduction;
- table includes candidates displaced into/out of top-k;
- no secret key reaches browser or export;
- inspector is usable by keyboard and screen reader.

**Demo checkpoint**  
A user should now be able to explain the watermark mechanism after clicking one token.

---

## LDW-009 — Manual edit laboratory

**Goal**  
Let the user directly destroy or preserve the signal and receive immediate detector feedback.

**User-visible result**  
Editing the loaded output updates token counts, z-score, p-value, threshold state, and token edit distance live.

**Implement**

- editable loaded-text area;
- debounced `/api/detect` requests;
- request cancellation/versioning;
- original-versus-edited token diff;
- reset;
- edited token annotations in a read-only preview if needed;
- short/repetitive text warnings;
- edit revision in memory.

**Acceptance criteria**

- stale detector responses never overwrite newer text;
- 500-token detection meets latency target on host;
- reset restores exact original output and score;
- deleting enough text produces `insufficient scored tokens` rather than a misleading verdict;
- changing punctuation can visibly alter tokenization and the UI explains that fact;
- manual edits do not mutate the original generation record.

---

## LDW-010 — Automated attack drawer

**Goal**  
Add reproducible perturbation experiments without cluttering the main screen.

**User-visible result**  
The user opens `Automate edits`, applies a seeded attack, and sees a compact before/after history.

**Implement**

- attack interface;
- deletion;
- insertion;
- curated substitution;
- punctuation/case normalization;
- intensity and seed;
- actual model-token edit-distance calculation;
- attack history disclosure;
- one-click restore/branch from revision.

**Acceptance criteria**

- attacks are deterministic for seed/config;
- reported change percentage uses actual model tokens as well as human-readable words;
- no remote service is called;
- history remains hidden before first attack;
- each revision is independently rescored;
- app copy avoids claiming general robustness from one example.

**Demo checkpoint**  
The complete core causal arc is now present: generation, probability shift, detection, and degradation under editing.

---

## LDW-011 — SQLite sessions and history

**Goal**  
Make experiments durable without making persistence part of the visible main workflow.

**User-visible result**  
Completed sessions survive restart and can be reopened from a simple list.

**Implement**

- SQLite database;
- forward-only migrations;
- WAL mode;
- session/branch/token/edit tables;
- transaction boundaries;
- save versus ephemeral mode;
- Sessions list/open/delete/duplicate;
- JSON export without keys;
- database backup before migration.

**Acceptance criteria**

- restart preserves saved sessions;
- ephemeral sessions leave no text rows after cleanup;
- old session uses its original model/profile/key references;
- deleting a session removes dependent traces/revisions;
- export reproduces the displayed metrics;
- database corruption/migration failures produce actionable errors and preserve backup.

---

## LDW-012 — Reference compatibility and advanced profiles

**Goal**  
Validate the teaching implementation and add a more robust reference-aligned profile.

**User-visible result**  
Settings offers `Teaching KGW`, `Robust KGW`, and `Custom`, while the default Lab remains uncluttered.

**Implement**

- isolated adapter to the official extended KGW implementation;
- golden compatibility fixtures;
- minhash/self-hash profile where feasible;
- context-width control;
- repeated-ngram policy control;
- key/profile fingerprinting;
- wrong-key experiment;
- standalone `Inspect pasted text` mode as a secondary Lab mode.

**Acceptance criteria**

- at least one profile matches reference favored sets and detector outputs;
- profile changes are serialized and reproducible;
- wrong-key result is clearly distinguished from correct-key result;
- pasted-text inspection requires explicit tokenizer/profile/key selection;
- app still refuses to characterize arbitrary text as “Claude-generated.”

---

## LDW-013 — Local-model paraphrase attack and paired randomness

**Goal**  
Add the two valuable but nonessential experiments after the core is stable.

**User-visible result**  
The user can locally paraphrase a loaded passage and can compare independent versus paired-randomness generation.

**Implement**

- local paraphrase prompt/template;
- separate paraphrase generation record;
- shared-Gumbel or other validated coupling for paired sampling;
- configuration label explaining that pairing is not the watermark;
- tests that each branch’s marginal sampler remains correct;
- side-by-side outcome comparison.

**Acceptance criteria**

- paraphrase never calls a remote API;
- paraphrase generation is reproducible by model/seed/template;
- paired sampling does not change each branch’s intended marginal distribution in statistical tests;
- UI does not imply word-by-word causal equivalence after contexts diverge;
- feature can be disabled without affecting the core engine.

---

## LDW-014 — Private host deployment

**Goal**  
Turn the development app into dependable private software on an always-on host.

**User-visible result**  
The app starts automatically, survives reboot, and is reachable from the owner’s own devices over a private network boundary if configured.

**Implement**

- production asset build;
- optional process-manager install script for the host OS;
- loopback-only server;
- reverse-proxy / private-network access notes;
- log rotation;
- data/config directory conventions;
- model readiness after boot;
- backup and upgrade scripts;
- sanitized diagnostics bundle.

**Acceptance criteria**

- cold reboot leads to a healthy app without manual shell steps;
- service is not reachable from the public internet by default;
- only one app/model process is running;
- remote private-network clients can generate, stop, inspect, and edit when the operator has configured access;
- restart during an idle state preserves sessions;
- upgrade script backs up and smoke-tests before declaring success.

---

## LDW-015 — Release hardening

**Goal**  
Ship a dependable v1 rather than a permanently almost-finished demo.

**User-visible result**  
A polished private application with clear documentation and no known high-severity correctness or privacy defects.

**Implement**

- full test matrix;
- accessibility audit;
- performance profiling;
- model OOM recovery;
- stream reconnect soak test;
- database migration test;
- key-loss behavior;
- threat-model review;
- user guide;
- algorithm guide;
- limitations page;
- versioned release artifact.

**Release gates**

- no prompt/output in default logs;
- no full key in browser, database, logs, or exports;
- reference compatibility test passes;
- control/correct-key/wrong-key aggregate statistical tests pass;
- 100 repeated generate/stop cycles do not leak unbounded memory;
- mobile main flow passes;
- keyboard-only main flow passes;
- reconnect does not duplicate tokens;
- app uses the phrase `AI detector` only to explain what it is not.

---

## 24. Future extension seam

After v1, add algorithms only through an adapter contract. Candidates include SynthID-style scoring and algorithms available in MarkLLM, but do not import MarkLLM wholesale into the core app until there is a concrete experiment the UI can explain.

A new algorithm adapter must provide:

- generation-time transform or sampler;
- detection result;
- per-token or per-span visualization data;
- configuration schema;
- key requirements;
- portability assumptions;
- reference fixtures;
- plain-language explanation;
- attack compatibility.

Algorithms that cannot expose an intelligible local counterfactual may belong in a separate comparison mode rather than being forced into the KGW token-inspector UI.

---

## 25. Definition of v1 success

The first real release succeeds when the owner can open it from a phone or laptop and complete this sequence without reading documentation:

1. Enter a prompt.
2. Generate ordinary and loaded completions.
3. Watch the loaded score cross the threshold while the control remains near chance.
4. Click a token and see exactly how its probability changed.
5. Edit the loaded prose until the watermark is no longer detected.
6. Change the key and see the signal disappear.
7. Reopen the saved session later.

The final feeling should be:

> “Oh. The words are normal. The dice were loaded.”

Not:

> “I have opened a monitoring console for a nuclear reactor.”

---

## 26. Source anchors

These are implementation and conceptual anchors, not dependencies that must dictate the UI.

- Kirchenbauer et al., **A Watermark for Large Language Models**: https://arxiv.org/abs/2301.10226
- Official KGW implementation: https://github.com/jwkirchenbauer/lm-watermarking
- Kirchenbauer et al., **On the Reliability of Watermarks for Large Language Models**: https://arxiv.org/abs/2306.04634
- Hugging Face Transformers generation/logits processor documentation: https://huggingface.co/docs/transformers/internal/generation_utils
- FastAPI WebSocket documentation: https://fastapi.tiangolo.com/advanced/websockets/
- SQLite WAL documentation: https://www.sqlite.org/wal.html
- MarkLLM toolkit, useful for later adapters and attack comparisons: https://github.com/THU-BPM/MarkLLM
- SynthID Text reference implementation, useful for a later algorithm family: https://github.com/google-deepmind/synthid-text

### Licensing note

The official KGW and MarkLLM repositories use Apache-2.0 licensing at the time of this specification. If code is copied or vendored, retain the required license and attribution files. Prefer a small isolated reference adapter plus an independently testable inspectable engine rather than casually copying research-demo code throughout the product.
