const { test, expect } = require('@playwright/test');
const { statSync, readFileSync } = require('node:fs');

// Never print tokens, customer names, exports, or response bodies in public logs.
const email = process.env.PESLC_QA_EMAIL;
const password = process.env.PESLC_QA_PASSWORD;

async function signIn(page) {
  if (!email || !password) throw new Error('PESLC_QA_EMAIL and PESLC_QA_PASSWORD secrets are required.');
  await page.goto('/login?next=%2Fdashboard');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 45_000 });
}

test('anonymous visitor cannot open protected account list', async ({ page }) => {
  await page.goto('/accounts');
  await expect(page).toHaveURL(/\/login(?:\?|$)/, { timeout: 30_000 });
});

test('approved administrator can view saved list and three reporting tabs', async ({ page }) => {
  await signIn(page);
  const started = Date.now();
  await page.goto('/accounts');
  await expect(page.getByLabel('Search accounts')).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Final Priority Score' })).toBeVisible();
  await expect.poll(async () => page.locator('table.decision-table tbody tr').count()).toBeGreaterThan(0);
  console.log(`qa_read_only_account_list_ms=${Date.now() - started}`);
  await page.goto('/reports');
  await expect(page.getByRole('heading', { name: 'Detailed Analytics', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Annual Valid Sales Invoice Sales' })).toBeVisible();
  await page.getByRole('tab', { name: 'Account & Prioritization Insights' }).click();
  await expect(page.getByRole('heading', { name: 'RFM Score Distribution' })).toBeVisible();
  await page.getByRole('tab', { name: 'Analytics Validation' }).click();
  await expect(page.getByText('Model selection and historical classification evidence')).toBeVisible();
});

for (const format of ['csv', 'xlsx']) {
  test(`approved administrator can download ${format.toUpperCase()} output`, async ({ page }) => {
    await signIn(page);
    await page.goto('/reports');
    await expect(page.getByRole('heading', { name: 'Account Prioritization export' })).toBeVisible();
    const pending = page.waitForEvent('download', { timeout: 45_000 });
    await page.getByRole('button', { name: format.toUpperCase(), exact: true }).click();
    const download = await pending;
    const localPath = await download.path();
    const size = statSync(localPath).size;
    expect(size).toBeGreaterThan(50);
    if (format === 'xlsx') {
      expect(readFileSync(localPath).subarray(0, 2).toString()).toBe('PK');
    } else {
      const head = readFileSync(localPath).subarray(0, 100).toString('utf8');
      expect(head).toContain(',');
    }
    console.log(`qa_${format}_download_bytes=${size}`);
    // Files remain on ephemeral runner only; do not upload public artifacts.
  });
}
