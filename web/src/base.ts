/**
 * Configurable application base path for reverse-proxy subpath hosting.
 *
 * Vite injects `import.meta.env.BASE_URL` from its `base` config (sourced from
 * `APP_BASE_PATH` at build time). Values are always absolute and end with `/`
 * (e.g. `/` or `/loaded-dicewriter/`).
 *
 * Strip-prefix reverse proxy: browser requests `/loaded-dicewriter/x` are
 * forwarded to the app as `/x`. Asset + API URLs still include the base so the
 * browser path matches the proxy slug; the server serves at web root.
 */

/** Vite base URL: `/` locally, `/loaded-dicewriter/` when built for a subpath proxy. */
export function appBaseUrl(): string {
  const raw = import.meta.env.BASE_URL || "/";
  if (raw === "/") return "/";
  return raw.endsWith("/") ? raw : `${raw}/`;
}

/**
 * React Router basename: leading slash, no trailing slash, or undefined at root.
 * Example: `/loaded-dicewriter` when `APP_BASE_PATH=/loaded-dicewriter/`.
 */
export function routerBasename(): string | undefined {
  const base = appBaseUrl();
  if (base === "/") return undefined;
  return base.replace(/\/+$/, "") || undefined;
}

/** Join an app-absolute path (`/api/...`) onto the configured base. */
export function withBase(path: string): string {
  const base = appBaseUrl();
  const normalized = path.startsWith("/") ? path.slice(1) : path;
  if (base === "/") {
    return `/${normalized}`;
  }
  return `${base}${normalized}`;
}
