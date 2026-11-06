// Non-mutating production authorization probes. Every body is deliberately
// incomplete: even an administrator reaches validation (422), never a write.
// The retired refresh handler only returns 410. No upload or valid entity ID.
const { test, expect } = require('@playwright/test');
const crypto = require('node:crypto');

const routes = require('./production_denial_probes.json');

async function session(page, role) {
  const email = process.env[role === 'management' ? 'PESLC_MANAGEMENT_QA_EMAIL' : 'PESLC_QA_EMAIL'];
  const password = process.env[role === 'management' ? 'PESLC_MANAGEMENT_QA_PASSWORD' : 'PESLC_QA_PASSWORD'];
  if (!email || !password) throw new Error(`Authorized ${role} QA credentials are required`);
  await page.goto('/login?next=%2Fdashboard');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard(?:\?|$)/, { timeout: 45000 });
  const capture = page.waitForRequest(r => r.url().includes('/reports/native/overview') && r.method() === 'GET');
  await page.goto('/reports');
  const authenticated = await capture;
  const authorization = authenticated.headers()['authorization'];
  expect(authorization?.toLowerCase().startsWith('bearer ')).toBe(true);
  const endpoint = new URL(authenticated.url());
  const prefix = endpoint.pathname.slice(0, endpoint.pathname.indexOf('/reports/native/overview'));
  return { headers: { authorization }, url: path => endpoint.origin + prefix + path };
}

async function publishedFingerprint(request, auth) {
  const response = await request.get(auth.url('/reports/native/overview'), { headers: auth.headers });
  expect(response.status()).toBe(200);
  return crypto.createHash('sha256').update(JSON.stringify(await response.json())).digest('hex');
}

test('production Management denies nine mutation routes; safe administrator controls cannot write', async ({ browser, request, baseURL }) => {
  const context = await browser.newContext({ baseURL });
  const page = await context.newPage();
  try {
    const management = await session(page, 'management');
    const before = await publishedFingerprint(request, management);
    for (const [method, path] of routes) {
      const response = await request.fetch(management.url(path), {
        method, headers: management.headers, data: {}, maxRedirects: 0,
      });
      expect(response.status(), `${method} ${path}`).toBe(403);
      expect(await publishedFingerprint(request, management)).toBe(before);
      console.log(JSON.stringify({ environment: 'production', role: 'management', method, path, status: 403,
        payload: 'empty invalid body; no file', published_data_unchanged: true }));
    }
    // A separate authenticated administrator verifies these payloads cannot
    // reach a valid mutation handler even if the Management guard regresses.
    const adminContext = await browser.newContext({ baseURL });
    try {
      const admin = await session(await adminContext.newPage(), 'administrator');
      for (const [method, path, expected] of routes) {
        const response = await request.fetch(admin.url(path), { method, headers: admin.headers, data: {}, maxRedirects: 0 });
        expect(response.status(), `safe administrator control ${method} ${path}`).toBe(expected);
        expect(await publishedFingerprint(request, admin)).toBe(before);
        console.log(JSON.stringify({ environment: 'production', role: 'administrator', method, path,
          status: expected, valid_mutation_executed: false }));
      }
    } finally { await adminContext.close(); }
  } finally { await context.close(); }
});
