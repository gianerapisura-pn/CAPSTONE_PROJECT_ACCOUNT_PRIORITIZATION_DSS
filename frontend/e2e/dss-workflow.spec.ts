import { expect, test } from "@playwright/test";
import path from "node:path";

test("demo administrator imports future data and reaches updated decision outputs", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("Demo mode is active")).toBeVisible();
  await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem("peslc-demo-session"))).toBe("administrator");
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/import");
  await page.locator('input[type="file"]').setInputFiles(path.resolve("../sample_data/test_fixtures/future_valid.csv"));
  await page.getByRole("button", { name: /Validate and preview/i }).click();
  await expect(page.getByText("Validation result")).toBeVisible();
  await expect(page.getByText("5", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm import" }).click();
  await page.getByLabel("Analysis reference date").fill("2030-07-10");
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
  await expect(page.getByText("2030-07-10")).toBeVisible();
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Detailed Analytics", exact: true })).toBeVisible();
  await expect(page.getByText("Configuration required")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).first().click();
  expect((await download).suggestedFilename()).toContain("priorities");
});
