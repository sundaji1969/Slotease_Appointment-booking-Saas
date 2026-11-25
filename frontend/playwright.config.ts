import { defineConfig } from "@playwright/test";

/**
 * E2E needs the API running (default http://localhost:8000) against a migrated database.
 * The frontend dev server is started automatically.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true, timeout: 60_000 },
});
