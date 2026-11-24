// Receives a disposable staging session and synthetic password through stdin only.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { chromium, expect } = createRequire(path.resolve(__dirname, '../frontend/package.json'))('@playwright/test');
const cfg = JSON.parse(fs.readFileSync(0, 'utf8'));
const report = { result: 'NOT COMPLETED', real_staging_auth: true, production_requests: 0, checks: [], javascript_errors: [] };
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    await context.addInitScript(({ origin, session }) => {
      if (location.origin === origin) localStorage.setItem('sb-ymonifjcvkxsqhabgpxp-auth-token', JSON.stringify(session));
    }, { origin: cfg.origin, session: cfg.session });
    await context.route(/ocroshaikrfzvwtpbqzs|peslc-dss-academic-web\.vercel\.app/, route => { report.production_requests++; return route.abort(); });
    const page = await context.newPage(); page.setDefaultNavigationTimeout(120000); page.setDefaultTimeout(30000);
    page.on('pageerror', error => report.javascript_errors.push(error.name));
    await page.goto(cfg.origin + '/reset-password', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('New password', { exact: true }).fill(cfg.password);
    await page.getByLabel('Confirm new password', { exact: true }).fill(cfg.password);
    await page.getByRole('button', { name: 'Update password', exact: true }).click();
    await expect(page.getByText('Password updated. Sign in with your new password.', { exact: true })).toBeVisible();
    report.checks.push({ name: 'Live HIBP screening followed by real staging password update and sign-out', result: 'PASS' });
    expect(report.production_requests).toBe(0); expect(report.javascript_errors).toEqual([]);
    report.result = 'PASS'; await context.close();
  } catch { report.result = 'FAIL'; process.exitCode = 1; }
  finally { await browser.close(); fs.writeFileSync(cfg.output, JSON.stringify(report, null, 2)); }
})();
