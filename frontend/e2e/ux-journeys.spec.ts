import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("peslc-demo-session", "administrator"));
});

test("category, filtered list, detail, neighbors, and browser history form a complete round trip", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", req => {
    const url = new URL(req.url());
    if (url.port === "8021" && (url.pathname.startsWith("/accounts") || url.pathname.startsWith("/exports"))) {
      if (url.searchParams.has("returnTo") || url.searchParams.has("viaList")) errors.push("UI metadata reached the API");
    }
  });
  await page.goto("/reports");
  await page.getByRole("tab", { name: "Account & Prioritization Insights" }).click();
  const composition = page.getByRole("region", { name: "Business Composition" });
  await composition.getByText("Select a category by name").click();
  await composition.getByLabel("Business category selection").selectOption("Construction & Engineering");
  await expect(composition.locator(".business-selected-category")).toContainText("30 ranked accounts");
  for (const [group, count] of [["High", 8], ["Medium", 11], ["Low", 11]] as const) {
    await expect(composition.locator(".business-group-card." + group.toLowerCase())).toContainText(String(count));
  }
  await composition.getByRole("button", { name: "Select High Priority" }).click();
  await composition.getByRole("link", { name: "View Matching Accounts in Account Prioritization" }).click();
  await expect(page.getByLabel("Priority Group", { exact: true })).toHaveValue("High");
  await expect(page.getByLabel("Business category", { exact: true })).toHaveValue("Construction & Engineering");
  await expect(page.locator(".pagination")).toContainText("of 8");
  await page.getByLabel("Sort accounts").selectOption("account");
  await page.getByLabel("Sort direction").selectOption("desc");
  const first = page.locator("tbody tr").first();
  const originalRank = await first.locator("td").first().innerText();
  const accountName = await first.locator("td").nth(1).innerText();
  const expected = await (await request.get("http://127.0.0.1:8021/accounts?eligibility=ranked&priority_group=High&business_category=Construction%20%26%20Engineering&sort_by=account&sort_direction=desc")).json();
  expect(originalRank).toBe("#" + expected.items[0].priority_rank);
  await first.getByRole("link", { name: "Open " + accountName }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(accountName);
  const score = page.locator(".account-hero").getByRole("button").filter({ hasText: /^0\./ }).first();
  await score.focus();
  await expect(page.getByRole("tooltip").filter({ hasText: "Final Priority Score" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("link", { name: "Next Account", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText(accountName);
  await page.getByRole("link", { name: "Previous Account", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(accountName);
  await page.getByRole("link", { name: "Back to Filtered Accounts" }).click();
  await expect(page.getByLabel("Sort accounts")).toHaveValue("account");
  await expect(page.getByLabel("Sort direction")).toHaveValue("desc");
  await page.getByRole("link", { name: "Back to Business Composition" }).click();
  await expect(page.getByRole("tab", { name: "Account & Prioritization Insights" })).toHaveAttribute("aria-selected", "true");
  await expect(composition.locator(".business-selected-category")).toContainText("30 ranked accounts");
  await expect(composition.getByRole("button", { name: "Select High Priority" })).toHaveAttribute("aria-pressed", "true");
  await expect(composition).toBeFocused();
  expect((await composition.boundingBox())!.y).toBeGreaterThanOrEqual(68);
  expect((await composition.boundingBox())!.y).toBeLessThan(250);
  await page.reload();
  await expect(composition.getByRole("button", { name: "Select High Priority" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("tab", { name: "Management Overview" }).click();
  await page.goBack();
  await expect(page.getByRole("tab", { name: "Account & Prioritization Insights" })).toHaveAttribute("aria-selected", "true");
  await page.goForward();
  await expect(page.getByRole("tab", { name: "Management Overview" })).toHaveAttribute("aria-selected", "true");
  expect(errors).toEqual([]);
});

test("business type search and explorer state survive list and account-detail visits", async ({ page, request }) => {
  const all = await (await request.get("http://127.0.0.1:8021/accounts?eligibility=ranked&page_size=500")).json();
  const type = all.items.find((row: { business_category: string; primary_business_type: string }) => row.business_category === "Construction & Engineering").primary_business_type;
  await page.goto("/reports?tab=account-insights&business_category=Construction%20%26%20Engineering");
  const composition = page.getByRole("region", { name: "Business Composition" });
  await composition.getByText(/Explore Primary Business Types/).click();
  await composition.getByLabel("Search Business Type").fill(type);
  await composition.locator("tbody tr").filter({ hasText: type }).first().getByRole("link", { name: "View Matching Accounts" }).click();
  await page.getByText(/More Filters/).click();
  await expect(page.getByLabel("Primary business type")).toHaveValue(type);
  await page.locator("tbody tr").first().getByRole("link", { name: /^Open / }).click();
  await page.getByRole("link", { name: "Back to Filtered Accounts" }).click();
  await page.getByRole("link", { name: "Back to Business Composition" }).click();
  await expect(composition.getByLabel("Search Business Type")).toHaveValue(type);
  await expect(composition.getByLabel("Search Business Type")).toBeVisible();
  await expect(page).toHaveURL(/primary_business_type=/);
  await composition.getByText("Select a category by name").click();
  await composition.getByLabel("Business category selection").selectOption("Healthcare & Pharmaceuticals");
  expect(new URL(page.url()).searchParams.get("primary_business_type")).toBeNull();
  await expect(composition.getByLabel("Search Business Type")).toHaveValue("");
});

test("RFM and settlement keep their distributions and restore their own matching context", async ({ page }) => {
  await page.goto("/reports?tab=account-insights");
  const chart = page.getByRole("region", { name: "RFM Score Distribution" });
  await expect(chart.locator(".recharts-bar-rectangle").first()).toBeVisible();
  const bars = await chart.locator(".recharts-bar-rectangle").count();
  await page.getByLabel("RFM component", { exact: true }).selectOption("Frequency");
  await page.getByLabel("RFM component score").selectOption("5");
  await expect(chart.locator(".recharts-bar-rectangle")).toHaveCount(bars);
  await page.getByRole("link", { name: "View accounts matching RFM selection" }).click();
  await expect(page.locator("tbody tr").first()).toBeVisible();
  await page.getByRole("link", { name: "Back to RFM Distribution" }).click();
  await expect(page).toHaveURL(/\/reports\?tab=account-insights&section=rfm-distribution/);
  await expect(page.getByLabel("RFM component", { exact: true })).toHaveValue("Frequency");
  await expect(page.getByLabel("RFM component score")).toHaveValue("5");
  await expect(chart).toBeFocused();
  await page.getByLabel("Average settlement days", { exact: true }).selectOption("30-<60");
  await page.getByRole("link", { name: "View accounts matching settlement selection" }).click();
  await expect(page).toHaveURL(/\/accounts\?/);
  const query = new URL(page.url()).searchParams;
  expect(query.get("settlement_range")).toBe("30-<60");
  expect(query.get("rfm_score")).toBeNull();
  await page.getByRole("link", { name: "Back to Settlement Distribution" }).click();
  await expect(page).toHaveURL(/\/reports\?tab=account-insights&section=settlement-distribution/);
  await expect(page.getByLabel("Average settlement days", { exact: true })).toHaveValue("30-<60");
  await expect(page.getByRole("region", { name: "Historical Settlement Duration Distribution" })).toBeFocused();
  await page.getByRole("link", { name: "Account Prioritization", exact: true }).click();
  await page.getByRole("link", { name: "Detailed Analytics", exact: true }).click();
  await expect(page.getByLabel("RFM component score")).toHaveValue("5");
  await expect(page.getByLabel("Average settlement days", { exact: true })).toHaveValue("30-<60");
  await page.getByRole("tab", { name: "Management Overview" }).click();
  await page.getByLabel("Priority group", { exact: true }).selectOption("High");
  await page.getByRole("link", { name: "Review selected Priority Group" }).click();
  await expect(page).toHaveURL(/\/accounts\?/);
  const overviewQuery = new URL(page.url()).searchParams;
  expect(overviewQuery.get("priority_group")).toBe("High");
  expect(overviewQuery.has("rfm_score")).toBe(false);
  expect(overviewQuery.has("settlement_range")).toBe(false);
  expect(new URL(overviewQuery.get("returnTo")!, "http://localhost").searchParams.get("rfm_score")).toBe("5");
});

test("essential validation is visible, unsafe context is rejected, and layouts fit four widths", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  for (const width of [1440, 1366, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/reports?tab=analytics-validation&section=validation-findings");
    await expect(page.getByRole("heading", { name: "Historical classifier finding" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Official priority method versus a Recency-only rule" })).toBeVisible();
    await expect(page.getByRole("region", { name: "FPS and recency-only comparison" })).toContainText("4.39x");
    await expect(page.getByRole("region", { name: "FPS and recency-only comparison" })).toContainText("4.92x");
    const bootstrap = page.getByRole("region", { name: "Bootstrap uncertainty for historical group differences" });
    await expect(bootstrap).toBeVisible();
    await expect(bootstrap.locator("tbody tr")).toHaveCount(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(width + "-validation-visible.png") });
    await page.goto("/reports?tab=account-insights&section=business-composition&business_category=Construction%20%26%20Engineering&priority_group=High");
    await expect(page.getByRole("button", { name: "Select High Priority" })).toHaveAttribute("aria-pressed", "true");
    const bars = page.getByRole("region", { name: "Business Composition" }).locator(".recharts-bar-rectangle");
    await expect.poll(() => bars.evaluateAll(elements => elements.length > 0 && elements.every(element => {
      const box = element.getBoundingClientRect(); return box.height >= 12 && box.width > 0;
    }))).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(width + "-composition-return.png") });
  }
  await page.goto("/reports?tab=bad&section=bad");
  await expect(page.getByRole("tab", { name: "Management Overview" })).toHaveAttribute("aria-selected", "true");
  await page.goto("/accounts?returnTo=https%3A%2F%2Fevil.example");
  await expect(page.getByRole("navigation", { name: "Return to originating insight" })).toHaveCount(0);
  await page.goto("/accounts?unknown_filter=bad");
  await expect(page.getByText(/unsupported account filter/)).toBeVisible();
  expect(errors).toEqual([]);
});

test("touch explanations and keyboard tabs are usable without nested interactive links", async ({ browser, request }) => {
  const data = await (await request.get("http://127.0.0.1:8021/accounts?eligibility=ranked&page_size=1")).json();
  const context = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 }, baseURL: "http://127.0.0.1:3021" });
  try {
    const page = await context.newPage();
    await page.addInitScript(() => sessionStorage.setItem("peslc-demo-session", "administrator"));
    await page.goto("/accounts");
    const value = page.locator("tbody tr").first().getByRole("button", { name: data.items[0].final_priority_score.toFixed(4), exact: true });
    await value.tap();
    const explanation = page.getByRole("tooltip").filter({ hasText: "Final Priority Score" });
    await expect(explanation).toBeVisible();
    await explanation.getByText("Saved values for this result").tap();
    await expect(explanation).toContainText("Recency:");
    const box = (await explanation.boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(390);
    expect(box.y + box.height).toBeLessThanOrEqual(844);
    await page.getByRole("heading", { level: 1 }).tap();
    await expect(explanation).toHaveCount(0);
    await page.goto("/reports");
    const tab = page.getByRole("tab", { name: "Management Overview" });
    await tab.focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("tab", { name: "Account & Prioritization Insights" })).toBeFocused();
    await page.keyboard.press("End");
    await expect(page.getByRole("tab", { name: "Analytics Validation" })).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("a button, a [role='button'], button button")).toHaveCount(0);
  } finally { await context.close(); }
});
