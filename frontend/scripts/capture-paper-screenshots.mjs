import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";

const base = process.env.PESLC_CAPTURE_URL ?? "http://127.0.0.1:3000";
const capturedAtUtc = new Date().toISOString();
const output = path.resolve("test-results", `peslc-paper-screenshots-${capturedAtUtc.replace(/[:.]/g, "-")}`);
let gitCommit = null;
try { gitCommit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: path.resolve(".."), encoding: "utf8" }).trim() || null; }
catch { /* A capture outside a Git checkout has no verifiable commit. */ }
const routes = [
  ["01-overview", "/dashboard"],
  ["02-account-prioritization", "/accounts"],
  ["03-detailed-analytics-management", "/reports"],
  ["04-detailed-analytics-account-insights", "/reports", "Account & Prioritization Insights"],
  ["05-detailed-analytics-validation", "/reports", "Analytics Validation"],
  ["06-import-data", "/import"],
  ["07-import-history", "/import/history"],
  ["08-analytics-runs", "/runs"],
  ["09-methodology-governance", "/settings"],
  ["10-rfm", "/analytics/rfm"],
  ["11-settlement", "/analytics/settlement"],
  ["12-predictive", "/analytics/predictive"],
  ["13-sensitivity", "/analytics/sensitivity"],
];

await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const manifest = [];
const metadata = { capturedAtUtc, gitCommit, analysisRunId: null, analysisReferenceDate: null, environment: "unverified" };
page.on("response", async response => {
  if (!response.ok() || !/\/reports\/native\/(overview|insights|validation)$/.test(new URL(response.url()).pathname)) return;
  try {
    const run = (await response.json()).run;
    if (run?.analysis_run_id && run?.analysis_reference_date) {
      metadata.analysisRunId = run.analysis_run_id;
      metadata.analysisReferenceDate = run.analysis_reference_date;
    }
  } catch { /* Keep unavailable run metadata null. */ }
});

async function capture(name, route, tab) {
  await page.goto(`${base}${route}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (route !== "/login") {
    await page.locator(".page-stack, .account-hero").first().waitFor({ timeout: 30000 });
    await page.locator(".auth-loading").waitFor({ state: "hidden", timeout: 30000 });
    if (route.startsWith("/accounts/")) await page.locator(".account-hero").waitFor({ timeout: 60000 });
  }
  if (tab) await page.getByRole("tab", { name: tab }).click();
  await page.waitForTimeout(1300);
  await page.evaluate(async () => {
    for (const image of document.images) if (!image.complete) await image.decode().catch(() => {});
  });
  const heading = await page.locator("h1").first().textContent().catch(() => "");
  const error = (await page.locator(".error-state, [role=alert]").allTextContents()).map(value => value.trim()).filter(Boolean);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const step = 790;
  const parts = Math.max(1, Math.ceil(Math.max(0, height - 900) / step) + 1);
  const files = [];
  for (let index = 0; index < parts; index++) {
    const position = Math.min(index * step, Math.max(0, height - 900));
    await page.evaluate(y => window.scrollTo(0, y), position);
    await page.waitForTimeout(140);
    const file = `${name}-${String(index + 1).padStart(2, "0")}.png`;
    await page.screenshot({ path: path.join(output, file), animations: "disabled" });
    files.push(file);
  }
  manifest.push({ name, route, tab: tab ?? null, heading: heading?.trim(), height, files, errors: error });
  console.log(`${name}: ${files.length} screenshots, heading=${heading?.trim() || "none"}, errors=${error.length}`);
}

try {
  await capture("00-sign-in", "/login");
  await page.getByRole("button", { name: /Enter isolated demo workspace/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });
  if (await page.getByText(/DEMO ENVIRONMENT/i).count()) metadata.environment = "isolated demo";
  for (const [name, route, tab] of routes) await capture(name, route, tab);

  await page.goto(`${base}/accounts`);
  await page.locator(".page-stack").waitFor();
  await page.waitForTimeout(1200);
  const accountLink = await page.locator('a[href^="/accounts/"]').first().getAttribute("href");
  if (accountLink) await capture("14-account-detail", accountLink);

  await page.goto(`${base}/reports`);
  await page.getByRole("tab", { name: "Account & Prioritization Insights" }).click();
  await page.waitForTimeout(1300);
  await page.addStyleTag({ content: ".topbar { position: static !important; }" });
  for (const [name, title] of [
    ["15-business-category-chart", "Priority Groups by Business Category"],
    ["16-primary-business-type-chart", "Priority Groups by Primary Business Type"],
  ]) {
    const chart = page.getByRole("region", { name: title }).first();
    const target = await chart.count() ? chart : page.locator("section.native-group-explorer").filter({ has: page.getByRole("heading", { name: title }) });
    await target.scrollIntoViewIfNeeded();
    await page.mouse.move(10, 10);
    await page.waitForTimeout(180);
    const file = `${name}.png`;
    await target.screenshot({ path: path.join(output, file), animations: "disabled" });
    manifest.push({ name, route: "/reports", tab: "Account & Prioritization Insights", files: [file] });
    console.log(`${name}: 1 focused screenshot`);
  }

  await page.getByRole("button", { name: "Next account page" }).click();
  const accountTable = page.locator("section.native-table-section").first();
  await accountTable.scrollIntoViewIfNeeded();
  await page.mouse.move(10, 10);
  await accountTable.screenshot({ path: path.join(output, "17-b2b-account-table-page-2.png"), animations: "disabled" });
  manifest.push({ name: "17-b2b-account-table-page-2", route: "/reports", tab: "Account & Prioritization Insights", files: ["17-b2b-account-table-page-2.png"] });

  await page.getByRole("tab", { name: "Analytics Validation" }).click();
  await page.waitForTimeout(900);
  const expandable = page.locator("details.native-evidence-details");
  const expandedFiles = [];
  for (let index = 0; index < await expandable.count(); index++) {
    const item = expandable.nth(index);
    const title = (await item.locator("summary").textContent())?.trim() ?? `Evidence ${index + 1}`;
    await item.locator("summary").click();
    await item.scrollIntoViewIfNeeded();
    await page.mouse.move(10, 10);
    const file = `18-validation-expanded-${String(index + 1).padStart(2, "0")}.png`;
    await item.screenshot({ path: path.join(output, file), animations: "disabled" });
    expandedFiles.push({ title, file });
    await item.locator("summary").click();
  }
  manifest.push({ name: "18-validation-expanded-evidence", route: "/reports", tab: "Analytics Validation", sections: expandedFiles, files: expandedFiles.map(item => item.file) });
  console.log(`18-validation-expanded-evidence: ${expandedFiles.length} screenshots`);

  await writeFile(path.join(output, "MANIFEST.json"), JSON.stringify({ metadata, screenshots: manifest }, null, 2));
  await writeFile(path.join(output, "README.txt"),
    `PESLC DSS screenshots captured ${capturedAtUtc}.\n` +
    `Source URL: ${base}. Environment: ${metadata.environment}.\n` +
    "The capture does not establish live Supabase deployment or source-package verification.\n" +
    "Numbered PNGs follow page scroll order; later files show focused charts, table pagination, and expanded evidence.\n" +
    "See MANIFEST.json for observed run metadata, routes, tabs, screenshot lists, and capture errors.\n");
} finally {
  await browser.close();
}
