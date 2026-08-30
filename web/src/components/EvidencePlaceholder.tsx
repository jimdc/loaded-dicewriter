/** Empty evidence strip — structure only until the detector card. */
export function EvidencePlaceholder() {
  // Threshold marker at ~55% of the track for z=4 visual reference (purely decorative now).
  const thresholdPct = 55;

  return (
    <section className="evidence-panel" aria-labelledby="evidence-heading">
      <h2 id="evidence-heading" className="evidence-panel__label">
        Evidence
      </h2>
      <div
        className="evidence-strip"
        role="img"
        aria-label="Evidence strip placeholder. No scores yet. Detection threshold z greater than or equal to 4.0 will mark here after generation."
      >
        <div className="evidence-strip__track" />
        <div
          className="evidence-strip__threshold"
          style={{ left: `${thresholdPct}%` }}
          aria-hidden="true"
        />
        <span
          className="evidence-strip__threshold-label"
          style={{ left: `${thresholdPct}%` }}
          aria-hidden="true"
        >
          z 4.0
        </span>
        <div
          className="evidence-strip__marker"
          style={{ left: "0%" }}
          aria-hidden="true"
        />
      </div>
      <p className="evidence-panel__hint">
        After generation, a single accumulation strip will show how weak token-level biases become a
        z-score. No evidence yet.
      </p>
    </section>
  );
}
