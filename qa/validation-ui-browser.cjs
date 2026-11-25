// Presentation regression with synthetic intercepted Auth/API responses.
// No database requests, credential changes, or client approvals are performed.
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { chromium, expect } = createRequire(path.resolve(__dirname, '../frontend/package.json'))('@playwright/test');
const origin = process.argv[2];
const output = process.argv[3];
const run = { analysis_run_id: 'synthetic-ui-run', analysis_reference_date: '2030-06-01', completed_at: '2030-06-01T12:00:00Z', model_version: 'catboost_stage8' };
const weights = { recency: .4, frequency: .2, monetary: .3, settlement: .1 };
const accounts = [{ account: 'SYNTHETIC ACCOUNT', account_key: 'synthetic', business_category: 'Corporate', primary_business_type: 'Commercial', account_status: 'Client-Confirmed Active', is_ranked: true, current_actionable: true, priority_rank: 1, priority_group: 'High', final_priority_score: .8, r_score: 4, f_score: 3, m_score: 2, frequency_count: 3, average_settlement_days: 25, predicted_future_transaction_class: 'With Future Sales' }];
const evidence = {
  annual_rank_stability: [{ from_year: 2022, to_year: 2023, common_accounts: 12, spearman_rho: .9, mean_absolute_rank_percentile_change: .05, changed_group: 2 }],
  group_pooled_outcomes: [{ priority_group: 'High', future_buyer_account_years: 2, account_years: 10, purchase_incidence: .2, sales_capture: .3 }],
  group_yearly_outcomes: [2022, 2023].flatMap(year => ['High', 'Medium', 'Low'].map(priority_group => ({ year, priority_group, accounts: 10, buyers_group: 2, purchase_incidence: .2, sales_capture: .3, next_year_sales: 300, universe_sales: 1000 }))),
  fps_future_relationship: [{ year: 2023, auc_fps_for_next_year_purchase: .6, spearman_fps_vs_next_year_si: -.1234 }],
  recency_only_benchmark: [{ year: 2023, recency_only_lift: 1.4 }],
  feature_ablation_summary: [{ experiment: 'all_7', n_features: 7, outer_folds: 3, mean_macro_f1: .8, delta_macro_f1_vs_all_7: 0 }],
  ranking_bootstrap: [{ contrast: 'High_minus_Low', observed_rate_difference: .1, ci_2_5: -.1, ci_97_5: .3, resamples: 1000 }],
};
const validation = { run, study: { model_family: 'CatBoost', forecast_origin: '2025-12-31', future_window_start: '2026-01-01', future_window_end: '2026-12-31', target_horizon_months: 12, class_counts: { 'With Future Sales': 10, 'With No Future Sales': 73 } }, model_evidence_status: 'available', model_artifact_hash: 'synthetic', historical_error_summary: null, ranked_account_count: 12, scenario_detail_count: 4800, horizons: [], benchmarks: [], development_profile: [], lookback_summary: [], lookback_folds: [], yearly_folds: [], later_checks: [], critic_weights: weights,
  sensitivity: [.1, .2, .3, .4].map(weight_range => ({ weight_range, iterations: 100, mean_spearman: .98, min_spearman: .95, group_movement_rate: .01, max_group_movement_rate: .1 })),
  critic_influence: [{ removed_account: 'OMITTED SYNTHETIC ACCOUNT', maximum_absolute_weight_change: .05 }],
  supplemental: [
    { source_member: 'qa/current_metrics.csv', comparison: 'CRITIC vs Entropy', spearman: .95 },
    { source_member: 'AGGREGATION/current_metrics.csv', comparison: 'MCS vs TOPSIS', spearman: .99 },
    { source_member: 'qa/criterion_ablation_current.csv', removed_criterion: 'recency' },
    { source_member: 'qa/criterion_ablation_history.csv', removed_criterion: 'recency' },
    ...Array.from({ length: 12 }, (_, i) => ({ source_member: 'qa/boundary_movement.csv', account_name: 'BOUNDARY ' + (i + 1), group_change_count: 1, group_change_rate: .12 - i / 100, baseline_priority_group: 'High', perturbation_level: .1, maximum_absolute_rank_change: 2 })),
  ], backtest: { cutoffs: [{ cutoff_date: '2023-12-31', eligible_account_count: 12, selected_account_count: 2, expected_random_capture: 2 / 12, top_decile_capture: .5, lift_over_expected_random: 3 }] }, additional_evidence: evidence };
const before = JSON.stringify(validation);
const report = { scope: 'Local/released frontend rendering with synthetic intercepted Auth/API; not live database authorization or client UAT', result: 'NOT COMPLETED', checks: [], errors: [], unexpected_requests: [] };
const save = () => fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify(report, null, 2));
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    for (const role of ['administrator', 'management']) {
      for (const width of [1366, 390]) {
        const context = await browser.newContext({ viewport: { width, height: 900 } });
        const user = { id: '00000000-0000-4000-8000-000000000099', email: 'synthetic@example.invalid', aud: 'authenticated', role: 'authenticated', app_metadata: {}, user_metadata: {} };
        await context.addInitScript(({ user }) => {
          for (const ref of ['ocroshaikrfzvwtpbqzs', 'ymonifjcvkxsqhabgpxp']) localStorage.setItem('sb-' + ref + '-auth-token', JSON.stringify({ access_token: 'synthetic.integration.token', refresh_token: 'synthetic-only', expires_at: Math.floor(Date.now() / 1000) + 3600, expires_in: 3600, token_type: 'bearer', user }));
        }, { user });
        await context.route('**/*', async route => {
          const request = route.request(); const url = new URL(request.url()); const pathname = url.pathname.replace(/^\/api(?=\/)/, '');
          if (url.hostname.endsWith('.supabase.co')) return route.fulfill({ json: user });
          if (pathname === '/auth/me') return route.fulfill({ json: { role, display_name: 'Synthetic ' + role } });
          if (pathname.startsWith('/reports/native/')) {
            if (pathname.endsWith('/ranking-history')) {
              const year = Number(url.searchParams.get('year') || 2023);
              return route.fulfill({ json: { study_reference_date: '2023-12-31', years: [2022, 2023], year, population: 12, total: 1, page: 1, page_size: 10, items: [{ account_key: 'synthetic', account_name: 'SYNTHETIC ACCOUNT', year, cutoff: year + '-12-31', rank: 1, fps: .8, population: 12, priority_group: 'High', designation: 'Historical backtest', evaluation_end: (year + 1) + '-12-31', outcome_status: 'observed', subsequent_si_value: 300, previous: null }] } });
            }
            if (pathname.endsWith('/overview')) return route.fulfill({ json: { run, historical_identities: 12, b2b_analytical_accounts: 12, current_actionable_accounts: 12, ranked_accounts: 12, business_baselines: [], accounts } });
            if (pathname.endsWith('/insights')) return route.fulfill({ json: { run, accounts, critic_weights: weights } });
            return route.fulfill({ json: validation });
          }
          if (pathname.startsWith('/exports/priorities.')) return route.fulfill({ status: 200, headers: { 'Content-Disposition': 'attachment; filename=synthetic.csv' }, body: 'account,rank\nSYNTHETIC ACCOUNT,1\n' });
          if (url.origin === origin && !url.pathname.startsWith('/api/')) return route.continue();
          report.unexpected_requests.push(url.origin + url.pathname); return route.abort();
        });
        const page = await context.newPage(); page.setDefaultTimeout(30000); page.setDefaultNavigationTimeout(120000);
        page.on('pageerror', error => report.errors.push(error.message));
        await page.goto(origin + '/reports?tab=analytics-validation', { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('heading', { name: 'Understanding the evidence' })).toBeVisible();
        const content = await page.locator('#validation-findings').innerText();
        expect(content).not.toMatch(/TOPSIS|Entropy|Equal Weighting|Recency-only|leave-one-account-out|criterion-removal|account-omission|4,000|Sideño|October 28/i);
        for (const name of ['Annual Account Ranking History', 'Annual rank agreement and movement', 'Historical 12-month buyer incidence by Priority Group', 'What determines the Final Priority Score?', 'Sensitivity summary', 'Backtest summary', 'CatBoost feature-set sensitivity', 'Bootstrap uncertainty for historical group differences']) await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Buyer-discrimination AUC' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'FPS versus next-year SI Spearman' })).toBeVisible();
        await page.getByRole('combobox', { name: /^Ranking year/ }).selectOption('2022');
        await expect(page.locator('.annual-ranking-section tbody')).toContainText('SYNTHETIC ACCOUNT');
        await page.getByRole('combobox', { name: /^Group-outcome cutoff year/ }).selectOption('2022');
        await expect(page.getByRole('table', { name: 'Priority Group outcomes at the 2022 cutoff' })).toBeVisible();
        await page.getByRole('button', { name: '-0.1234', exact: true }).click();
        const tooltip = page.getByRole('tooltip'); await expect(tooltip).toBeVisible();
        await tooltip.getByText('Definition and calculation', { exact: true }).click();
        await expect(tooltip).toBeVisible(); await expect(tooltip).toContainText('observed next-year SI value');
        await page.keyboard.press('Escape');
        const boundary = page.locator('details').filter({ has: page.locator('summary', { hasText: 'Priority boundary movement observations' }) });
        await boundary.getByRole('button', { name: 'Next boundary movement page' }).click();
        await expect(boundary).toContainText('Showing 11-12 of 12');
        for (const link of await page.locator('.validation-roadmap a').all()) {
          await link.click(); const target = await link.getAttribute('href'); expect(await page.locator(target).count()).toBe(1);
        }
        await expect(page.locator('.report-meta')).toContainText('2030-06-01');
        for (const name of ['Management Overview', 'Account & Prioritization Insights', 'Analytics Validation']) { await page.getByRole('tab', { name, exact: true }).click(); await expect(page.getByRole('tabpanel', { name, exact: true })).toBeVisible(); }
        for (const format of ['CSV', 'XLSX']) { const pending = page.waitForEvent('download'); await page.getByRole('button', { name: format, exact: true }).click(); expect(await (await pending).failure()).toBeNull(); }
        await page.reload({ waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('tab', { name: 'Analytics Validation', exact: true })).toHaveAttribute('aria-selected', 'true');
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBeTruthy();
        await page.screenshot({ path: path.join(output, role + '-' + width + '.png'), fullPage: true });
        if (role === 'management') { await page.goto(origin + '/import'); await expect(page.getByText('Administrator access required', { exact: true })).toBeVisible(); }
        report.checks.push({ role, width, result: 'PASS', checks: ['removed sections absent with evidence present', 'core diagnostics retained', 'annual selectors', 'persistent definition/calculation', 'boundary pagination', 'anchors', 'three tabs', 'exports', 'reload', 'responsive layout', 'role presentation'] }); save();
        await context.close();
      }
    }
    expect(JSON.stringify(validation)).toBe(before); expect(report.errors).toEqual([]); expect(report.unexpected_requests).toEqual([]); report.result = 'PASS';
  } catch (error) { report.result = 'FAIL'; report.error = error.message; process.exitCode = 1; }
  finally { await browser.close(); save(); }
})();
