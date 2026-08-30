import { useCallback, useState } from "react";
import { DemoGallery } from "../components/DemoGallery";
import { EvidenceStrip } from "../components/EvidenceStrip";
import { OutputPair } from "../components/OutputPair";
import {
  DEMO_EXAMPLE,
  exampleToLiveState,
  getDemoExample,
} from "../data/demoExample";
import type { BranchLabel, DetectionSnapshot, TokenEvent } from "../types/generation";

function pickPedagogicalToken(tokens: TokenEvent[]): number | null {
  // Prefer a scored favored token with a clear probability shift; else first eligible.
  let best: { pos: number; score: number } | null = null;
  for (const t of tokens) {
    if (!t.eligible) continue;
    const base = t.base_probability ?? 0;
    const after = t.biased_probability ?? t.final_sampling_probability ?? base;
    const shift = Math.abs(after - base);
    const score = (t.favored ? 1 : 0) + shift * 4;
    if (!best || score > best.score) {
      best = { pos: t.position, score };
    }
  }
  return best?.pos ?? (tokens[0]?.position ?? null);
}

/**
 * Gallery-only demo surface: frozen coherent clean/loaded pairs.
 * Live generation lives offline in scripts/generate_demo_example.py (see README).
 */
export function Lab() {
  const [selectedDemoId, setSelectedDemoId] = useState(DEMO_EXAMPLE.id);
  const [gen, setGen] = useState(() => exampleToLiveState(DEMO_EXAMPLE));
  const [revealClasses, setRevealClasses] = useState(true);
  const [selectedBranch, setSelectedBranch] = useState<BranchLabel>("loaded");
  const [selectedPosition, setSelectedPosition] = useState<number | null>(() =>
    pickPedagogicalToken(DEMO_EXAMPLE.loaded.tokens as TokenEvent[]),
  );

  const selectDemo = useCallback((id: string) => {
    const example = getDemoExample(id);
    setSelectedDemoId(example.id);
    setRevealClasses(true);
    setGen(exampleToLiveState(example));
    setSelectedBranch("loaded");
    setSelectedPosition(pickPedagogicalToken(example.loaded.tokens as TokenEvent[]));
  }, []);

  const activeDemo = getDemoExample(selectedDemoId);
  const selectedToken =
    selectedPosition === null
      ? null
      : (selectedBranch === "control" ? gen.control.tokens : gen.loaded.tokens).find(
          (t) => t.position === selectedPosition,
        ) ?? null;

  return (
    <div>
      <header className="lab-header">
        <div>
          <h1 className="lab-header__title">loaded-dicewriter</h1>
        </div>
      </header>

      <p className="page-lede" style={{ marginBottom: "1.25rem" }}>
        A secret key slightly favors some words at each step. Alone those choices look ordinary;
        together they form a statistical signal.
      </p>

      <DemoGallery selectedId={selectedDemoId} onSelect={selectDemo} />

      <OutputPair
        prompt={activeDemo.prompt}
        control={gen.control}
        loaded={gen.loaded}
        empty={false}
        generating={false}
        revealClasses={revealClasses}
        selectedBranch={selectedBranch}
        selectedPosition={selectedPosition}
        onSelectToken={(branch, position) => {
          setSelectedBranch(branch);
          setSelectedPosition(position);
        }}
        onRevealChange={setRevealClasses}
        showRevealToggle
        demoBadge
        showTokenDiff
        flipSummary={
          typeof activeDemo.flip_rate === "number"
            ? {
                flipped: activeDemo.flipped_tokens ?? 0,
                aligned: activeDemo.aligned_tokens ?? 0,
                flipRate: activeDemo.flip_rate,
              }
            : null
        }
        demoLabel={`Gallery · ${activeDemo.label}${
          activeDemo.strength_label ? ` · ${activeDemo.strength_label}` : ""
        }`}
      />

      <EvidenceStrip
        control={gen.control.detection as DetectionSnapshot | null}
        loaded={gen.loaded.detection as DetectionSnapshot | null}
        generating={false}
      />

      <section
        className="token-inspector"
        hidden={!selectedToken}
        aria-hidden={!selectedToken}
        data-region="token-inspector"
      >
        {selectedToken ? (
          <>
            <h2 className="token-inspector__title">
              Token {selectedToken.position} · “{selectedToken.text}”
            </h2>
            <p className="token-inspector__lede">
              {selectedToken.eligible
                ? selectedToken.favored
                  ? "Favored at this position under the secret green list."
                  : "Not favored at this position."
                : selectedToken.exclusion_reason === "missing_context"
                  ? "Excluded: context unavailable for portable scoring."
                  : selectedToken.exclusion_reason === "repeated_ngram"
                    ? "Excluded: repeated n-gram."
                    : "Excluded from scoring."}
              {selectedBranch === "loaded" &&
              selectedToken.biased_probability != null &&
              selectedToken.base_probability != null
                ? selectedToken.favored
                  ? ` Base probability ${(selectedToken.base_probability * 100).toFixed(1)}% → after bias ${(selectedToken.biased_probability * 100).toFixed(1)}%.`
                  : ` Logit unchanged; probability ${(selectedToken.base_probability * 100).toFixed(1)}% → ${(selectedToken.biased_probability * 100).toFixed(1)}% as favored alternatives gained mass.`
                : null}
            </p>
            {selectedToken.top_candidates_after &&
            selectedToken.top_candidates_after.length > 0 ? (
              <table className="candidate-table">
                <caption className="sr-only">Top candidates before and after watermark bias</caption>
                <thead>
                  <tr>
                    <th scope="col">candidate</th>
                    <th scope="col">class</th>
                    <th scope="col">base</th>
                    <th scope="col">after bias</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedToken.top_candidates_after.map((c) => {
                    const before = selectedToken.top_candidates_before?.find(
                      (b) => b.token_id === c.token_id,
                    );
                    const isSelected = c.token_id === selectedToken.token_id;
                    return (
                      <tr key={c.token_id} className={isSelected ? "is-selected" : undefined}>
                        <td>
                          {c.text}
                          {isSelected ? " ←" : ""}
                        </td>
                        <td>{c.favored ? "favored" : "not favored"}</td>
                        <td>{((before?.probability ?? 0) * 100).toFixed(1)}%</td>
                        <td>{(c.probability * 100).toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );
}
