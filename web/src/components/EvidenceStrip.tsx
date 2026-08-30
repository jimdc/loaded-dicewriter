import type { DetectionSnapshot } from "../types/generation";

type Props = {
  control: DetectionSnapshot | null;
  loaded: DetectionSnapshot | null;
  threshold?: number;
  generating?: boolean;
};

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

/** Map z to a 0–1 position on the strip. Threshold sits near mid-right. */
function zToPct(z: number, threshold: number): number {
  const maxZ = Math.max(threshold * 1.8, 8);
  return clamp01(z / maxZ) * 100;
}

function formatZ(z: number | null | undefined): string {
  if (z === null || z === undefined || Number.isNaN(z)) return "—";
  return z.toFixed(2);
}

export function EvidenceStrip({
  control,
  loaded,
  threshold = 4.0,
  generating = false,
}: Props) {
  const controlZ = control?.z_score ?? 0;
  const loadedZ = loaded?.z_score ?? 0;
  const hasScores = Boolean(control || loaded);
  const thrPct = zToPct(threshold, threshold);

  const controlLabel = control
    ? `Clean z ${formatZ(control.z_score)}, ${control.verdict_label}`
    : "Clean: no scores yet";
  const loadedLabel = loaded
    ? `Watermarked z ${formatZ(loaded.z_score)}, ${loaded.verdict_label}`
    : "Watermarked: no scores yet";

  return (
    <section className="evidence-panel" aria-labelledby="evidence-heading">
      <h2 id="evidence-heading" className="evidence-panel__label">
        Signal strength
      </h2>
      <div className="evidence-panel__scores" aria-live="polite">
        <span>CLEAN · z {formatZ(control?.z_score)}</span>
        <span className="evidence-panel__scores-gap">
          strong when z ≥ {threshold.toFixed(1)}
        </span>
        <span>WATERMARKED · z {formatZ(loaded?.z_score)}</span>
      </div>
      <div
        className={`evidence-strip${generating ? " evidence-strip--live" : ""}`}
        role="img"
        aria-label={`${controlLabel}. ${loadedLabel}. Threshold z greater than or equal to ${threshold}.`}
      >
        <div className="evidence-strip__track" />
        <div
          className="evidence-strip__threshold"
          style={{ left: `${thrPct}%` }}
          aria-hidden="true"
        />
        <span
          className="evidence-strip__threshold-label"
          style={{ left: `${thrPct}%` }}
          aria-hidden="true"
        >
          z {threshold.toFixed(1)}
        </span>
        {hasScores ? (
          <>
            <div
              className="evidence-strip__marker evidence-strip__marker--control"
              style={{ left: `${zToPct(controlZ, threshold)}%` }}
              aria-hidden="true"
            />
            <div
              className="evidence-strip__marker evidence-strip__marker--loaded"
              style={{ left: `${zToPct(loadedZ, threshold)}%` }}
              aria-hidden="true"
            />
          </>
        ) : (
          <div
            className="evidence-strip__marker"
            style={{ left: "0%" }}
            aria-hidden="true"
          />
        )}
      </div>
      <p className="evidence-panel__hint">
        {generating && !loaded
          ? "Tokens are streaming — watch the watermarked marker climb as evidence accumulates."
          : loaded
            ? loaded.verdict === "detected"
              ? `Watermarked: ${loaded.num_tokens_scored} scored · z ${formatZ(loaded.z_score)} · strong signal under this app’s matching key — not a claim that arbitrary prose is AI-generated.`
              : loaded.verdict === "insufficient_scored_tokens"
                ? `Watermarked: ${loaded.num_tokens_scored} scored tokens so far — still gathering.`
                : `Watermarked: ${loaded.num_tokens_scored} scored · z ${formatZ(loaded.z_score)} · ${loaded.verdict_label}.`
            : "After generation, one strip shows how weak word-level biases become a z-score. No evidence yet."}
      </p>
    </section>
  );
}
