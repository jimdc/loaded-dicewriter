/**
 * User-facing engine labels.
 * Internal config/API mode may be "fake"; never put that word in UI copy.
 */

export function engineDisplayName(modelMode: string | null | undefined): string {
  if (modelMode === "transformers") return "local model";
  // Default teaching engine (internal mode key: "fake") — no weights required.
  return "built-in engine";
}

/** Short status for the shell dot and header, e.g. "ready" or "built-in engine · ready". */
export function engineStatusLabel(opts: {
  loading?: boolean | undefined;
  error?: string | null | undefined;
  modelReady?: boolean | undefined;
  modelMode?: string | null | undefined;
  compact?: boolean | undefined;
  generating?: boolean | undefined;
}): string {
  if (opts.error) return "backend unreachable";
  if (opts.loading || opts.modelReady === undefined) return "checking…";
  if (!opts.modelReady) return "engine not loaded";
  if (opts.generating) {
    return opts.compact ? "generating…" : `${engineDisplayName(opts.modelMode)} · generating…`;
  }
  if (opts.compact) return "ready";
  return `${engineDisplayName(opts.modelMode)} · ready`;
}
