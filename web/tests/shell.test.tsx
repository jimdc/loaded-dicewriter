import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "../src/app/App";
import { DEMO_EXAMPLE, DEMO_GALLERY } from "../src/data/demoExample";

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

function waitForLab() {
  return screen.findByRole("heading", { name: /worked examples/i });
}

describe("quiet application shell", () => {
  afterEach(() => {
    cleanup();
  });

  it("boots into a gallery of pre-loaded real-English examples", async () => {
    renderApp("/");
    expect(screen.getByRole("heading", { name: /loaded-dicewriter/i })).toBeInTheDocument();
    await waitForLab();
    // Never surface internal "fake" mode on the main surface.
    expect(screen.queryByText(/fake ready/i)).toBeNull();
    expect(screen.queryByText(/\bfake\b/i)).toBeNull();
    // Gallery is primary — and the whole experience.
    expect(screen.getByRole("heading", { name: /worked examples/i })).toBeInTheDocument();
    expect(screen.getByRole("listbox", { name: /precomputed examples/i })).toBeInTheDocument();
    expect(DEMO_GALLERY.examples.length).toBeGreaterThanOrEqual(4);
    expect(screen.getByRole("heading", { name: /^clean$/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^watermarked$/i })).toBeInTheDocument();
    const loadedDet = DEMO_EXAMPLE.loaded.detection;
    expect(loadedDet).not.toBeNull();
    const loadedZ = loadedDet!.z_score.toFixed(2);
    expect(
      screen.getByText(new RegExp(`WATERMARKED · z ${loadedZ.replace(".", "\\.")}`, "i")),
    ).toBeInTheDocument();
    expect(screen.getByText(/Gallery ·/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /signal strength/i })).toBeInTheDocument();
  });

  it("renders prompt and continuation as one continuous passage", async () => {
    renderApp("/");
    await waitForLab();
    const prefixes = document.querySelectorAll('[data-region="prompt-prefix"]');
    expect(prefixes.length).toBeGreaterThanOrEqual(2); // clean + watermarked
    const prompt = DEMO_EXAMPLE.prompt.trim();
    for (const el of prefixes) {
      expect(el.textContent?.trim()).toBe(prompt);
    }
    const passage = prefixes[0]!.closest(".token-text");
    expect(passage).toBeTruthy();
    expect(passage!.querySelectorAll("button.tok").length).toBeGreaterThan(0);
  });

  it("has no live generate UI (gallery-only)", async () => {
    renderApp("/");
    await waitForLab();
    expect(screen.queryByRole("button", { name: /generate pair/i })).toBeNull();
    expect(screen.queryByText(/^try your own$/i)).toBeNull();
    expect(document.querySelector(".try-own")).toBeNull();
    expect(document.querySelector(".prompt-composer")).toBeNull();
    // How-it-works / try-it-yourself lives in the README, not on the page.
    expect(screen.queryByRole("heading", { name: /how it works/i })).toBeNull();
    expect(document.querySelector(".how-it-works")).toBeNull();
    expect(screen.queryByText(/scripts\/generate_demo_example\.py/i)).toBeNull();
  });

  it("is a single page without Settings chrome or engine status", async () => {
    renderApp("/");
    await waitForLab();
    expect(screen.queryByRole("link", { name: /^settings$/i })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^settings$/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /^sessions$/i })).toBeNull();
    expect(screen.queryAllByText(/built-in engine · ready/i)).toHaveLength(0);
    expect(document.querySelector(".top-bar")).toBeTruthy();
    expect(document.querySelector(".sidebar")).toBeNull();
  });

  it("redirects legacy /settings and /sessions to the single demo surface", async () => {
    renderApp("/settings");
    await waitForLab();
    expect(screen.getByRole("heading", { name: /worked examples/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^settings$/i })).toBeNull();

    cleanup();
    renderApp("/sessions");
    await waitForLab();
    expect(screen.getByRole("heading", { name: /worked examples/i })).toBeInTheDocument();
  });

  it("shows token inspector for the selected gallery example", async () => {
    renderApp("/");
    await waitForLab();
    const inspector = document.querySelector('[data-region="token-inspector"]');
    expect(inspector).toBeTruthy();
    expect(inspector).not.toHaveAttribute("hidden");
  });

  it("switches gallery examples and updates the pair", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await waitForLab();
    if (DEMO_GALLERY.examples.length < 2) return;
    const second = DEMO_GALLERY.examples[1]!;
    const card = screen.getByRole("option", { name: new RegExp(second.label, "i") });
    await user.click(card);
    expect(card).toHaveAttribute("aria-selected", "true");
    const lz = second.loaded.detection!.z_score.toFixed(2);
    expect(
      screen.getByText(new RegExp(`WATERMARKED · z ${lz.replace(".", "\\.")}`, "i")),
    ).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Gallery · ${second.label}`, "i"))).toBeInTheDocument();
  });

  it("keeps a short concept intro without overclaiming", async () => {
    renderApp("/");
    await waitForLab();
    // Page intro is the two-sentence concept only; honest-scope disclaimer lives in README.
    expect(
      screen.getByText(/A secret key slightly favors some words at each step/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/together they form a statistical signal/i)).toBeInTheDocument();
    expect(screen.queryByText(/Watch a watermark load the dice/i)).toBeNull();
    expect(screen.queryByText(/One idea:/i)).toBeNull();
    expect(screen.queryByText(/not Claude/i)).toBeNull();
    expect(screen.queryByText(/99\.9999%/i)).toBeNull();
    expect(screen.queryByText(/Claude detected/i)).toBeNull();
    expect(screen.queryByText(/Pick one to inspect the signal/i)).toBeNull();
  });
});
