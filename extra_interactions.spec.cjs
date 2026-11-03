// Read-only EXTRA PESLC production QA, tested browser source from main.
// No POST/PATCH, no imports, no PII written to runner logs or artifacts.
const { test, expect } = require('@playwright/test');

async function signIn(page) {
  const email = process.env.PESLC_QA_EMAIL;
  const password = process.env.PESLC_QA_PASSWORD;
  if (!email || !password) throw new Error('Existing GitHub Actions QA secrets are required.');
  await page.goto('/login?next=%2Freports');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/(?:reports|dashboard)(?:\?|$)/, { timeout: 45000 });
}

async function overviewData(page) {
  const responseWait = page.waitForResponse(
    r => r.url().includes('/reports/native/overview') && r.request().method() === 'GET' && r.status() === 200,
    { timeout: 45000 }
  );
  await page.goto('/reports');
  return (await responseWait).json();
}

test('category and predicted-class filters retain saved ranked population', async ({ page }) => {
  await signIn(page);
  const overview = await overviewData(page);
  const members = overview.accounts ?? [];
  const candidate = members.find(x => x.is_ranked && x.business_category && x.predicted_future_transaction_class);
  expect(candidate, 'No eligible source-derived filter combination').toBeTruthy();
  const count = (rows) => rows.filter(x => x.is_ranked).length;
  const byCategory = count(members.filter(x => x.business_category === candidate.business_category));
  await page.getByRole('combobox', { name: 'Business category' }).selectOption(candidate.business_category);
  await expect(page.locator('.report-facts > div').filter({ hasText: 'Ranked in view' }).locator('strong'))
    .toHaveText(String(byCategory));
  const byBoth = count(members.filter(x => x.business_category === candidate.business_category &&
    x.predicted_future_transaction_class === candidate.predicted_future_transaction_class));
  await page.getByRole('combobox', { name: 'Operational 12-month SI class' })
    .selectOption(candidate.predicted_future_transaction_class);
  await expect(page.locator('.report-facts > div').filter({ hasText: 'Ranked in view' }).locator('strong'))
    .toHaveText(String(byBoth));
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page.locator('.report-facts > div').filter({ hasText: 'Ranked in view' }).locator('strong'))
    .toHaveText(String(count(members)));
});

test('tab keyboard navigation and account-insights filter controls', async ({ page }) => {
  await signIn(page);
  await overviewData(page);
  const overviewTab = page.getByRole('tab', { name: 'Management Overview', exact: true });
  await overviewTab.focus();
  await page.keyboard.press('ArrowRight');
  const insightsTab = page.getByRole('tab', { name: 'Account & Prioritization Insights', exact: true });
  await expect(insightsTab).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('heading', { name: 'RFM Score Distribution' })).toBeVisible();
  await page.getByRole('combobox', { name: 'RFM component' }).selectOption('Recency');
  await page.getByRole('combobox', { name: 'RFM component score' }).selectOption('5');
  await expect(page.getByRole('link', { name: 'View accounts matching RFM selection' }))
    .toHaveAttribute('href', /rfm_score=5/);
  await page.getByRole('combobox', { name: 'Average settlement days' }).selectOption('Below 30');
  await expect(page.getByRole('heading', { name: 'Historical Settlement Duration Distribution' })).toBeVisible();
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await insightsTab.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Analytics Validation', exact: true }))
    .toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('heading', { name: 'Predictive Validation' })).toBeVisible();
});

test('priority-chart hover exposes meaningful tooltip', async ({ page }) => {
  await signIn(page);
  await overviewData(page);
  const chart = page.locator('section.native-chart[aria-label="Priority Group Counts"]');
  await expect(chart).toBeVisible();
  const bar = chart.locator('.recharts-rectangle').first();
  await expect(bar).toBeVisible();
  await bar.hover();
  await expect(chart.getByRole('tooltip')).toBeVisible({ timeout: 8000 });
  await expect(chart.getByRole('tooltip')).toContainText('accounts');
});
