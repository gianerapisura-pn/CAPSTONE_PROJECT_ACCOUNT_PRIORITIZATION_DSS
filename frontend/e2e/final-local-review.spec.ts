import { expect, test } from "@playwright/test";

test("verified published data, drilldowns, explanations, and responsive reports", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const api = "http://127.0.0.1:8021";
  const all = await (await request.get(api + "/accounts?page_size=500")).json();
  expect(all.items.length).toBe(all.total);
  const ranked = all.items.filter((row: { is_ranked: boolean }) => row.is_ranked);
  const categories = [...new Set(ranked.map((row: { business_category: string }) => row.business_category))];
  await page.goto("/login");
  await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
  await expect(page).toHaveURL(/dashboard/);
  await page.goto("/accounts");
  await expect(page.locator(".pagination")).toContainText("of " + ranked.length);
  await expect(page.locator("tbody tr")).toHaveCount(Math.min(10, ranked.length));
  await page.getByLabel("Search accounts").fill(ranked[0].account);
  await expect(page.locator("tbody tr")).toHaveCount(1);
  const filteredUrl = page.url();
  await page.reload();
  await expect(page.getByLabel("Search accounts")).toHaveValue(ranked[0].account);
  await page.getByRole("link", { name: "Open " + ranked[0].account, exact: true }).click();
  await expect(page.getByRole("heading", { name: "Why this score?" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to Filtered Accounts" })).toHaveAttribute("href", "/accounts" + new URL(filteredUrl).search);
  await expect(page.getByText("Next Account", { exact: true })).toHaveAttribute("aria-disabled", "true");
  await page.getByRole("link", { name: "Back to Filtered Accounts" }).click();
  await expect(page.getByLabel("Search accounts")).toHaveValue(ranked[0].account);

  for (const width of [1440, 1366, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Annual Valid Sales Invoice Sales" })).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: test.info().outputPath(width + "-management.png"), fullPage: false });
    await page.getByRole("tab", { name: "Account & Prioritization Insights" }).click();
    const composition = page.getByRole("region", { name: "Business Composition" });
    await expect(composition.locator(".recharts-bar-rectangle")).toHaveCount(categories.length);
    await composition.getByText("Select a category by name").click();
    const chosen = String(categories[0]);
    await composition.getByLabel("Business category selection").selectOption(chosen);
    const members = ranked.filter((row: { business_category: string }) => row.business_category === chosen);
    await expect(composition.locator(".business-selected-category")).toContainText(members.length + " ranked accounts");
    const categoryLink = composition.getByRole("link", { name: "View Matching Accounts in Account Prioritization" });
    const target = new URL(await categoryLink.getAttribute("href") ?? "", "http://127.0.0.1:3021");
    expect(target.searchParams.get("business_category")).toBe(chosen);
    await expect(page.getByRole("heading", { name: "B2B status and prioritization" })).toHaveCount(0);
    await composition.getByText(/Explore Primary Business Types/).click();
    await expect(composition.getByLabel("Search Business Type")).toBeVisible();
    await composition.locator(".business-chart-plot").screenshot({ path: test.info().outputPath(width + "-category-chart.png") });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: test.info().outputPath(width + "-insights.png"), fullPage: false });
    await page.getByRole("tab", { name: "Analytics Validation" }).click();
    await page.getByText("Model selection and historical classification evidence").click();
    await page.getByText("Weight sensitivity, backtests, and technical robustness").click();
    await expect(page.getByRole("heading", { name: "CatBoost feature-set sensitivity" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Historical 12-month buyer incidence by Priority Group" })).toBeVisible();
    const layout = await page.evaluate(() => ({ width: window.innerWidth, document: document.documentElement.scrollWidth }));
    expect(layout.document).toBeLessThanOrEqual(layout.width + 1);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: test.info().outputPath(width + "-validation.png"), fullPage: false });
  }
  expect(errors).toEqual([]);
});

test("account explanation stays open through keyboard scroll and fits the mobile viewport", async ({ page, request }) => {
  const api = "http://127.0.0.1:8021";
  const data = await (await request.get(api + "/accounts?eligibility=ranked&page_size=1")).json();
  const ranked = data.items;
  await page.addInitScript(() => sessionStorage.setItem("peslc-demo-session", "administrator"));
  for (const height of [900, 667]) {
    await page.setViewportSize({ width: 390, height });
    await page.goto("/accounts");
    const value = page.locator("tbody tr").first().getByRole("button", { name: ranked[0].final_priority_score.toFixed(4), exact: true });
    await value.focus();
    const explanation = page.getByRole("tooltip");
    await expect(explanation).toBeVisible();
    await explanation.hover();
    await explanation.getByText("Saved values for this result").click();
    await expect(explanation).toContainText("Recency:");
    const box = await explanation.boundingBox();
    expect(box?.x).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(390);
    expect(box?.y).toBeGreaterThanOrEqual(0);
    expect((box?.y ?? 0) + (box?.height ?? 0)).toBeLessThanOrEqual(height);
    await page.screenshot({ path: test.info().outputPath("390-" + height + "-account-explanation.png") });
    await page.keyboard.press("Escape");
    await expect(explanation).toHaveCount(0);
  }
});

test("all authorized local pages render without runtime or API failures", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("response", response => {
    if (response.url().startsWith("http://127.0.0.1:8021") && response.status() >= 500)
      errors.push(response.status() + " " + response.url());
  });
  await page.addInitScript(() => sessionStorage.setItem("peslc-demo-session", "administrator"));
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const route of ["/dashboard", "/accounts", "/analytics/rfm", "/analytics/settlement",
    "/analytics/predictive", "/analytics/sensitivity", "/profile", "/runs", "/import/history", "/settings", "/import"]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Reading the latest successful analytical run.")).toHaveCount(0);
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
    await page.screenshot({ path: test.info().outputPath(route.slice(1).replaceAll("/", "-") + ".png") });
  }
  expect(errors).toEqual([]);
});
