import { defineConfig } from "../../frontend/node_modules/@playwright/test";
import path from "node:path";
import os from "node:os";

const frontend = process.cwd();
const temporary = process.env.RUNNER_TEMP || os.tmpdir();
const origin = "http://127.0.0.1:3011";
const database = path.join(temporary, `peslc-native-${Date.now()}.sqlite3`);

export default defineConfig({
  testDir: path.join(frontend, "e2e"),
  testMatch: "dss-workflow.spec.ts",
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  outputDir: path.join(temporary, "peslc-native-browser-results"),
  reporter: [
    ["dot"],
    ["junit", { outputFile: path.join(temporary, "peslc-native-browser-results", "results.xml") }],
  ],
  use: { baseURL: origin, trace: "retain-on-failure", screenshot: "only-on-failure" },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8011",
      cwd: path.resolve(frontend, "../backend"),
      url: "http://127.0.0.1:8011/health",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        APP_ENV: "test", DEMO_MODE: "true",
        DATABASE_URL: "sqlite:///" + database,
        SUPABASE_URL: "", SUPABASE_SERVICE_ROLE_KEY: "",
        CORS_ALLOWED_ORIGINS: origin,
        DEMO_STORAGE_PATH: path.join(temporary, "peslc-native-source"),
        DEMO_MODEL_STORAGE_PATH: path.join(temporary, "peslc-native-models"),
        POWER_BI_AUTO_REFRESH_ENABLED: "false",
      },
    },
    {
      command: "node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3011",
      cwd: frontend,
      url: origin + "/login",
      timeout: 180_000,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_DEMO_API_URL: "http://127.0.0.1:8011",
        NEXT_PUBLIC_DEMO_MODE: "true",
        NEXT_PUBLIC_SUPABASE_URL: "", NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
      },
    },
  ],
});
