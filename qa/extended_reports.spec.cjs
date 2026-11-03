const { test, expect } = require('@playwright/test');
const reference = require('./report_reference.json');

// Read-only tests. Never log credentials, tokens, customer rows or API bodies.
const webUrl = process.env.PESLC_WEB_URL || 'https://peslc-dss-academic-web.vercel.app';

async function login(page, email, password) {
  if (!email || !password) throw new Error('Authorized QA credentials are not configured.');
  await page.goto('/login?next=%2Freports');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/(?:reports|dashboard)(?:\?|$)/, {timeout: 45000});
}

async function readTab(page, tab, endpoint) {
  const response = page.waitForResponse(r => r.url().includes(endpoint) && r.request().method() === 'GET' && r.status() === 200, {timeout: 45000});
  if (tab) await page.getByRole('tab', {name: tab, exact: true}).click();
  else await page.goto('/reports');
  return (await response).json();
}

async function enterReports(page) {
  await login(page, process.env.PESLC_QA_EMAIL, process.env.PESLC_QA_PASSWORD);
  await page.goto('/reports');
  await expect(page.getByRole('tab', { name: 'Management Overview' })).toBeVisible();
}

test('published Management Overview baseline and filter accuracy', async ({page}) => {
  await login(page, process.env.PESLC_QA_EMAIL, process.env.PESLC_QA_PASSWORD);
  const overview = await readTab(page, null, '/reports/native/overview');
  expect(overview.ranked_accounts).toBe(reference.ranked_accounts);
  expect(overview.b2b_analytical_accounts).toBe(reference.historical_b2b_accounts);
  const years = new Map(overview.business_baselines.map(x => [Number(x.year), x]));
  for (const row of reference.annual_baselines) {
    const actual = years.get(row.year);
    expect(actual, `Missing ${row.year} annual baseline`).toBeTruthy();
    expect(Math.abs(Number(actual.all_recorded_sales) - row.sales_php)).toBeLessThan(0.011);
    expect(Number(actual.b2b_transacting_account_count)).toBe(row.transacting_b2b);
  }
  await expect(page.getByRole('heading', {name:'Annual Valid Sales Invoice Sales'})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Yearly Transacting B2B Accounts'})).toBeVisible();
  await expect(page.getByRole('heading', {name:'Priority Group Counts'})).toBeVisible();
  // Filtering cannot alter the published underlying ranking.
  await page.getByRole('combobox', {name:'Priority group'}).selectOption('High');
  await expect(page.locator('.report-facts > div').filter({hasText:'Ranked in view'}).locator('strong')).toHaveText('28');
  await page.getByRole('button', {name:'Reset filters'}).click();
  await expect(page.locator('.report-facts > div').filter({hasText:'Ranked in view'}).locator('strong')).toHaveText('83');
});

test('insights show fixed CRITIC weights and RFM/settlement sections', async ({page}) => {
  await enterReports(page);
  const details = await readTab(page, 'Account & Prioritization Insights', '/reports/native/insights');
  expect(details.accounts.length).toBe(reference.historical_b2b_accounts);
  const weights=details.critic_weights;
  for (const [key,value] of Object.entries(reference.critic_weights)) {
    expect(Math.abs(Number(weights[key])-value), key).toBeLessThan(1e-8);
  }
  expect(Math.abs(Object.values(weights).reduce((s,v)=>s+Number(v),0)-1)).toBeLessThan(1e-9);
  await expect(page.getByRole('heading',{name:'RFM Score Distribution'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Historical Settlement Duration Distribution'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Published CRITIC Criterion Weights'})).toBeVisible();
});

test('validation shows frozen CatBoost study and scenario counts', async ({page}) => {
  await enterReports(page);
  const data=await readTab(page, 'Analytics Validation', '/reports/native/validation');
  expect(data.ranked_account_count).toBe(reference.ranked_accounts);
  expect(data.study.class_counts['With Future Sales']).toBe(reference.study_with_future_sales);
  expect(data.study.class_counts['With No Future Sales']).toBe(reference.study_with_no_future_sales);
  expect(data.sensitivity.reduce((s,v)=>s+Number(v.iterations),0)).toBe(reference.sensitivity_iterations);
  expect(data.scenario_detail_count).toBe(reference.sensitivity_account_scenarios);
  expect(data.backtest.cutoffs.length).toBe(reference.backtest_cutoffs);
  expect(data.study.forecast_origin).toBe(reference.analysis_reference_date);
  await expect(page.getByRole('heading',{name:'Predictive Validation'})).toBeVisible();
});

test('real management token denies administrator-only read APIs', async ({page, request}) => {
  const email=process.env.PESLC_MANAGEMENT_QA_EMAIL;
  const password=process.env.PESLC_MANAGEMENT_QA_PASSWORD;
  test.skip(!email || !password, 'Authorized management QA credentials absent; never substitute admin credentials.');
  await login(page, email, password);
  const capture=page.waitForRequest(req=>req.url().includes('/reports/native/overview') && req.method()==='GET',{timeout:45000});
  await page.goto('/reports');
  const authenticatedReq=await capture;
  const authorization=authenticatedReq.headers()['authorization'];
  expect(authorization?.toLowerCase().startsWith('bearer ')).toBe(true);
  const base=new URL(authenticatedReq.url());
  const prefix=base.pathname.slice(0,base.pathname.indexOf('/reports/native/overview'));
  const url=(path)=>base.origin+prefix+path;
  const headers={authorization};
  const allowed=await request.get(url('/reports/native/overview'), {headers});
  expect(allowed.status()).toBe(200);
  // GET-only endpoints: no state mutation, and tokens never appear in logs.
  for (const restricted of ['/imports','/audit-log','/models/current','/analytics/runs']) {
    const response=await request.get(url(restricted),{headers});
    expect(response.status(), `${restricted} should be forbidden to management`).toBe(403);
  }
});
