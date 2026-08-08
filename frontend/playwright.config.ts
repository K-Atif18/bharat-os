import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end configuration.
 *
 * Both the API and the frontend are started by Playwright, against a dedicated
 * database, so the E2E run never touches development data and requires no manual
 * setup beyond Postgres being available.
 */
const API_PORT = 8100;
const WEB_PORT = 3100;

const E2E_DATABASE_URL =
  process.env.BHARAT_OS_E2E_DATABASE_URL ?? "postgresql+psycopg:///bharat_os_e2e";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",

  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      // Migrate and seed before serving, so the run is reproducible from an empty
      // database rather than depending on prior state.
      command: [
        "cd ../backend",
        `&& BHARAT_OS_DATABASE_URL=${E2E_DATABASE_URL} .venv/bin/alembic upgrade head`,
        `&& BHARAT_OS_DATABASE_URL=${E2E_DATABASE_URL} .venv/bin/python -m bharat_os.seed.load`,
        `&& BHARAT_OS_DATABASE_URL=${E2E_DATABASE_URL} .venv/bin/uvicorn bharat_os.main:app --port ${API_PORT}`,
      ].join(" "),
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        BHARAT_OS_ENVIRONMENT: "development",
        BHARAT_OS_ENCRYPTION_KEY: "Zh3rVJ0dQ8pQ0Z1kX2wA9sT4nR6uY8bC1dE3fG5hI7k=",
        // The E2E frontend runs on its own port, so it has to be an allowed
        // origin. Credentials are sent with every request, so this list is
        // explicit rather than a wildcard.
        BHARAT_OS_CORS_ALLOWED_ORIGINS: `http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}`,
      },
    },
    {
      command: `npm run dev -- --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_PORT: String(API_PORT),
      },
    },
  ],
});
