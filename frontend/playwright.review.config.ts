import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["final-local-review.spec.ts", "ux-journeys.spec.ts", "post-qa-presentation.spec.ts"],
  outputDir: "./test-results/final-review",
  workers: 1,
  timeout: 300_000,
  expect: { timeout: 60_000 },
  use: {
    baseURL: "http://127.0.0.1:3021", screenshot: "only-on-failure", trace: "retain-on-failure",
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
      args: process.env.PLAYWRIGHT_LOW_MEMORY === "true"
        ? ["--disable-gpu", "--in-process-gpu", "--renderer-process-limit=1"] : undefined,
    },
  },
});
