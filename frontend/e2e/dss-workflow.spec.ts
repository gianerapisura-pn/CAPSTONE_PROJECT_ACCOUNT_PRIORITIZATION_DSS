import { expect, test } from "@playwright/test";
import path from "node:path";

test("demo administrator imports future data and reaches updated decision outputs", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("Demo mode is active")).toBeVisible();
  await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  await page.goto("/import");
  await page.locator('input[type="file"]').setInputFiles(path.resolve("../sample_data/test_fixtures/future_valid.csv"));
  await page.getByRole("button", { name: /Validate and preview/i }).click();
  await expect(page.getByText("Validation result")).toBeVisible();
  await expect(page.getByText("5", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Confirm import" }).click();
  const override = page.getByLabel("Required duplicate override reason");
  if (await override.isVisible().catch(() => false)) await override.fill("Controlled repeat for automated end-to-end verification.");
  await page.getByRole("button", { name: /Commit and run analytics/i }).click();
  await expect(page.getByText("Import and analytics publication completed")).toBeVisible({ timeout: 90_000 });

  await page.goto("/accounts");
  await page.getByLabel("Search accounts").fill("NEW FUTURE ACCOUNT");
  await expect(page.getByText("NEW FUTURE ACCOUNT")).toBeVisible();
  await page.getByRole("link", { name: "Open NEW FUTURE ACCOUNT" }).click();
  await page.waitForURL(/\/accounts\/NEW%20FUTURE%20ACCOUNT/, { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "NEW FUTURE ACCOUNT" })).toBeVisible();
  await expect(page.getByText("Current rank")).toBeVisible();

  await page.goto("/analytics/rfm");
  await expect(page.getByRole("heading", { name: "RFM analytics" })).toBeVisible();
  await expect(page.getByRole("table").getByText("NEW FUTURE ACCOUNT")).toBeVisible();

  await page.goto("/reports");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "CSV" }).first().click();
  expect((await download).suggestedFilename()).toContain("priorities");
});
