import { expect, test } from "@playwright/test";
import type { AccountDecisionRow, NormalizationEvidence } from "../types/dss";

const api = "http://127.0.0.1:8021";
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("peslc-demo-session", "administrator"));
});

for (const width of [1440, 1366, 1024, 390]) {
test(`shared typography preserves readable words, row alignment, and panel bounds at ${width}px`, async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const list = await (await request.get(api + "/accounts?eligibility=ranked&page_size=1")).json();
  const routes = ["/dashboard", "/accounts/" + list.items[0].account_key,
    "/accounts", "/analytics/rfm", "/analytics/settlement", "/analytics/predictive",
    "/analytics/sensitivity", "/profile", "/runs", "/import/history", "/settings", "/import",
    "/reports?tab=management-overview", "/reports?tab=account-insights", "/reports?tab=analytics-validation"];
    await page.setViewportSize({ width, height: 900 });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByText("Reading the latest successful analytical run.")).toHaveCount(0);
      const alerts = page.locator("main").getByRole("alert");
      await expect(alerts, route + ": " + (await alerts.allTextContents()).join(" | ")).toHaveCount(0);
      if (route === "/dashboard") {
        await expect(page.locator(".compact-row")).toHaveCount(9);
        for (const link of await page.locator(".compact-row>a").all()) {
          await expect(link).toHaveCSS("display", "block");
          expect((await link.boundingBox())!.width).toBeGreaterThan(140);
        }
        const top = page.locator(".compact-row").filter({ has: page.locator(".compact-rank") }).first();
        await expect(top).toContainText(list.items[0].account);
        expect((await top.boundingBox())!.height).toBeLessThan(110);
        for (const value of await page.locator(".kpi-card strong .explained-value").all()) {
          await expect(value).toHaveCSS("font-size", "21px");
        }
        await expect(page.locator(".report-meta .explained-value").first()).toHaveCSS("padding", "0px");
        await page.screenshot({ path: test.info().outputPath(width + "-dashboard-typography.png"), fullPage: true });
      }
      if (["/accounts", "/profile", "/settings"].includes(route)) {
        await page.screenshot({ path: test.info().outputPath(width + "-" + route.slice(1) + "-panel-spacing.png"), fullPage: false });
      }
      const issues = await page.locator("main").evaluate(main => {
        const issues: string[] = [];
        if (document.documentElement.scrollWidth > innerWidth + 1) issues.push("Page exceeds viewport");
        for (const panel of main.querySelectorAll<HTMLElement>(".data-section")) {
          const panelBox = panel.getBoundingClientRect();
          for (const content of panel.querySelectorAll<HTMLElement>(":scope>.active-filters,:scope>.data-meta,:scope>.button,:scope>.page-actions,:scope>.profile-actions,:scope>.profile-form,:scope>p")) {
            const box = content.getBoundingClientRect();
            if (!box.width || !box.height) continue;
            const leftInset = box.left - panelBox.left + parseFloat(getComputedStyle(content).paddingLeft);
            const rightInset = panelBox.right - box.right + parseFloat(getComputedStyle(content).paddingRight);
            if (leftInset < 16 || rightInset < 16) issues.push("Missing panel gutter: " + content.className + " " + content.textContent);
            if (content.matches(".button") && panelBox.bottom - box.bottom < 16) issues.push("Missing action bottom gutter");
          }
        }
        for (const element of main.querySelectorAll<HTMLElement>(".compact-row strong,.compact-row small,.method-facts dt,.method-facts dd,.section-heading h2")) {
          const box = element.getBoundingClientRect();
          if (!box.width || !box.height) continue;
          if (element.scrollWidth > element.clientWidth + 1) issues.push("Overflow: " + element.textContent);
          const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
          let node: Node | null;
          while ((node = walker.nextNode())) {
            for (const match of (node.textContent ?? "").matchAll(/\b[A-Za-z]{4,24}\b/g)) {
              const range = document.createRange();
              range.setStart(node, match.index!);
              range.setEnd(node, match.index! + match[0].length);
              const lines = new Set(Array.from(range.getClientRects()).filter(rect => rect.width > 0).map(rect => Math.round(rect.y)));
              if (lines.size > 1) issues.push("Split word: " + match[0]);
            }
          }
        }
        return issues;
      });
      expect(issues, width + "px " + route).toEqual([]);
    }
  expect(errors).toEqual([]);
});
}

test("all published normalization explanations reconcile without changing official evidence", async ({ request }) => {
  const all: { items: AccountDecisionRow[]; analysis_run_id: string } = await (await request.get(api + "/accounts?eligibility=all&page_size=500")).json();
  const ranked = all.items.filter(row => row.is_ranked);
  expect(all.items).toHaveLength(84);
  expect(ranked).toHaveLength(83);
  expect(new Set(ranked.map(row => row.business_category)).size).toBe(8);
  expect(new Set(all.items.map(row => row.primary_business_type)).size).toBe(59);
  for (const [group, total] of [["High", 28], ["Medium", 27], ["Low", 28]] as const) expect(ranked.filter(row => row.priority_group === group)).toHaveLength(total);
  const paths = ["/accounts/priorities", "/reports/native/validation", "/reports/native/overview"];
  const before = [];
  for (const path of paths) before.push(await (await request.get(api + path)).text());
  for (const row of ranked) {
    const detail = await (await request.get(api + "/accounts/" + row.account_key + "?search=" + encodeURIComponent(row.account))).json();
    const evidence: NormalizationEvidence = detail.normalization;
    expect(evidence.analysis_run_id).toBe(all.analysis_run_id);
    expect(evidence.eligible_account_count).toBe(83);
    expect(detail.navigation.total).toBe(1);
    for (const [criterion, value] of Object.entries(evidence.criteria)) {
      expect(value.status).toBe("verified");
      expect(value.calculated_normalized!).toBeCloseTo(value.saved_normalized!, 12);
      expect(value.saved_normalized).toBe(row[("normalized_" + criterion) as keyof AccountDecisionRow]);
    }
  }
  for (const [index, path] of paths.entries()) expect(await (await request.get(api + path)).text()).toBe(before[index]);
  const validation = JSON.parse(before[1]);
  expect(validation.study.class_counts).toEqual({ "With Future Sales": 10, "With No Future Sales": 73 });
  expect(validation.model_artifact_hash).toBe("09e4dcb0afd228a046c853d11729301dbb86d04fea9459194e22cde1ae377fb3");
});

test("Megaworld actual normalization inputs fit accessible explanations at four widths", async ({ page, request }) => {
  const list = await (await request.get(api + "/accounts?search=MEGAWORLD&page_size=10")).json();
  const account = list.items.find((row: AccountDecisionRow) => row.account === "MEGAWORLD CORPORATION");
  for (const width of [1440, 1366, 1024, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto("/accounts/" + account.account_key);
    await page.getByText("Saved normalization, weights, and contributions", { exact: true }).click();
    for (const [criterion, result] of [["Recency", "0.8934269304"], ["Frequency", "1.0000000000"], ["Monetary", "1.0000000000"], ["Settlement", "0.8414256198"]]) {
      const value = page.locator(".account-calculations dt").filter({ hasText: "Normalized " + criterion }).locator("..").getByRole("button");
      await value.focus();
      const tooltip = page.getByRole("tooltip").filter({ hasText: "Normalized " + criterion });
      await expect(tooltip).toContainText("83 ranked accounts; reference 2025-12-31");
      await expect(tooltip).toContainText("= " + result);
      await tooltip.getByText("Saved values for this result").click();
      await expect(tooltip).toContainText("Eligible minimum:");
      await expect(tooltip).toContainText("Eligible maximum:");
      await expect(tooltip).toContainText("Saved normalized result: " + result);
      const box = (await tooltip.boundingBox())!;
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      expect(box.y).toBeGreaterThanOrEqual(0);
      expect(box.y + box.height).toBeLessThanOrEqual(width === 390 ? 844 : 900);
      expect(await tooltip.evaluate(element => element.scrollWidth <= element.clientWidth && element.scrollHeight <= element.clientHeight)).toBe(true);
      await page.screenshot({ path: test.info().outputPath(width + "-normalized-" + criterion + ".png") });
      await page.keyboard.press("Escape");
      await expect(tooltip).toHaveCount(0);
      await page.mouse.move(0, 0);
    }
  }
});

test("filtered ranks, historical context, and distinct RFM series remain clear and responsive", async ({ page, request }) => {
  const all: { items: AccountDecisionRow[] } = await (await request.get(api + "/accounts?eligibility=all&page_size=500")).json();
  const closed = all.items.find(row => !row.is_ranked)!;
  const medium = all.items.find(row => row.priority_group === "Medium")!;
  for (const width of [1440, 1366, 1024, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/reports?tab=management-overview&priority_group=Medium");
    const top = page.getByRole("region", { name: "Highest-Ranked Accounts Matching Your Filters" });
    await expect(top).toContainText("Showing 10 of 27 matching accounts");
    await expect(top).toContainText("no new ranking is calculated");
    await page.getByText("Open a top account by name").click();
    await expect(page.getByRole("link", { name: new RegExp("#" + medium.priority_rank + " " + medium.account.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) })).toBeVisible();
    const comparison = page.getByRole("region", { name: "Priority Group Counts" });
    await expect(comparison).toContainText("other groups remain visible for comparison");
    await top.screenshot({ path: test.info().outputPath(width + "-filtered-top.png") });
    const params = new URLSearchParams({ tab: "account-insights", eligibility: "not_ranked", business_category: closed.business_category! });
    await page.goto("/reports?" + params);
    const composition = page.getByRole("region", { name: "Business Composition" });
    await expect(composition.getByLabel("Historical account filter")).toContainText("chart compares 83 currently ranked accounts");
    await expect(composition.getByLabel("Historical account filter")).toContainText("1 account matches");
    await composition.getByText(/Explore Primary Business Types/).click();
    await expect(composition.locator("tbody tr")).toHaveCount(1);
    await expect(composition.locator("tbody tr")).toContainText(closed.primary_business_type!);
    await composition.screenshot({ path: test.info().outputPath(width + "-historical-context.png") });
    await composition.getByRole("link", { name: "View historical matching accounts" }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody tr")).toContainText(closed.account);
    await page.getByRole("link", { name: "Back to Business Composition" }).click();
    await expect(composition).toBeFocused();
    await page.goto("/reports?tab=account-insights");
    const rfm = page.getByRole("region", { name: "RFM Score Distribution", exact: true });
    for (const component of ["Recency score", "Frequency score", "Monetary score"]) await expect(rfm.getByText(component, { exact: true })).toBeVisible();
    await expect(rfm).toContainText("not Priority Groups");
    await expect.poll(async () => rfm.locator(".recharts-bar-rectangle path").evaluateAll(elements => [...new Set(elements.map(element => element.getAttribute("fill")))].sort())).toEqual(["#336caa", "#687d29", "#a05b85"]);
    await rfm.locator(".recharts-bar-rectangle path").first().hover();
    await expect(rfm.getByRole("tooltip")).toContainText("not High Priority membership");
    await rfm.screenshot({ path: test.info().outputPath(width + "-rfm-series.png") });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  }
});
