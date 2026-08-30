import { describe, expect, it } from "vitest";
import { normalizeViteBase } from "../src/normalizeBase";

// withBase / routerBasename depend on import.meta.env.BASE_URL (build-time).
// Test the pure normalizer here; runtime helpers are covered by shell tests
// under default base `/`.

describe("normalizeViteBase", () => {
  it("defaults empty/root to /", () => {
    expect(normalizeViteBase(undefined)).toBe("/");
    expect(normalizeViteBase("")).toBe("/");
    expect(normalizeViteBase("   ")).toBe("/");
    expect(normalizeViteBase("/")).toBe("/");
  });

  it("normalizes subpath slug with leading and trailing slash", () => {
    expect(normalizeViteBase("/loaded-dicewriter")).toBe("/loaded-dicewriter/");
    expect(normalizeViteBase("/loaded-dicewriter/")).toBe("/loaded-dicewriter/");
    expect(normalizeViteBase("loaded-dicewriter")).toBe("/loaded-dicewriter/");
    expect(normalizeViteBase("loaded-dicewriter/")).toBe("/loaded-dicewriter/");
  });
});
