# Test Results

Executed 2026-08-20 on Windows with Python 3.13, Node 24, Next 16.3.1.

- Backend `python -m pytest`: `20 passed in 31.79s` on the final rerun.
- Frontend `npm test`: source terminology scan passed; Vitest `5 files, 8 tests passed`.
- Type check `npm run lint`: passed (`tsc --noEmit`).
- Production build `npm run build`: passed; 15 pages generated and dynamic account route validated.
- Dependency audit after upgrades: `0 vulnerabilities`.
- Playwright `npm run test:e2e`: `1 passed in 2.5m`; demo login, future preview/commit/run, new account, account detail/rank, RFM, and export. The web-server startup allowance is 240 seconds for this slow Windows workspace.
- Persisted API smoke: preview 200, commit 200, dashboard/accounts/detail/export 200; 2030 `NEW FUTURE ACCOUNT` exposed.
- Frozen workbook: 363 rows through full persisted successful publication; details in `CURRENT_DATA_VALIDATION_REPORT.md`.

The workspace filesystem required elevated permission for generated `.next`, SQLite, and browser artifacts. Playwright used an already downloaded full Chromium because the optional headless-shell download exhausted available disk space after Chromium itself had completed.
