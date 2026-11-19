# Predictive model review

The Admin **Methodology & Governance** page now shows one compact model-review panel. It checks readiness against the latest successful publication, its immutable B2B context, independently verified SI coverage, and the current calendar date. Viewing it does not fit a model or change results. Management reporting remains unchanged.

Compatible imports still score with the hash-verified `catboost_stage8` artifact. Importing a later year does not itself establish a completed 12-month outcome window. The original study forecast and later-period confirmations remain reserved evidence, not candidate-selection data.

## Separate comparison process

Use the existing backend virtual environment on an authorized local computer. This is a technical maintenance process, not another client survey. No paid worker, scheduled Vercel training, new Python dependency, new database table, or public training endpoint is required.

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_predictive_models --output .test-tmp/model-review/new-comparison.json
```

On macOS, use the corresponding environment's `python -m scripts.compare_predictive_models` command. The environment must have the pinned backend requirements and approved database/model-storage configuration. Do not transfer Windows virtual environments to macOS or put credentials in this document.

The default command reads database inputs and writes a new local report. It does not write to the database. Add `--record` only for an authorized append of completed comparison evidence to the existing monitoring table; the matching report then appears in the Admin panel. Existing report files are never overwritten. The command refuses insufficient evidence before loading or training models.

The process compares the current approved artifact with a separately fitted CatBoost candidate and an Extra Trees candidate. Parameters and thresholds are fixed before evaluation. Fitted candidates are evaluated separately in expanding chronological windows; training outcomes must finish by each test origin. Imputation is fitted only on training rows. Only published verified B2B identities eligible at each cutoff enter the comparison. Collection evidence after a cutoff does not enter its features.

Candidate review requires at least two fresh annual windows after the final study origin, at least 60 training observations and 30 test accounts per fold, and at least five outcomes of each class in both training and test sets. At most the latest three eligible windows are compared. These are conservative screening rules, not a significance test or proof of optimality. Training uses the defined historical development cutoffs and earlier eligible fresh cutoffs; original later-period confirmations and the final study origin are excluded. With the original 2025 study origin, the earliest fresh test origin is December 31, 2026, with outcomes ending December 31, 2027. The separate evaluation of the original 2026 forecast is retained in existing monitoring.

A candidate is recommended for technical review only when its mean Macro F1 improves by at least 0.02, no tested window loses Macro F1, and Future Transaction precision and recall each fall by no more than 0.05 in any window. Otherwise the recommendation is to retain the active model. The report includes every tested fold, class metrics, model/artifact identity, source publication, policy, and an input fingerprint. A changed publication, policy, artifact, or evaluated input invalidates its display as current evidence.

## Release boundary

Comparison does **not** activate, register, save a deployable replacement artifact, or roll back a predictive model. It does not rewrite the final study, account ranking, CRITIC/MCS, existing runs, or existing client answers. Automatic training dispatch and one-click model activation are not implemented. Releasing another model requires a separately validated artifact contract, technical review, and a controlled release; the current locked scoring contract intentionally rejects other artifacts. The Admin panel states this boundary rather than presenting unsupported activation controls.

The technical QA for this addition uses isolated synthetic data. Actual Admin acceptance should confirm that the review status and next step are clear. Do not record a new client/researcher acceptance or mark future outcome evaluation PASS without actual evidence.
