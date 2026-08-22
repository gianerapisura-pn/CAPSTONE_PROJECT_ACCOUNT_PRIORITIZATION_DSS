# Test Results

Executed 2026-08-22 on Windows with Python 3.13, Node 24, Next 16.3.1.

- Backend `python -m pytest -q --basetemp=../.test-tmp`: `33 passed in 5.68s` on the final rerun.
- Frontend `npm test`: methodology scan passed; Vitest `5 files, 8 tests passed`.
- ESLint `npm run lint`: passed with no errors or warnings.
- Type check `npm run typecheck`: passed.
- Production build `npm run build`: passed; 15 routes generated and the dynamic account route validated.
- Dependency audit after upgrades: `0 vulnerabilities`.
- Playwright `npm run test:e2e` with the installed Chromium executable:
  `1 passed in 1.2m`; demo login, future preview/commit, new account,
  account detail, RFM rendering, and CSV export completed.
- Persisted integration tests cover duplicate blocking, preview/commit,
  latest-successful publication, 2030 `NEW FUTURE ACCOUNT`, and API payloads
  using isolated SQLite/private demo storage.
- Frozen workbook: 363 rows processed read-only through the corrected analytics
  pipeline; details in `CURRENT_DATA_VALIDATION_REPORT.md`.

The workspace filesystem required elevated permission for generated `.next`, SQLite, and browser artifacts. Playwright used an already downloaded full Chromium because the optional headless-shell download exhausted available disk space after Chromium itself had completed.
