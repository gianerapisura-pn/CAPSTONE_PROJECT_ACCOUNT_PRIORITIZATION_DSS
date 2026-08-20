import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, ".") } },
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"], globals: true, css: false,
    exclude: ["tests/no-obsolete-terms.test.js", "e2e/**", "node_modules/**", ".next/**"] },
});
