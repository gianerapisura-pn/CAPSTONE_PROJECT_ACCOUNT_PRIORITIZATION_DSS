"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { RefreshCw, RotateCcw } from "lucide-react";
import { PageState } from "@/components/page-state";
import { useApi } from "@/lib/use-api";
import type { AccountDecisionRow, RunSummary } from "@/types/dss";

type Overview = {
  run: RunSummary;
  historical_identities: number;
  b2b_analytical_accounts: number;
  current_actionable_accounts: number;
  ranked_accounts: number;
  business_baselines: { year: number; period_status: string; all_recorded_sales: number; data_complete_through: string }[];
  accounts: AccountDecisionRow[];
};
type Insights = { run: RunSummary; accounts: AccountDecisionRow[] };
type EvidenceRow = Record<string, string | number | boolean | null>;
type Validation = {
  run: RunSummary;
  study: { status: string; model_version?: string; model_family?: string; target_horizon_months?: number; forecast_origin?: string; future_window_start?: string; future_window_end?: string; class_counts?: Record<string, number> };
  model_evidence_status: string;
  model_artifact_hash: string | null;
  historical_error_summary: { observations: number; errors: number; true_future: number; missed_future: number; true_no_future: number; false_future: number } | null;
  scenario_detail_count: number;
  ranked_account_count: number;
  horizons: EvidenceRow[];
  benchmarks: EvidenceRow[];
  later_checks: EvidenceRow[];
  sensitivity: { weight_range: number; iterations: number; mean_spearman: number; min_spearman: number; group_movement_rate: number; max_group_movement_rate: number }[];
  critic_influence: EvidenceRow[];
  backtest: { cutoffs?: { cutoff_date: string; eligible_account_count: number; selected_account_count: number; expected_random_capture: number | null; top_decile_capture: number | null; lift_over_expected_random: number | null }[] };
  critic_weights: Record<string, number>;
  supplemental: EvidenceRow[];
};

const colors = { high: "#168366", medium: "#4d78ac", low: "#d59c43", line: "#167d68", muted: "#788d98" };
const groups = ["High", "Medium", "Low"] as const;
const money = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", maximumFractionDigits: 0 });
const number = new Intl.NumberFormat("en-PH");
const pct = (value: number | null | undefined) => value == null ? "Unavailable" : `${(value * 100).toFixed(2)}%`;
const score = (value: number | null | undefined) => value == null ? "Unavailable" : value.toFixed(4);
const finiteValue = (value: unknown): number | null => value == null || value === "" || !Number.isFinite(Number(value)) ? null : Number(value);
const evidenceScore = (value: unknown) => value == null || !Number.isFinite(Number(value)) ? "Unavailable" : score(Number(value));
const evidencePct = (value: unknown) => value == null || !Number.isFinite(Number(value)) ? "Unavailable" : pct(Number(value));

function RunContext({ run, onRefresh }: { run: RunSummary; onRefresh: () => void }) {
  return <div className="report-meta" aria-label="Published analysis context">
    <span>Analysis reference <strong>{run.analysis_reference_date ?? "Unavailable"}</strong></span>
    <span>Published run <strong className="mono">{run.analysis_run_id.slice(0, 12)}</strong></span>
    <span>Completed <strong>{run.completed_at ? new Date(run.completed_at).toLocaleString() : "Unavailable"}</strong></span>
    <span>Model <strong>{run.model_version ?? "Unavailable"}</strong></span>
    <button type="button" className="button secondary" onClick={onRefresh}><RefreshCw size={15} />Refresh reports</button>
  </div>;
}

function ChartFrame({ title, description, children, tall = false, empty = false }: { title: string; description: string; children: React.ReactNode; tall?: boolean; empty?: boolean }) {
  return <section className="native-chart" aria-label={title}>
    <div className="native-chart-heading"><h3>{title}</h3><p>{description}</p></div>
    {empty ? <div className="native-chart-empty" role="status">No published evidence is available for this chart in the selected run.</div> : <div className={`native-chart-canvas${tall ? " tall" : ""}`} role="img" aria-label={`${title}. ${description}`}>{children}</div>}
  </section>;
}

function FilterSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label className="native-filter">{label}<select value={value} onChange={event => onChange(event.target.value)}>
    <option value="">All</option>{options.map(option => <option key={option} value={option}>{option}</option>)}
  </select></label>;
}

function MultiFilter({ label, values, options, onChange }: { label: string; values: string[]; options: string[]; onChange: (values: string[]) => void }) {
  return <details className="native-multi-filter"><summary>{label}{values.length ? ` (${values.length})` : " (All)"}</summary>
    <div>{options.map(option => <label key={option}><input type="checkbox" checked={values.includes(option)} onChange={() => onChange(values.includes(option) ? values.filter(item => item !== option) : [...values, option])} />{option}</label>)}</div>
  </details>;
}

export function ManagementOverview() {
  const { data, error, loading, reload } = useApi<Overview>("/reports/native/overview");
  const router = useRouter();
  const [category, setCategory] = useState("");
  const [group, setGroup] = useState("");
  const [prediction, setPrediction] = useState("");
  const accounts = data?.accounts ?? [];
  const categories = [...new Set(accounts.map(row => row.business_category).filter((value): value is string => Boolean(value)))].sort();
  const filtered = accounts.filter(row => (!category || row.business_category === category) && (!group || row.priority_group === group) && (!prediction || row.predicted_future_transaction_class === prediction));
  const distribution = groups.map(name => ({ name, count: filtered.filter(row => row.priority_group === name).length }));
  const top = filtered.filter(row => row.is_ranked && row.final_priority_score != null)
    .sort((a, b) => (a.priority_rank ?? Infinity) - (b.priority_rank ?? Infinity)).slice(0, 10)
    .map(row => ({ name: row.account, score: row.final_priority_score, rank: row.priority_rank, account_key: row.account_key }));
  const reset = () => { setCategory(""); setGroup(""); setPrediction(""); };
  return <PageState loading={loading} error={error} onRetry={reload} empty={!data}>
    {data && <div className="native-report-content">
      <RunContext run={data.run} onRefresh={reload} />
      <div className="report-facts"><div><span>Historical identities</span><strong>{data.historical_identities}</strong></div><div><span>Verified B2B profiles</span><strong>{data.b2b_analytical_accounts}</strong></div><div><span>Current actionable</span><strong>{data.current_actionable_accounts}</strong></div><div><span>Ranked accounts</span><strong>{data.ranked_accounts}</strong></div><div><span>Accounts in view</span><strong>{filtered.length}</strong></div></div>
      <div className="native-filter-bar"><FilterSelect label="Business category" value={category} options={categories} onChange={setCategory} /><FilterSelect label="Priority group" value={group} options={[...groups]} onChange={setGroup} /><FilterSelect label="Operational 12-month SI class" value={prediction} options={["Future Transaction", "No Future Transaction"]} onChange={setPrediction} /><button className="button secondary" onClick={reset}><RotateCcw size={15} />Reset filters</button></div>
      <ChartFrame title="Annual Valid Sales Invoice Sales" description="All valid recorded Sales Invoices; vertical axis in PHP millions. Account filters do not change this source-wide baseline." empty={!data.business_baselines.length}>
        <ResponsiveContainer width="100%" height="100%"><LineChart data={data.business_baselines} margin={{ top: 12, right: 24, bottom: 12, left: 20 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="year" /><YAxis width={64} tickFormatter={value => `${(Number(value) / 1000000).toFixed(0)}m`} /><Tooltip formatter={value => money.format(Number(value))} labelFormatter={label => `Year ${label}`} /><Line type="monotone" dataKey="all_recorded_sales" name="Valid SI sales (PHP)" stroke={colors.line} strokeWidth={3} dot /></LineChart></ResponsiveContainer>
      </ChartFrame>
      <p className="native-note">The current reference year is labeled complete only when the published baseline marks it as a complete year. {data.business_baselines.at(-1)?.period_status ?? "Coverage unavailable"}.</p>
      <div className="native-chart-grid">
        <ChartFrame title="Priority Group Counts" description="Published groups; select a bar to filter accounts." empty={!accounts.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={distribution}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Accounts" onClick={entry => setGroup(String(entry?.payload?.name ?? ""))}>{distribution.map(row => <Cell key={row.name} fill={colors[row.name.toLowerCase() as keyof typeof colors]} fillOpacity={!group || group === row.name ? 1 : 0.4} />)}</Bar></BarChart></ResponsiveContainer></ChartFrame>
        <ChartFrame title="Top 10 Ranked Accounts" description="Published score and original rank; select a bar or account to open detail." empty={!top.length} tall><ResponsiveContainer width="100%" height="100%"><BarChart data={top} layout="vertical" margin={{ left: 16, right: 22 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" domain={[0, 1]} /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} /><Tooltip formatter={value => score(Number(value))} /><Bar dataKey="score" name="Final Priority Score" fill={colors.medium} onClick={entry => { if (entry?.payload?.account_key) router.push(`/accounts/${encodeURIComponent(String(entry.payload.account_key))}`); }} /></BarChart></ResponsiveContainer></ChartFrame>
      </div>
      <div className="native-account-links">{top.map(row => <Link key={row.account_key} href={`/accounts/${encodeURIComponent(row.account_key)}`}>#{row.rank} {row.name} <strong>{score(row.score)}</strong></Link>)}</div>
    </div>}
  </PageState>;
}

const settlementBins = ["Below 30", "30-<60", "60-<90", "90-<120", "120+"];
function settlementBin(days: number) { return days < 30 ? settlementBins[0] : days < 60 ? settlementBins[1] : days < 90 ? settlementBins[2] : days < 120 ? settlementBins[3] : settlementBins[4]; }

export function AccountInsights() {
  const { data, error, loading, reload } = useApi<Insights>("/reports/native/insights");
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [types, setTypes] = useState<string[]>([]);
  const [group, setGroup] = useState("");
  const [status, setStatus] = useState("");
  const [ranking, setRanking] = useState("");
  const [prediction, setPrediction] = useState("");
  const [scoreSelection, setScoreSelection] = useState<number | null>(null);
  const [binSelection, setBinSelection] = useState("");
  const [selectedKey, setSelectedKey] = useState("");
  const accounts = data?.accounts ?? [];
  const option = (field: "business_category" | "primary_business_type" | "account_status") => [...new Set(accounts.map(row => row[field]).filter((value): value is string => Boolean(value)))].sort();
  const filtered = accounts.filter(row => {
    const matchesScore = scoreSelection == null || [row.r_score, row.f_score, row.m_score].includes(scoreSelection);
    const matchesBin = !binSelection || (row.average_settlement_days != null && settlementBin(row.average_settlement_days) === binSelection);
    return row.account.toLowerCase().includes(search.toLowerCase()) && (!categories.length || categories.includes(row.business_category ?? "")) && (!types.length || types.includes(row.primary_business_type ?? "")) && (!group || row.priority_group === group) && (!status || row.account_status === status) && (!ranking || (ranking === "Ranked" ? row.is_ranked : !row.is_ranked)) && (!prediction || row.predicted_future_transaction_class === prediction) && matchesScore && matchesBin;
  });
  const rfm = [1, 2, 3, 4, 5].map(value => ({ name: String(value), value, Recency: filtered.filter(row => row.r_score === value).length, Frequency: filtered.filter(row => row.f_score === value).length, Monetary: filtered.filter(row => row.m_score === value).length }));
  const settlement = settlementBins.map(name => ({ name, count: filtered.filter(row => row.average_settlement_days != null && settlementBin(row.average_settlement_days) === name).length }));
  const byCategory = [...new Set(filtered.map(row => row.business_category ?? "Unspecified"))].sort().map(name => ({ name, High: filtered.filter(row => (row.business_category ?? "Unspecified") === name && row.priority_group === "High").length, Medium: filtered.filter(row => (row.business_category ?? "Unspecified") === name && row.priority_group === "Medium").length, Low: filtered.filter(row => (row.business_category ?? "Unspecified") === name && row.priority_group === "Low").length }));
  const selected = filtered.find(row => row.account_key === selectedKey) ?? null;
  const reset = () => { setSearch(""); setCategories([]); setTypes([]); setGroup(""); setStatus(""); setRanking(""); setPrediction(""); setScoreSelection(null); setBinSelection(""); setSelectedKey(""); };
  return <PageState loading={loading} error={error} onRetry={reload} empty={!data}>
    {data && <div className="native-report-content"><RunContext run={data.run} onRefresh={reload} />
      <div className="native-filter-bar"><label className="native-filter">Account search<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search account" /></label><MultiFilter label="Business category" values={categories} options={option("business_category")} onChange={setCategories} /><MultiFilter label="Primary business type" values={types} options={option("primary_business_type")} onChange={setTypes} /><FilterSelect label="Priority group" value={group} options={[...groups]} onChange={setGroup} /><FilterSelect label="Current status" value={status} options={option("account_status")} onChange={setStatus} /><FilterSelect label="Ranking status" value={ranking} options={["Ranked", "Not ranked"]} onChange={setRanking} /><FilterSelect label="Future SI class" value={prediction} options={["Future Transaction", "No Future Transaction"]} onChange={setPrediction} /><button className="button secondary" onClick={reset}><RotateCcw size={15} />Reset filters</button></div>
      <p className="native-note">{number.format(filtered.length)} of {number.format(accounts.length)} verified B2B accounts in view. Chart selections filter the view; published weights, scores, ranks, and groups never change. {scoreSelection != null ? `R/F/M score ${scoreSelection} selected. ` : ""}{binSelection ? `${binSelection} days selected.` : ""}</p>
      <div className="native-chart-grid"><ChartFrame title="RFM Score Distribution" description="Published tie-aware 1-5 scores. Select a bar to filter accounts with that R, F, or M score." empty={!filtered.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={rfm}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Bar dataKey="Recency" fill={colors.high} onClick={entry => setScoreSelection(Number(entry?.payload?.value))} /><Bar dataKey="Frequency" fill={colors.medium} onClick={entry => setScoreSelection(Number(entry?.payload?.value))} /><Bar dataKey="Monetary" fill={colors.low} onClick={entry => setScoreSelection(Number(entry?.payload?.value))} /></BarChart></ResponsiveContainer></ChartFrame>
        <ChartFrame title="Historical Settlement Duration Distribution" description="Account-level average settlement days; missing values are excluded, not treated as zero." empty={!filtered.some(row => row.average_settlement_days != null)}><ResponsiveContainer width="100%" height="100%"><BarChart data={settlement}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" name="Accounts" fill={colors.medium} onClick={entry => setBinSelection(String(entry?.payload?.name ?? ""))} /></BarChart></ResponsiveContainer></ChartFrame></div>
      <ChartFrame title="Priority Groups by Business Category" description="Verified category is descriptive only; it is not an input to CRITIC or MCS." empty={!byCategory.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={byCategory} layout="vertical" margin={{ left: 12, right: 18 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} /><Tooltip /><Legend /><Bar dataKey="High" stackId="a" fill={colors.high} onClick={entry => setCategories([String(entry?.payload?.name ?? "")])} /><Bar dataKey="Medium" stackId="a" fill={colors.medium} onClick={entry => setCategories([String(entry?.payload?.name ?? "")])} /><Bar dataKey="Low" stackId="a" fill={colors.low} onClick={entry => setCategories([String(entry?.payload?.name ?? "")])} /></BarChart></ResponsiveContainer></ChartFrame>
      <section className="native-table-section"><div className="section-heading"><h2>B2B status and prioritization</h2><span>{filtered.length} accounts</span></div><div className="table-wrap"><table><thead><tr><th>Account</th><th>Category</th><th>Current status</th><th>Ranking</th><th>Priority group</th><th>Score</th><th>12-month SI class</th></tr></thead><tbody>{filtered.map(row => <tr key={row.account_key}><td><button className="native-table-link" onClick={() => setSelectedKey(row.account_key)}>{row.account}</button></td><td>{row.business_category ?? "Unavailable"}</td><td>{row.account_status ?? "Unavailable"}</td><td>{row.is_ranked ? `#${row.priority_rank}` : row.ranking_status}</td><td>{row.priority_group ?? "Not ranked"}</td><td>{score(row.final_priority_score)}</td><td>{row.predicted_future_transaction_class ?? "Unavailable"}</td></tr>)}</tbody></table></div></section>
      {selected && <section className="native-detail" aria-label="Selected account summary"><div className="section-heading"><h2>{selected.account}</h2><Link href={`/accounts/${encodeURIComponent(selected.account_key)}`}>Open account detail</Link></div><div className="native-detail-grid"><span>Status <strong>{selected.account_status ?? "Unavailable"}</strong></span><span>R/F/M <strong>{selected.r_score} / {selected.f_score} / {selected.m_score}</strong></span><span>Settlement days <strong>{selected.average_settlement_days?.toFixed(1) ?? "Unavailable"}</strong></span><span>Final Priority Score <strong>{score(selected.final_priority_score)}</strong></span><span>Published rank / group <strong>{selected.is_ranked ? `#${selected.priority_rank} / ${selected.priority_group}` : "Not ranked"}</strong></span><span>Separate future SI class <strong>{selected.predicted_future_transaction_class ?? "Unavailable"}</strong></span>{(["recency", "frequency", "monetary", "settlement"] as const).map(criterion => <span key={criterion}>{criterion[0].toUpperCase() + criterion.slice(1)} normalized / weight / contribution <strong>{score(selected[`normalized_${criterion}`])} / {pct(selected[`baseline_${criterion}_weight`])} / {score(selected[`${criterion}_contribution`])}</strong></span>)}</div></section>}
      <p className="native-note">Settlement duration is historical evidence, not a contractual late/on-time assessment. Predicted class is separate from the Final Priority Score.</p>
    </div>}
  </PageState>;
}

export function AnalyticsValidation() {
  const { data, error, loading, reload } = useApi<Validation>("/reports/native/validation");
  const horizon = (data?.horizons ?? []).map(row => ({ name: `${row.horizon_months} months`, macroF1: finiteValue(row.mean_macro_f1_2020_2022), recall: finiteValue(row.mean_future_recall_2020_2022), selected: row.stage4_decision === "SELECTED" }));
  const benchmark = (data?.benchmarks ?? []).filter(row => row.source_member === "model_benchmark.csv" && ["CatBoost", "Extra Trees", "HistGradientBoosting"].includes(String(row.family))).map(row => ({ name: String(row.family), macroF1: finiteValue(row.mean_macro_f1), row }));
  const benchmarkRows = benchmark.filter(row => ["CatBoost", "Extra Trees"].includes(row.name));
  const sensitivity = (data?.sensitivity ?? []).map(row => ({ name: `+/-${Math.round(row.weight_range * 100)}%`, mean: row.mean_spearman, min: row.min_spearman, ...row }));
  const backtest = (data?.backtest.cutoffs ?? []).map(row => ({ name: row.cutoff_date.slice(0, 4), lift: row.lift_over_expected_random, ...row }));
  const studyCounts = data?.study.class_counts ?? {};
  const currentComparisons = (data?.supplemental ?? []).filter(row => String(row.source_member).endsWith("/current_metrics.csv"));
  const robustnessBacktests = (data?.supplemental ?? []).filter(row => String(row.source_member).endsWith("/backtest_summary.csv"));
  return <PageState loading={loading} error={error} onRetry={reload} empty={!data}>
    {data && <div className="native-report-content"><RunContext run={data.run} onRefresh={reload} />
      <div className="report-facts"><div><span>Selected model</span><strong>{data.study.model_family ?? data.run.model_version ?? "Unavailable"}</strong></div><div><span>Study predicted Future SI</span><strong>{studyCounts["Future Transaction"] ?? "Unavailable"}</strong></div><div><span>Study predicted No Future SI</span><strong>{studyCounts["No Future Transaction"] ?? "Unavailable"}</strong></div><div><span>Total study predictions</span><strong>{Object.keys(studyCounts).length ? Object.values(studyCounts).reduce((total, count) => total + count, 0) : "Unavailable"}</strong></div><div><span>Current ranked</span><strong>{data.ranked_account_count}</strong></div><div><span>Sensitivity scenarios</span><strong>{data.sensitivity.length ? data.sensitivity.reduce((total, row) => total + row.iterations, 0) : "Unavailable"}</strong></div><div><span>Account-scenario rows</span><strong>{data.sensitivity.length ? number.format(data.scenario_detail_count) : "Unavailable"}</strong></div><div><span>Study outcome monitoring</span><strong>{data.study.status === "Validated" ? "Pending" : "Unavailable"}</strong></div></div>
      <p className="native-note">Study origin {data.study.forecast_origin ?? "unavailable"}; {data.study.target_horizon_months ?? "unavailable"}-month outcome window {data.study.future_window_start ?? "unavailable"} to {data.study.future_window_end ?? "unavailable"}. Predictions are not verified future sales. Model evidence: {data.model_evidence_status}. Artifact SHA-256: <code>{data.model_artifact_hash ?? "Unavailable"}</code>.</p>
      <div className="native-chart-grid"><ChartFrame title="Prediction Horizon Comparison" description="Stage 4 Extra Trees horizon screen, 2020-2022 equal-year means; 12 months selected." empty={!horizon.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={horizon}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 1]} /><Tooltip formatter={value => score(Number(value))} /><Legend /><Bar dataKey="macroF1" name="Macro F1" fill={colors.high} /><Bar dataKey="recall" name="Future recall" fill={colors.medium} /></BarChart></ResponsiveContainer></ChartFrame>
        <ChartFrame title="Model Benchmark: Mean Macro F1" description="Chronological equal-year comparison; CatBoost selected, Extra Trees retained as challenger." empty={!benchmark.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={benchmark}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis domain={[0, 1]} /><Tooltip formatter={value => score(Number(value))} /><Bar dataKey="macroF1" name="Mean Macro F1">{benchmark.map(row => <Cell key={row.name} fill={row.name === "CatBoost" ? colors.high : colors.medium} />)}</Bar></BarChart></ResponsiveContainer></ChartFrame></div>
      <section className="native-table-section"><div className="section-heading"><h2>Selected model and challenger</h2></div><div className="table-wrap"><table><thead><tr><th>Metric</th>{benchmarkRows.map(row => <th key={row.name}>{row.name}</th>)}</tr></thead><tbody>{([ ["Mean Macro F1", "mean_macro_f1"], ["Mean error", "mean_classification_error"], ["Balanced accuracy", "mean_balanced_accuracy"], ["Future recall", "mean_future_recall"], ["Future F1", "mean_future_f1"], ["MCC", "mean_mcc"] ] as const).map(([label, key]) => <tr key={key}><th>{label}</th>{benchmarkRows.map(row => <td key={row.name}>{evidenceScore(row.row[key])}</td>)}</tr>)}</tbody></table></div></section>
      <p className="native-note">CatBoost was selected on recorded mean chronological Macro F1; its advantage over Extra Trees is small. {data.historical_error_summary ? ("Historical pooled validation recorded " + data.historical_error_summary.errors + " errors in " + data.historical_error_summary.observations + " observations (" + data.historical_error_summary.true_future + " true Future, " + data.historical_error_summary.missed_future + " missed Future, " + data.historical_error_summary.true_no_future + " true No Future, " + data.historical_error_summary.false_future + " false Future).") : "Pooled confusion evidence is unavailable."} This is not confirmed 2026 forecast accuracy.</p>
      <section className="native-table-section"><div className="section-heading"><h2>Historical later-period confirmations</h2></div><div className="table-wrap"><table><thead><tr><th>Period</th><th>Cutoff</th><th>Outcome end</th><th>Accounts</th><th>Actual Future / No Future</th><th>Predicted Future / No Future</th><th>Error</th><th>Macro F1</th><th>Accuracy</th></tr></thead><tbody>{data.later_checks.map(row => <tr key={String(row.cutoff_date)}><td>{row.period}</td><td>{row.cutoff_date}</td><td>{row.future_window_end}</td><td>{row.observations}</td><td>{row.actual_future_transaction} / {row.actual_no_future_transaction}</td><td>{row.predicted_future_transaction} / {row.predicted_no_future_transaction}</td><td>{evidencePct(row.classification_error)}</td><td>{evidenceScore(row.macro_f1)}</td><td>{evidencePct(row.accuracy)}</td></tr>)}</tbody></table></div><p className="native-note">These are historical outcome confirmations, not accuracy claims for the pending 2026 forecast.</p></section>
      <div className="native-chart-grid"><ChartFrame title="Sensitivity: Mean Spearman Rank Correlation" description="Persisted four-range CRITIC-weight perturbation summaries; no simulation runs in the browser." empty={!sensitivity.length}><ResponsiveContainer width="100%" height="100%"><LineChart data={sensitivity}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 1]} /><Tooltip formatter={value => score(Number(value))} /><Legend /><Line dataKey="mean" name="Mean Spearman" stroke={colors.high} strokeWidth={2} /><Line dataKey="min" name="Minimum Spearman" stroke={colors.medium} strokeWidth={2} /></LineChart></ResponsiveContainer></ChartFrame>
        <ChartFrame title="Historical Backtests 2018-2024: Lift vs Random" description="Published closure-aware cutoff results; below-random years remain visible." empty={!backtest.length}><ResponsiveContainer width="100%" height="100%"><BarChart data={backtest}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip formatter={value => score(Number(value))} /><Bar dataKey="lift" name="Lift vs random" fill={colors.medium} /></BarChart></ResponsiveContainer></ChartFrame></div>
      <div className="native-chart-grid"><section className="native-table-section"><div className="section-heading"><h2>Sensitivity summary</h2></div><div className="table-wrap"><table><thead><tr><th>Range</th><th>Scenarios</th><th>Mean Spearman</th><th>Max group movement</th></tr></thead><tbody>{sensitivity.map(row => <tr key={row.name}><td>{row.name}</td><td>{row.iterations}</td><td>{score(row.mean)}</td><td>{pct(row.max_group_movement_rate)}</td></tr>)}</tbody></table></div></section><section className="native-table-section"><div className="section-heading"><h2>Backtest summary</h2></div><div className="table-wrap"><table><thead><tr><th>Cutoff</th><th>Eligible</th><th>Selected</th><th>Random capture</th><th>Observed</th><th>Lift</th></tr></thead><tbody>{backtest.map(row => <tr key={row.name}><td>{row.name}</td><td>{row.eligible_account_count}</td><td>{row.selected_account_count}</td><td>{pct(row.expected_random_capture)}</td><td>{pct(row.top_decile_capture)}</td><td>{score(row.lift_over_expected_random)}</td></tr>)}</tbody></table></div></section></div>
      <details className="native-evidence-details"><summary>Leave-one-account-out CRITIC influence ({data.critic_influence.length})</summary><div className="table-wrap"><table><thead><tr><th>Removed account</th><th>Maximum weight change</th><th>Rank Spearman</th><th>Group movement</th><th>Recomputed weights</th></tr></thead><tbody>{data.critic_influence.map((row, index) => <tr key={index}><td>{String(row.removed_account ?? "Unavailable")}</td><td>{evidenceScore(row.maximum_absolute_weight_change)}</td><td>{evidenceScore(row.spearman_correlation)}</td><td>{evidencePct(row.group_movement_rate)}</td><td><code>{JSON.stringify(row.recomputed_weights ?? {})}</code></td></tr>)}</tbody></table></div></details>
      <details className="native-evidence-details"><summary>Supplementary weighting and aggregation evidence ({data.supplemental.length})</summary><div className="table-wrap"><table><thead><tr><th>Comparison</th><th>Rank Spearman</th><th>Group agreement</th><th>Group changes</th></tr></thead><tbody>{currentComparisons.map((row, index) => <tr key={index}><td>{String(row.comparison ?? (String(row.source_member).includes("AGGREGATION") ? "Additive MCS vs CRITIC-TOPSIS" : "Unavailable"))}</td><td>{evidenceScore(row.spearman)}</td><td>{evidencePct(row.group_agreement)}</td><td>{String(row.group_changes ?? "Unavailable")}</td></tr>)}</tbody></table></div><div className="table-wrap"><table><thead><tr><th>Method</th><th>Periods</th><th>Lift above random</th><th>Mean lift</th><th>Minimum lift</th><th>Pooled future sales capture</th></tr></thead><tbody>{robustnessBacktests.map((row, index) => <tr key={index}><td>{String(row.method ?? "Unavailable")}</td><td>{String(row.periods ?? "Unavailable")}</td><td>{String(row.periods_lift_above_1 ?? "Unavailable")}</td><td>{evidenceScore(row.mean_lift)}</td><td>{evidenceScore(row.minimum_lift)}</td><td>{evidencePct(row.pooled_future_sales_capture_rate)}</td></tr>)}</tbody></table></div></details>
      <p className="native-note">Predictive CatBoost classification and prescriptive CRITIC + additive MCS are separate. Entropy, Equal Weighting, and TOPSIS results are locked 2025-study supplementary checks, not operational replacements or recalculations for later runs.</p>
    </div>}
  </PageState>;
}
