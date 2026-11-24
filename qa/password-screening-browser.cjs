// Synthetic password-reset integration. Auth updates are intercepted, never sent.
const { createRequire } = require('node:module');
const path = require('node:path');
const fs = require('node:fs');
const { chromium, expect } = createRequire(path.resolve(__dirname, '../frontend/package.json'))('@playwright/test');
const origin = process.argv[2];
const output = process.argv[3];
const report = { result: 'NOT COMPLETED', scope: 'Reset UI with intercepted synthetic Auth; live HIBP range lookup', checks: [], auth_updates_sent: 0, javascript_errors: [] };
const record = name => report.checks.push({ name, result: 'PASS' });
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    for (const mode of ['breached', 'unavailable', 'clean', 'live-breached']) {
      const context = await browser.newContext();
      const user = { id: '00000000-0000-4000-8000-000000000099', email: 'synthetic@example.invalid', aud: 'authenticated', role: 'authenticated', app_metadata: {}, user_metadata: {} };
      await context.addInitScript(({ origin, user }) => {
        if (location.origin !== origin) return;
        for (const ref of ['ocroshaikrfzvwtpbqzs', 'ymonifjcvkxsqhabgpxp']) {
          localStorage.setItem('sb-' + ref + '-auth-token', JSON.stringify({ access_token: 'synthetic.integration.token', refresh_token: 'synthetic-only', expires_in: 3600, expires_at: Math.floor(Date.now()/1000)+3600, token_type: 'bearer', user }));
        }
      }, { origin, user });
      let updates = 0; let lookups = 0;
      await context.route(/supabase\.co\//, async route => {
        if (route.request().method() === 'PUT' && new URL(route.request().url()).pathname === '/auth/v1/user') updates++;
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
      });
      await context.route('https://api.pwnedpasswords.com/range/*', async route => {
        lookups++;
        const request = route.request();
        expect(new URL(request.url()).pathname).toMatch(/^\/range\/[A-F0-9]{5}$/);
        expect(request.postData()).toBeNull();
        if (mode === 'live-breached') { await route.continue(); return; }
        if (mode === 'unavailable') { await route.fulfill({ status: 503, body: 'Unavailable' }); return; }
        // SHA-1 suffix for the public synthetic example 'passwordpassword'.
        const { createHash } = require('node:crypto');
        const suffix = createHash('sha1').update('passwordpassword').digest('hex').toUpperCase().slice(5);
        await route.fulfill({ status: 200, contentType: 'text/plain', body: mode === 'breached' ? suffix + ':123' : 'A'.repeat(35) + ':1' });
      });
      const page = await context.newPage(); page.setDefaultNavigationTimeout(120000); page.setDefaultTimeout(30000); page.on('pageerror', e => report.javascript_errors.push(e.message));
      await page.goto(origin + '/reset-password', { waitUntil: 'domcontentloaded' });
      await page.getByLabel('New password', { exact: true }).fill('passwordpassword');
      await page.getByLabel('Confirm new password', { exact: true }).fill('passwordpassword');
      expect(lookups).toBe(0);
      await page.getByRole('button', { name: 'Update password', exact: true }).click();
      if (mode === 'clean') {
        await expect(page.getByText('Password updated. Sign in with your new password.', { exact: true })).toBeVisible();
        expect(updates).toBe(1);
      } else {
        await expect(page.getByText(mode === 'unavailable' ? /password safety check is unavailable/ : /appears in known data breaches/)).toBeVisible({ timeout: 15000 });
        expect(updates).toBe(0);
      }
      expect(lookups).toBe(1); record(mode + ' reset workflow');
      await context.close();
    }
    expect(report.javascript_errors).toEqual([]); report.result = 'PASS';
  } catch (error) { report.result = 'FAIL'; report.error = error.message; process.exitCode = 1; }
  finally { await browser.close(); fs.writeFileSync(output, JSON.stringify(report, null, 2)); }
})();
