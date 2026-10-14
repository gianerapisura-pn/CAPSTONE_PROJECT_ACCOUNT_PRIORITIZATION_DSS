import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { chromium } from "@playwright/test";

const base = process.env.LOCAL_DEMO_URL ?? "http://127.0.0.1:3012";
await mkdir("test-results", { recursive: true });
const browser = await chromium.launch();
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport });
    await page.goto(`${base}/login`);
    await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
    await page.goto(`${base}/dashboard`);
    await page.getByRole("heading", { name: "Management overview" }).waitFor();
    await page.getByText("84 B2B analytical profiles").waitFor();
    const boxes = await page.evaluate(() => {
      const topbar = document.querySelector(".topbar")?.getBoundingClientRect();
      const header = document.querySelector(".page-header")?.getBoundingClientRect();
      const rows = [...document.querySelectorAll(".compact-list > a, .compact-list > div")];
      return {
        topbar: topbar && { bottom: topbar.bottom },
        header: header && { top: header.top },
        rowOverflow: rows.some(row => row.scrollWidth > row.clientWidth + 1),
      };
    });
    assert.ok(boxes.header && boxes.topbar && boxes.header.top >= boxes.topbar.bottom);
    assert.equal(boxes.rowOverflow, false);
    await page.screenshot({ path: `test-results/local-dashboard-${viewport.width}.png` });
    await page.goto(`${base}/reports`);
    await page.getByRole("heading", { name: "Detailed Analytics" }).waitFor();
    await page.getByText("Verified B2B profiles").waitFor();
    await page.locator(".recharts-line-curve").first().waitFor();
    assert.ok(await page.locator(".recharts-line-curve").first().getAttribute("d"));
    await page.screenshot({ path: `test-results/local-reports-${viewport.width}.png` });
    console.log(`${viewport.width}px dashboard and native charts: OK`);
    await page.close();
  }
} finally {
  await browser.close();
}
