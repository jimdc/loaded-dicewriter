import { defineConfig, devices } from "@playwright/test";

/**
 * Visual-regression baseline for the quiet Lab shell.
 * Run with a production-ish static preview or full make dev.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  use: {
    baseURL: process.env.LDW_E2E_BASE ?? "http://127.0.0.1:4173",
    trace: "off",
    colorScheme: "light",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: "mobile-320",
      // Chromium-only so CI needs no WebKit download; 320px viewport still exercises layout.
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 320, height: 568 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
