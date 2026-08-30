import type { GenerationLiveState } from "../types/generation";

/** Staged live-generation progress — not a binary spinner. */
export type GenStage =
  | { kind: "idle" }
  | { kind: "preparing"; label: string }
  | { kind: "token"; branch: "control" | "loaded"; n: number; m: number; label: string }
  | { kind: "scoring"; label: string }
  | { kind: "done"; label: string };

export type GenProgressInput = {
  status: GenerationLiveState["status"];
  controlTokens: number;
  loadedTokens: number;
  maxNewTokens: number;
  /** True after the client has a generation id / stream is open. */
  accepted: boolean;
  /** True once generation_finished (or equivalent) has been seen. */
  finishedEvent?: boolean;
};

/**
 * Derive a user-facing stage from live pair generation state.
 *
 * Order: preparing → clean token N/M → watermarked token N/M → scoring → done.
 * The toy engine runs branches sequentially, so control completes before loaded.
 */
export function deriveGenStage(input: GenProgressInput): GenStage {
  const { status, controlTokens, loadedTokens, maxNewTokens, accepted } = input;
  const m = Math.max(1, maxNewTokens);

  if (status === "idle") return { kind: "idle" };
  if (status === "failed" || status === "busy") return { kind: "idle" };
  if (status === "completed" || status === "stopped") {
    return { kind: "done", label: status === "stopped" ? "Stopped" : "Pair ready" };
  }

  if (status === "running") {
    if (!accepted || (controlTokens === 0 && loadedTokens === 0)) {
      return { kind: "preparing", label: "Preparing…" };
    }
    // Control branch first (sequential pairing).
    if (loadedTokens === 0 && controlTokens < m) {
      // Still on control, or control just finished and loaded not started.
      if (controlTokens > 0 && controlTokens < m) {
        return {
          kind: "token",
          branch: "control",
          n: controlTokens,
          m,
          label: `Clean sample · token ${controlTokens} of ${m}`,
        };
      }
      if (controlTokens === 0) {
        return { kind: "preparing", label: "Preparing…" };
      }
      // controlTokens === m, loaded still 0 → transition into loaded / scoring handoff
      return {
        kind: "token",
        branch: "loaded",
        n: 0,
        m,
        label: `Watermarked sample · starting…`,
      };
    }
    if (loadedTokens > 0 && loadedTokens < m) {
      return {
        kind: "token",
        branch: "loaded",
        n: loadedTokens,
        m,
        label: `Watermarked sample · token ${loadedTokens} of ${m}`,
      };
    }
    // Both branches at capacity (or early EOS filled both): finalize scores.
    if (controlTokens > 0 && loadedTokens > 0) {
      // If still running after both have tokens at/near end, show scoring.
      if (loadedTokens >= m || controlTokens >= m) {
        return { kind: "scoring", label: "Scoring watermark signal…" };
      }
      return {
        kind: "token",
        branch: "loaded",
        n: loadedTokens,
        m,
        label: `Watermarked sample · token ${loadedTokens} of ${m}`,
      };
    }
    return { kind: "preparing", label: "Preparing…" };
  }

  return { kind: "idle" };
}

export function stageProgressPct(stage: GenStage): number | null {
  if (stage.kind === "preparing") return 4;
  if (stage.kind === "token") {
    const branchWeight = stage.branch === "control" ? 0 : 0.5;
    const within = stage.m > 0 ? stage.n / stage.m : 0;
    return Math.round((branchWeight + within * 0.5) * 100);
  }
  if (stage.kind === "scoring") return 96;
  if (stage.kind === "done") return 100;
  return null;
}
