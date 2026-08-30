import { describe, expect, it } from "vitest";
import { deriveGenStage, stageProgressPct } from "./genProgress";

describe("deriveGenStage", () => {
  it("is preparing before any tokens", () => {
    const stage = deriveGenStage({
      status: "running",
      controlTokens: 0,
      loadedTokens: 0,
      maxNewTokens: 48,
      accepted: false,
    });
    expect(stage.kind).toBe("preparing");
  });

  it("tracks clean sample token N of M", () => {
    const stage = deriveGenStage({
      status: "running",
      controlTokens: 12,
      loadedTokens: 0,
      maxNewTokens: 48,
      accepted: true,
    });
    expect(stage.kind).toBe("token");
    if (stage.kind === "token") {
      expect(stage.branch).toBe("control");
      expect(stage.n).toBe(12);
      expect(stage.m).toBe(48);
      expect(stage.label).toMatch(/Clean sample · token 12 of 48/);
    }
  });

  it("tracks watermarked sample token N of M", () => {
    const stage = deriveGenStage({
      status: "running",
      controlTokens: 48,
      loadedTokens: 20,
      maxNewTokens: 48,
      accepted: true,
    });
    expect(stage.kind).toBe("token");
    if (stage.kind === "token") {
      expect(stage.branch).toBe("loaded");
      expect(stage.n).toBe(20);
      expect(stage.label).toMatch(/Watermarked sample · token 20 of 48/);
    }
  });

  it("enters scoring when both branches finish tokens", () => {
    const stage = deriveGenStage({
      status: "running",
      controlTokens: 48,
      loadedTokens: 48,
      maxNewTokens: 48,
      accepted: true,
    });
    expect(stage.kind).toBe("scoring");
    expect(stageProgressPct(stage)).toBe(96);
  });

  it("reports done on completed", () => {
    const stage = deriveGenStage({
      status: "completed",
      controlTokens: 48,
      loadedTokens: 48,
      maxNewTokens: 48,
      accepted: true,
    });
    expect(stage.kind).toBe("done");
  });
});
