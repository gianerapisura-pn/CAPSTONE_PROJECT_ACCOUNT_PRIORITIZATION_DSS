import { defineConfig } from "@playwright/test";

const isolatedDatabaseUrl = "sqlite:///./e2e-native-" + Date.now() + ".sqlite3";
// Keep the demo development-only; allow an alternate compiler for local QA.
const useWebpack = process.env.PLAYWRIGHT_USE_WEBPACK === "true";
const reuseDemoFrontend = process.env.PLAYWRIGHT_REUSE_DEMO_FRONTEND === "true";
const frontendOrigin = reuseDemoFrontend ? "http://127.0.0.1:3021" : "http://127.0.0.1:3011";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["final-local-review.spec.ts", "ux-journeys.spec.ts", "post-qa-presentation.spec.ts"],
  outputDir: "./test-results/workflow",
  timeout: 300_000,
  expect: { timeout: 60_000 },
  use: { baseURL: frontendOrigin, trace: "retain-on-failure", screenshot: "only-on-failure",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : undefined },
  webServer: [
    {
      command: "powershell -NoProfile -Command \"Set-Location ../backend; .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011\"",
      url: "http://127.0.0.1:8011/health",
      timeout: 240_000,
      reuseExistingServer: false,
      env: { ...process.env, DATABASE_URL: isolatedDatabaseUrl, DEMO_MODE: "true", APP_ENV: "test",
        CORS_ALLOWED_ORIGINS: frontendOrigin },
    },
    ...(reuseDemoFrontend ? [] : [{
      command: "node node_modules/next/dist/bin/next dev " + (useWebpack ? "--webpack " : "") + "--hostname 127.0.0.1 --port 3011",
      url: "http://127.0.0.1:3011/login",
      timeout: 240_000,
      reuseExistingServer: false,
      env: { ...process.env, NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_DEMO_API_URL: "http://127.0.0.1:8011", NEXT_PUBLIC_DEMO_MODE: "true" },
    }]),
  ],
});
