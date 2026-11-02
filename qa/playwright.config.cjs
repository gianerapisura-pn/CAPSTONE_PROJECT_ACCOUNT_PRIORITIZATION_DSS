const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: ['**/production.spec.cjs', '**/export_parity.spec.cjs'],
  timeout: 120_000,
  retries: 0,
  workers: 1,
  expect: { timeout: 30_000 },
  reporter: [['list']],
  use: {
    browserName: 'chromium',
    baseURL: process.env.PESLC_WEB_URL || 'https://peslc-dss-academic-web.vercel.app',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    acceptDownloads: true,
  },
});
