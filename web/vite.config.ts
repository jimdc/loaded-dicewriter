import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { normalizeViteBase } from "./src/normalizeBase";

const appBase = normalizeViteBase(process.env.APP_BASE_PATH);
const apiTarget = process.env.LDW_API_PROXY ?? "http://127.0.0.1:8765";

export default defineConfig({
  base: appBase,
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      // Dev default is root (`/`). When APP_BASE_PATH is set for local checks,
      // also proxy the prefixed API path (rewritten to root /api on the backend).
      "/api": {
        target: apiTarget,
        changeOrigin: false,
        ws: true,
      },
      ...(appBase !== "/"
        ? {
            [`${appBase}api`]: {
              target: apiTarget,
              changeOrigin: false,
              ws: true,
              rewrite: (p: string) => p.slice(appBase.length - 1), // keep leading /
            },
          }
        : {}),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: true,
    exclude: ["**/node_modules/**", "**/e2e/**", "**/dist/**"],
  },
});
