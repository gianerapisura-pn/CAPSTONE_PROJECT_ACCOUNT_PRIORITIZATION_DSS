const { test, expect } = require('@playwright/test');

for (const role of ['management', 'administrator']) {
  test(`production ${role} descriptive export visibility preserves analytical tables`, async ({ page }) => {
    const email = process.env[role === 'management' ? 'PESLC_MANAGEMENT_QA_EMAIL' : 'PESLC_QA_EMAIL'];
    const password = process.env[role === 'management' ? 'PESLC_MANAGEMENT_QA_PASSWORD' : 'PESLC_QA_PASSWORD'];
    if (!email || !password) throw new Error(`Existing authorized ${role} QA credentials required`);
    await page.goto('/login?next=%2Fdashboard');
    await page.locator('input[type=email]').fill(email);
    await page.locator('input[type=password]').fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, {timeout: 45000});
    for (const route of ['/analytics/rfm', '/analytics/settlement']) {
      await page.goto(route);
      await expect(page.getByRole('table')).toBeVisible();
      await expect(page.locator('tbody tr')).toHaveCount(10);
      await expect(page.getByText('Table order: Account Name (A-Z). This is not a ranking.')).toBeVisible();
      const button = page.getByRole('button', {name: 'Export', exact: true});
      if (role === 'management') await expect(button).toHaveCount(0);
      else await expect(button).toBeVisible();
      console.log(JSON.stringify({environment: 'production', role, route, export_visible: role === 'administrator', table_rows: 10}));
    }
  });
}
