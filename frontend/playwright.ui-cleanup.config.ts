import { defineConfig } from "@playwright/test";

// Full-study read tests use an explicitly launched isolated API/database copy.
export default defineConfig({
  testDir:"./e2e",testMatch:"ui-cleanup.spec.ts",workers:1,timeout:180_000,
  outputDir:"./test-results/ui-cleanup",expect:{timeout:60_000},
  use:{baseURL:"http://127.0.0.1:3077",viewport:{width:1366,height:900},screenshot:"only-on-failure",trace:"retain-on-failure"},
});
