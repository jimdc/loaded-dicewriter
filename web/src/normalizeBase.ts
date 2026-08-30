/**
 * Normalize APP_BASE_PATH for Vite `base` and shared docs/tests.
 * Root stays `/`; subpaths become `/loaded-dicewriter/` (leading + trailing slash).
 */
export function normalizeViteBase(raw: string | undefined): string {
  const value = (raw ?? "/").trim() || "/";
  if (value === "/") return "/";
  const withLeading = value.startsWith("/") ? value : `/${value}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}
