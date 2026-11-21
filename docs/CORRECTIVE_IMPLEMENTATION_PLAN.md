# Implementation Scope

The DSS uses the registered frozen CatBoost artifact for 12-month Future Transaction classification, with an explicit analysis reference and verified B2B eligibility. Its analytical workflow includes empirical-quintile RFM, cumulative logical-invoice reconstruction, duplicate no-op handling, artifact hash/version verification, four-criterion CRITIC/MCS, 400 sensitivity scenarios, leave-one-account-out influence, and cutoff-safe historical backtests against the exact k/n expected-random baseline. Routine imports do not retrain the model, and predictions do not determine FPS, rank, or Priority Group.

The authenticated web DSS presents published results through its operational pages and three native Detailed Analytics views. Entropy, Equal Weighting, and CRITIC-weighted TOPSIS provide supplementary robustness evidence; the official ranking method is CRITIC-weighted additive MCS.

Release verification follows `docs/DEPLOYMENT.md`. User acceptance and technical validation remain separate evidence categories, with case definitions in `docs/UAT_PLAN.md` and `docs/UAT_TEST_CASES.csv`. Actual execution records establish their outcomes; this scope document does not assign test results.
