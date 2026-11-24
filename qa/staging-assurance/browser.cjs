// Credentials arrive through stdin and are never written to the result files.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { chromium, expect: baseExpect } = createRequire(path.resolve(__dirname, '../../frontend/package.json'))('@playwright/test');
const expect = baseExpect.configure({ timeout: 60000 });
const cfg = JSON.parse(fs.readFileSync(0, 'utf8'));
const report = { scope: 'Current frontend against isolated staging API and database', result: 'NOT COMPLETED', checks: [], errors: [] };
const save = () => fs.writeFileSync(path.join(cfg.output, 'browser-results.json'), JSON.stringify(report, null, 2));
const check = name => { report.checks.push({ name, result: 'PASS' }); save(); };

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const [role, session] of Object.entries(cfg.sessions)) {
      const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
      const failures = [];
      await context.addInitScript(({ origin, ref, session }) => {
        if (location.origin === origin) localStorage.setItem('sb-' + ref + '-auth-token', JSON.stringify(session));
      }, { origin: cfg.origin, ref: cfg.ref, session });
      await context.route(/ocroshaikrfzvwtpbqzs|peslc-dss-academic-web\.vercel\.app/, route => {
        failures.push('Unexpected production request'); return route.abort();
      });
      const page = await context.newPage();
      page.setDefaultNavigationTimeout(120000);
      page.on('pageerror', e => report.errors.push(e.message));
      const ready = async () => {
        await expect(page.locator('main.main')).toBeVisible();
        await expect(page.getByText('Loading current DSS data', { exact: true })).toHaveCount(0);
        await expect(page.locator('main.main .state-panel.error-state')).toHaveCount(0);
      };
      await page.goto(cfg.origin + '/accounts', { waitUntil: 'domcontentloaded' }); await ready();
      const search = page.getByRole('textbox', { name: 'Search accounts' });
      await search.fill('QA ONLY ASSURANCE 20261124');
      await expect(page.getByText(/of 40$/)).toBeVisible();
      await page.getByRole('button', { name: 'Next page', exact: true }).click();
      await expect(page.getByText(/^Page 2 of \d+$/)).toBeVisible();
      await page.getByRole('button', { name: 'Previous page', exact: true }).click();
      for (const format of ['CSV', 'XLSX']) {
        const download = page.waitForEvent('download');
        await page.getByRole('button', { name: format, exact: true }).click();
        const file = await download; expect(await file.failure()).toBeNull();
      }
      await search.fill('NO_MATCH_ASSURANCE_20261124');
      await expect(page.getByText(/of 0$/)).toBeVisible();
      await page.getByRole('button', { name: 'Reset', exact: true }).click();
      await expect(search).toHaveValue('');
      check(role + ' account search, pagination, CSV/XLSX download, no-result state and reset');
      await page.goto(cfg.origin + '/accounts/' + cfg.account, { waitUntil: 'domcontentloaded' }); await ready();
      await expect(page.locator('main.main h1')).toContainText('QA ONLY ASSURANCE');
      check(role + ' new synthetic account detail');
      await page.goto(cfg.origin + '/reports', { waitUntil: 'domcontentloaded' }); await ready();
      for (const view of ['Management Overview', 'Account & Prioritization Insights', 'Analytics Validation']) {
        await page.getByRole('tab', { name: view, exact: true }).click(); await ready();
        await expect(page.getByRole('tabpanel', { name: view, exact: true })).toBeVisible();
        await expect(page.locator('.report-meta')).toContainText('2026-11-24');
        await expect(page.locator('.recharts-surface').first()).toBeVisible();
        await page.getByRole('button', { name: 'Refresh reports', exact: true }).click(); await ready();
        const values = page.locator('#report-panel .explained-value');
        let expanded = false;
        for (let i = 0; i < Math.min(await values.count(), 18); i++) {
          await values.nth(i).click();
          const tooltip = page.getByRole('tooltip');
          await expect(tooltip).toBeVisible();
          const summary = tooltip.locator('summary').filter({ hasText: 'Definition and calculation' });
          if (await summary.count()) {
            await summary.click();
            await expect(tooltip).toBeVisible(); await expect(summary.locator('..')).toHaveAttribute('open', '');
            expect((await tooltip.innerText()).length).toBeGreaterThan(40);
            expanded = true;
          }
          await page.keyboard.press('Escape');
          if (expanded) break;
        }
        expect(expanded).toBeTruthy();
        await page.screenshot({ path: path.join(cfg.output, role + '-' + view.replace(/\W+/g, '-') + '.png'), fullPage: false });
        check(role + ' ' + view + ' chart rendering, refresh and persistent definition/calculation');
      }
      await page.reload({ waitUntil: 'domcontentloaded' }); await ready();
      await expect(page.getByRole('tab', { name: 'Analytics Validation', exact: true })).toHaveAttribute('aria-selected', 'true');
      check(role + ' selected analytics tab survives reload');
      if (role === 'management') {
        await page.goto(cfg.origin + '/import', { waitUntil: 'domcontentloaded' });
        await expect(page.getByText('Administrator access required', { exact: true })).toBeVisible();
        check('Management import screen remains restricted');
      }
      expect(failures).toEqual([]); await context.close();
    }
    expect(report.errors).toEqual([]); report.result = 'PASS';
  } finally { await browser.close(); save(); }
})().catch(e => { report.result = 'FAIL'; report.error = e.message; save(); process.exitCode = 1; });
