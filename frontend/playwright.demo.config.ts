import { defineConfig, devices } from "@playwright/test";

import baseConfig from "./playwright.config";

/**
 * Curated media configuration.
 *
 * It reuses the same migrated, seeded backend and real frontend as the normal
 * E2E suite, while keeping video recording out of routine test runs.
 */
export default defineConfig({
  ...baseConfig,
  testDir: "./demo",
  outputDir: "./test-results/demo",
  reporter: "list",
  retries: 0,
  projects: [{ name: "demo-chromium", use: { ...devices["Desktop Chrome"] } }],
  use: {
    ...baseConfig.use,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "off",
  },
});
