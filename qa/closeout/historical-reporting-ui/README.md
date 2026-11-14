# Historical report UI correction

Annual Account Ranking History now uses aligned year/search controls, consistent column widths, wrapped account names and numeric alignment. Pagination uses the existing report spacing.

The annual Priority Group breakdown now has an explicit button-controlled state. Its content is absent on initial load and after refresh until opened. The expanded annual table uses consistent headers and numeric alignment.

Only the historical UI component, report stylesheet and its existing component tests changed. Backend logic, Supabase records, formulas, models, rankings, exports and manuscript remain unchanged.

Application revision: ccb7dcfc11d578023eaaa087f17173cd21433082
CI: https://github.com/gianerapisura-pn/CAPSTONE_PROJECT_ACCOUNT_PRIORITIZATION_DSS/actions/runs/43619370459

47 affected local UI tests passed. TypeScript and lint passed. The complete CI passed 164 frontend tests, types/lint, 73 existing backend regression checks and one synthetic browser workflow. These counts overlap other runs.

Staging browser checks passed for Admin and Management at 1440, 1366, 1024 and 390 pixels. The checks include matching control heights, desktop alignment, stacked mobile controls, right-aligned numeric columns, paragraph bounds, the absent collapsed table, expanded annual results, refresh, exports and access boundaries. No page errors were recorded.

Production deployment dpl_J9ErLrDPAhMxh7TX4MyGUYoJNPue is READY at the existing public URL, serving commit ccb7dcfc11d578023eaaa087f17173cd21433082. Both production roles passed the same checks with zero page errors. The public alias was verified. The existing human UAT follow-up remains separate.
