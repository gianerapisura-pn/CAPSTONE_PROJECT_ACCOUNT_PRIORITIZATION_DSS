/* Authenticated, read-only UI checks. Sessions arrive through stdin, never files/logs. */
const { chromium, expect: baseExpect } = require('../frontend/node_modules/@playwright/test');
const fs = require('node:fs');
const expect = baseExpect.configure({ timeout: 60000 });
let input = ''; process.stdin.setEncoding('utf8'); process.stdin.on('data', s => input += s);
process.stdin.on('end', async () => {
  const config = JSON.parse(input); const results = [];
  const browser = await chromium.launch({ headless: true });
  try {
    for (const role of ['administrator', 'management']) for (const width of [1366, 390]) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      const errors = []; const network = []; const page = await context.newPage(); page.setDefaultTimeout(45000);
      page.on('response', r => { if (r.url().includes('/auth/') || r.url().includes('/api/')) network.push({ path: new URL(r.url()).pathname, status: r.status() }); });
      page.on('requestfailed', r => network.push({ path: new URL(r.url()).pathname, failure: r.failure()?.errorText }));
      page.on('pageerror', e => errors.push(e.message));
      await context.addInitScript(({ ref, session }) => localStorage.setItem(`sb-${ref}-auth-token`, JSON.stringify(session)),
        { ref: config.ref, session: config.sessions[role] });
      await page.goto(config.origin + '/reports?tab=management-overview', { waitUntil: 'domcontentloaded', timeout: 120000 });
      const report = page.getByRole('region', { name: 'Historical sales comparison' });
      try { await expect(report.getByRole('heading', { name: 'What changed between complete years?' })).toBeVisible(); }
      catch (error) { await page.screenshot({ path: `${config.output}/failure-${config.environment}-${role}-${width}.png`, fullPage: true });
        fs.writeFileSync(`${config.output}/failure-page-${config.environment}.json`, JSON.stringify({ url: page.url(), text: (await page.locator('body').innerText()).slice(0,3500), errors, network }, null, 2)); throw error; }
      await expect(report.getByLabel('Comparison years')).toBeVisible();
      await report.getByLabel('Comparison years').selectOption('2024:2025');
      await expect(report).toContainText('12,146,363.69');
      await expect(report.getByRole('img', { name: /Sales bridge from 2024 to 2025/ })).toBeVisible();
      await report.getByLabel('Purchasing group').selectOption('Previous year only');
      await expect(report.getByRole('link', { name: 'MEGAWORLD CORPORATION', exact: true })).toBeVisible();
      await expect(report).toContainText('Showing 1-8 of 8');
      await report.getByLabel('Comparison years').selectOption('2023:2024');
      await expect(report).toContainText('824,900.55');
      await report.getByLabel('Comparison years').selectOption('2024:2025');
      await report.getByLabel('Purchasing group').selectOption('Previous year only');
      await report.scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${config.output}/${role}-${width}-sales-change.png`, fullPage: true });
      // Wide tables scroll within their container; the page itself must stay within the viewport.
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2);
      expect(overflow).toBe(false); expect(errors).toEqual([]);
      results.push({ role, width, result: 'PASS', errors, page_overflow: overflow });
      await context.close();
    }
    fs.writeFileSync(`${config.output}/browser-${config.environment}.json`, JSON.stringify({ environment: config.environment, origin: config.origin, results }, null, 2));
    console.log(JSON.stringify({ result: 'PASS', groups: results.length }));
  } catch (error) {
    fs.writeFileSync(`${config.output}/browser-${config.environment}-failure.json`, JSON.stringify({ results, error: String(error) }, null, 2));
    console.error(String(error)); process.exitCode = 1;
  } finally { await browser.close(); }
});
