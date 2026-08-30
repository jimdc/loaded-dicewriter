import { useMemo, useState } from "react";
import type { BranchState, DetectionSnapshot, TokenEvent } from "../types/generation";
import { TokenText } from "./TokenText";

type Props = {
  /** Prompt that the continuation follows — rendered inline for a single flowing passage. */
  prompt?: string | null;
  control: BranchState;
  loaded: BranchState;
  empty?: boolean;
  generating?: boolean;
  revealClasses: boolean;
  selectedBranch: "control" | "loaded";
  selectedPosition: number | null;
  onSelectToken: (branch: "control" | "loaded", position: number) => void;
  onRevealChange: (reveal: boolean) => void;
  showRevealToggle: boolean;
  demoBadge?: boolean;
  /** Optional override for the demo badge label. */
  demoLabel?: string;
  /** When true (gallery / completed pairs), highlight tokens that differ between branches. */
  showTokenDiff?: boolean;
  /** Optional precomputed flip summary from a coupled demo fixture. */
  flipSummary?: { flipped: number; aligned: number; flipRate: number } | null;
};

/** Positions where clean and loaded token ids disagree (token-level diff). */
export function diffTokenPositions(
  control: TokenEvent[],
  loaded: TokenEvent[],
): Set<number> {
  const n = Math.min(control.length, loaded.length);
  const out = new Set<number>();
  for (let i = 0; i < n; i++) {
    if (control[i]!.token_id !== loaded[i]!.token_id) {
      out.add(control[i]!.position);
    }
  }
  // Extra trailing tokens on either side count as diffs at their positions.
  for (let i = n; i < control.length; i++) out.add(control[i]!.position);
  for (let i = n; i < loaded.length; i++) out.add(loaded[i]!.position);
  return out;
}

function metaLine(
  detection: DetectionSnapshot | null,
  tokenCount: number,
  generating: boolean,
): string {
  if (tokenCount === 0) {
    return generating ? "writing…" : "— scored · signal —";
  }
  if (!detection) {
    return generating ? `${tokenCount} tokens · writing…` : `${tokenCount} tokens`;
  }
  const z = detection.z_score.toFixed(2);
  const scored = detection.num_tokens_scored;
  if (detection.verdict === "insufficient_scored_tokens") {
    return `${scored} scored · z ${z}${generating ? " · writing…" : " · still gathering"}`;
  }
  if (detection.detected) {
    return `${scored} scored · z ${z} · strong signal`;
  }
  return `${scored} scored · z ${z} · weak / no signal`;
}

export function OutputPair({
  prompt = null,
  control,
  loaded,
  empty = true,
  generating = false,
  revealClasses,
  selectedBranch,
  selectedPosition,
  onSelectToken,
  onRevealChange,
  showRevealToggle,
  demoBadge = false,
  demoLabel,
  showTokenDiff = false,
  flipSummary = null,
}: Props) {
  const [mobileTab, setMobileTab] = useState<"control" | "loaded">("loaded");

  const controlTokens: TokenEvent[] = control.tokens;
  const loadedTokens: TokenEvent[] = loaded.tokens;
  const promptText = (prompt ?? "").trim();

  const diffPositions = useMemo(() => {
    if (!showTokenDiff || empty || generating) return null;
    if (controlTokens.length === 0 || loadedTokens.length === 0) return null;
    return diffTokenPositions(controlTokens, loadedTokens);
  }, [showTokenDiff, empty, generating, controlTokens, loadedTokens]);

  const computedFlip =
    flipSummary ??
    (diffPositions
      ? {
          flipped: diffPositions.size,
          aligned: Math.max(controlTokens.length, loadedTokens.length),
          flipRate:
            Math.max(controlTokens.length, loadedTokens.length) > 0
              ? diffPositions.size / Math.max(controlTokens.length, loadedTokens.length)
              : 0,
        }
      : null);

  return (
    <section aria-label="Clean vs watermarked pair">
      <div className="output-toolbar">
        {demoBadge ? (
          <span className="demo-badge" role="status">
            {demoLabel ?? "Gallery example — browse above"}
          </span>
        ) : (
          <span className="demo-badge demo-badge--spacer" aria-hidden="true" />
        )}
        {showRevealToggle ? (
          <label className="reveal-toggle">
            <input
              type="checkbox"
              checked={revealClasses}
              onChange={(e) => onRevealChange(e.target.checked)}
            />
            <span>Color favored tokens</span>
          </label>
        ) : (
          <span className="reveal-toggle reveal-toggle--placeholder" aria-hidden="true" />
        )}
      </div>

      {computedFlip && computedFlip.aligned > 0 && !generating && !empty ? (
        <p className="pair-diff-summary" role="status">
          <span className="pair-diff-summary__swatch" aria-hidden="true" />
          {computedFlip.flipped === 0
            ? "Same tokens on both sides — watermark bias did not flip a sample."
            : `${computedFlip.flipped} of ${computedFlip.aligned} tokens differ (${(
                computedFlip.flipRate * 100
              ).toFixed(0)}%) — highlighted in the passage. Same model draws; only the green-list bias changed the winners.`}
        </p>
      ) : null}

      <div className="segmented" role="group" aria-label="Show clean or watermarked output">
        <button
          type="button"
          className="segmented__btn"
          aria-pressed={mobileTab === "control"}
          onClick={() => setMobileTab("control")}
        >
          Clean
        </button>
        <button
          type="button"
          className="segmented__btn"
          aria-pressed={mobileTab === "loaded"}
          onClick={() => setMobileTab("loaded")}
        >
          Watermarked
        </button>
      </div>

      <div
        className={`output-pair${generating ? " output-pair--generating" : ""}`}
        data-mobile-tab={mobileTab}
        data-generating={generating ? "true" : "false"}
      >
        <article className="output-card output-card--control" aria-labelledby="control-heading">
          <header className="output-card__header">
            <h2 id="control-heading">Clean</h2>
            <span className="output-card__sub">no watermark</span>
          </header>
          <div className="output-card__body">
            {empty || controlTokens.length === 0 ? (
              generating ? (
                <p className="output-card__empty">
                  <span className="writing-state">
                    <span className="writing-state__spinner" aria-hidden="true" />
                    Writing clean sample…
                  </span>
                </p>
              ) : promptText ? (
                <p className="token-text">
                  <span className="token-text__prompt">{promptText}</span>
                  <span className="token-text__awaiting"> …</span>
                </p>
              ) : (
                <p className="output-card__empty">
                  Ordinary sampling will appear here — no watermark bias.
                </p>
              )
            ) : (
              <TokenText
                tokens={controlTokens}
                revealClasses={revealClasses}
                selectedPosition={selectedBranch === "control" ? selectedPosition : null}
                onSelect={(pos) => onSelectToken("control", pos)}
                emptyLabel="Ordinary sampling will appear here — no watermark bias."
                streaming={generating}
                diffPositions={diffPositions}
                promptPrefix={promptText || null}
              />
            )}
          </div>
          <div className="output-card__meta" aria-live="polite">
            {metaLine(control.detection, controlTokens.length, generating)}
          </div>
        </article>

        <article className="output-card output-card--loaded" aria-labelledby="loaded-heading">
          <header className="output-card__header">
            <h2 id="loaded-heading">Watermarked</h2>
            <span className="output-card__sub">secret green list</span>
          </header>
          <div className="output-card__body">
            {empty || loadedTokens.length === 0 ? (
              generating ? (
                <p className="output-card__empty">
                  <span className="writing-state">
                    <span className="writing-state__spinner" aria-hidden="true" />
                    Writing watermarked sample…
                  </span>
                </p>
              ) : promptText ? (
                <p className="token-text">
                  <span className="token-text__prompt">{promptText}</span>
                  <span className="token-text__awaiting"> …</span>
                </p>
              ) : (
                <p className="output-card__empty">
                  Watermarked sampling will appear here — subtle token annotations after generation.
                </p>
              )
            ) : (
              <TokenText
                tokens={loadedTokens}
                revealClasses={revealClasses}
                selectedPosition={selectedBranch === "loaded" ? selectedPosition : null}
                onSelect={(pos) => onSelectToken("loaded", pos)}
                emptyLabel="Watermarked sampling will appear here — subtle token annotations after generation."
                streaming={generating}
                diffPositions={diffPositions}
                promptPrefix={promptText || null}
              />
            )}
          </div>
          <div className="output-card__meta" aria-live="polite">
            {metaLine(loaded.detection, loadedTokens.length, generating)}
          </div>
        </article>
      </div>
    </section>
  );
}
