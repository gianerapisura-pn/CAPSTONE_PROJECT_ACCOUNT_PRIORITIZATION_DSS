import { expect, test } from "@playwright/test";
import path from "node:path";
import { readFileSync } from "node:fs";

test("demo administrator imports future data and reaches updated decision outputs", async ({ page }) => {
  if (process.env.PLAYWRIGHT_REUSE_DEMO_FRONTEND === "true") {
    // Reuse compiled UI only; every API call still reaches a fresh test database.
    await page.route("http://127.0.0.1:8021/**", async route => {
      const target = new URL(route.request().url());
      target.port = "8011";
      await route.fulfill({ response: await route.fetch({ url: target.href }) });
    });
  }
  await page.goto("/login");
  await expect(page.getByText("Demo mode is active")).toBeVisible();
  await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("peslc-demo-session"))).toBe("administrator");
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/import");
  const fixture = readFileSync(path.resolve("../sample_data/test_fixtures/future_valid.csv"), "utf8")
    .replaceAll("2027", "2026").replaceAll("2030", "2026");
  await page.locator('input[type="file"]').setInputFiles({ name: "future-valid.csv", mimeType: "text/csv", buffer: Buffer.from(fixture) });
  await page.getByRole("button", { name: /Validate and preview/i }).click();
  await expect(page.getByText("Validation result")).toBeVisible();
  await expect(page.getByText("5", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm import" }).click();
  await page.getByLabel("Analysis reference date").fill("2026-07-10");
  await page.getByLabel("Evidence reference").fill("Isolated test fixture coverage record");
  await page.getByLabel("Evidence basis").fill("Synthetic test data are complete through the selected date");
  await page.getByLabel("Confirmation date").fill("2026-07-11");
  await page.getByRole("button", { name: /Commit and run analytics/i }).click();
  await expect(page.getByText("Import and analytics publication completed")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("link", { name: "Open Detailed Analytics" })).toBeVisible();
  await page.getByRole("link", { name: "View Updated Priorities" }).click();
  await expect(page).toHaveURL(/\/accounts/);
  await page.getByLabel("Search accounts").fill("New Future Account");
  await expect(page.getByText("No accounts match the selected filters.")).toBeVisible();

  await page.goto("/analytics/rfm");
  await expect(page.getByRole("heading", { name: "RFM analytics" })).toBeVisible();
  await expect(page.getByRole("table").getByText("New Future Account")).toHaveCount(0);

  await page.goto("/runs");
  await expect(page.getByText("2026-07-10")).toBeVisible();
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Detailed Analytics", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Annual Valid Sales Invoice Sales" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Priority Group Counts" })).toBeVisible();
  await page.getByRole("tab", { name: "Account & Prioritization Insights" }).click();
  await expect(page.getByRole("heading", { name: "RFM Score Distribution" })).toBeVisible();
  await page.getByRole("tab", { name: "Analytics Validation" }).click();
  await page.getByText("Model selection and historical classification evidence").click();
  await expect(page.getByRole("heading", { name: "Prediction Horizon Comparison" })).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).first().click();
  expect((await download).suggestedFilename()).toContain("priorities");
});
