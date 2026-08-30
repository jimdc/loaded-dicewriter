# Accessibility baseline (LDW-001)

Target: WCAG 2.2 AA behavior for the quiet application shell.

## Keyboard and focus

- All interactive controls are reachable by keyboard (`Tab` / `Shift+Tab`).
- Visible `:focus-visible` rings use `--focus` / `--focus-ring` tokens (not color-only).
- Empty Lab focus order is logical:
  1. Sidebar (or mobile top chrome) navigation
  2. Prompt textarea
  3. Example prompt chips
  4. Generate pair
  5. Mobile segmented control / bottom nav when present
- Token spans are **not** tab stops until inspection is enabled (later card). Arrow-key token navigation will land with the inspector.

## Non-color token-state design

Token classes must never rely on red/green alone. When annotations appear (later cards):

| State | Color cue | Non-color cue | Accessible name |
| --- | --- | --- | --- |
| Favored | faint green tint (`--token-favored-bg`) | **solid** underline (`--token-favored-underline`) | `favored` in `aria-label` + tooltip |
| Not favored | faint warm tint (`--token-nonfavored-bg`) | **dotted** underline | `not favored` |
| Excluded / unscored | none / neutral gray | thin gray underline or no underline | `excluded` |
| Selected | independent focus ring (`--token-selected-ring`) | focus ring regardless of class | included in accessible name |

Contrast notes (approximate, system light/dark):

- Body text `--text` on `--bg` exceeds 7:1 in both themes.
- Secondary text `--text-secondary` on `--bg` targets ≥ 4.5:1.
- Primary button uses inverse text on `--accent`; large-text / UI-component contrast ≥ 3:1.
- Status dots always pair with a text label (or `sr-only` text when compact on mobile).

## Structure and motion

- Landmark regions: primary sidebar / mobile nav, main content.
- Heading order: page `h1`, then section `h2` (Control / Loaded / Evidence / Settings sections).
- Inspector and edit lab are present in the DOM but `hidden` until relevant — no surprise live regions.
- No token-by-token live-region spam. Completion/error summaries use polite/alert live regions only.
- `prefers-reduced-motion` disables skeleton shimmer and non-essential transitions.
- System light/dark via `color-scheme` and `prefers-color-scheme` (CSS tokens in `web/src/styles/tokens.css`).
- Mobile controls target ≥ 44px height where practical (`--touch-min`).

## Visual baseline

Quiet empty-Lab screenshots (Playwright):

- `docs/screenshots/lab-empty-desktop.png`
- `docs/screenshots/lab-empty-mobile-320.png`

Regenerate:

```bash
make build
cd web && pnpm exec vite preview --host 127.0.0.1 --port 4173 &
cd web && pnpm exec playwright install chromium
cd web && pnpm screenshot
```
