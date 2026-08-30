import { expect, test } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const screenshotDir = path.resolve(here, "../../../docs/screenshots");

test.describe("quiet shell baseline", () => {
  test("desktop demo surface is calm and navigable", async ({ page }, testInfo) => {
    // Gallery is frozen JSON — no API required.
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /loaded-dicewriter/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /worked examples/i })).toBeVisible();
    await expect(page.getByRole("listbox", { name: /precomputed examples/i })).toBeVisible();
    await expect(page.getByText(/Gallery ·/i)).toBeVisible();
    await expect(page.getByText(/fake ready/i)).toHaveCount(0);
    // Gallery-only: no live generate, no Settings chrome.
    await expect(page.getByRole("button", { name: /generate pair/i })).toHaveCount(0);
    await expect(page.getByRole("link", { name: /settings/i })).toHaveCount(0);
    await expect(page.getByText(/built-in engine · ready/i)).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /how it works/i })).toBeVisible();
    await expect(
      page.locator(".output-card--loaded [data-region='prompt-prefix']"),
    ).toBeVisible();

    const name =
      testInfo.project.name === "mobile-320"
        ? "lab-empty-mobile-320.png"
        : "lab-empty-desktop.png";
    await page.screenshot({
      path: path.join(screenshotDir, name),
      fullPage: true,
    });
    if (testInfo.project.name !== "mobile-320") {
      await page.screenshot({
        path: path.join(screenshotDir, "after-desktop.png"),
        fullPage: true,
      });
      await expect(page.locator(".top-bar")).toBeVisible();
    }
  });
});
