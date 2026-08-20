from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup

LOWER_RISK = "Lower Inactivity Risk"
HIGHER_RISK = "Higher Inactivity Risk"
CANDIDATE_FEATURES = [
    "recency_days", "frequency_count", "monetary_value", "avg_settlement_days",
    "recent_transaction_count", "latest_transaction_year", "account_activity_gap",
    "has_valid_settlement_record",
]


@dataclass(frozen=True)
class CartResult:
    status: str
    outcome_window_months: int
    feature_columns: list[str]
    report: dict
    predictions: dict[str, str]
    model_version: str = ""
    lookback_months: int = 0
    development_periods: list[str] | None = None
    oop_period: str | None = None
    majority_baseline: float | None = None
    confusion_matrix: list[list[int]] | None = None
    feature_evidence: list[dict] | None = None
    redundancy_flags: list[dict] | None = None
    gini_importance: dict[str, float] | None = None
    permutation_importance: dict[str, float] | None = None
    feature_set_comparison: list[dict] | None = None
    hyperparameters: dict | None = None
    tree_depth: int | None = None
    leaf_count: int | None = None
    candidate_window_evidence: list[dict] | None = None


def _empty_result(status: str, config: AnalyticsConfig, window: int = 0) -> CartResult:
    return CartResult(
        status=status, outcome_window_months=window, feature_columns=[], report={}, predictions={},
        model_version=f"cart-{config.version}", lookback_months=config.predictive_lookback_months,
        development_periods=[], feature_evidence=[], redundancy_flags=[], gini_importance={},
        permutation_importance={}, feature_set_comparison=[], candidate_window_evidence=[],
    )


def build_cutoff_dataset(
    invoice_groups: list[InvoiceGroup], cutoff_date: pd.Timestamp, lookback_months: int,
    outcome_window_months: int, recent_months: int = 12,
) -> pd.DataFrame:
    """Build account observations with predictors available on or before cutoff only."""
    cutoff = pd.Timestamp(cutoff_date)
    feature_start = cutoff - pd.DateOffset(months=lookback_months)
    recent_start = cutoff - pd.DateOffset(months=recent_months)
    history = [g for g in invoice_groups if g.rfm_eligible and feature_start <= g.si_date <= cutoff]
    future_end = cutoff + pd.DateOffset(months=outcome_window_months)
    future_accounts = {g.standardized_account_name for g in invoice_groups if g.rfm_eligible and cutoff < g.si_date <= future_end}
    rows: list[dict] = []
    for account in sorted({g.standardized_account_name for g in history}):
        account_history = sorted((g for g in history if g.standardized_account_name == account), key=lambda g: g.si_date)
        dates = [g.si_date for g in account_history]
        settlement_days = [
            g.settlement_days for g in account_history
            if g.final_cr_date is not None and g.final_cr_date <= cutoff and g.settlement_days is not None
        ]
        rows.append({
            "account": account, "cutoff_date": cutoff,
            "recency_days": int((cutoff - dates[-1]).days),
            "frequency_count": len(account_history),
            "monetary_value": float(sum((g.si_amount for g in account_history), start=0)),
            "avg_settlement_days": float(np.mean(settlement_days)) if settlement_days else np.nan,
            "recent_transaction_count": sum(date >= recent_start for date in dates),
            "latest_transaction_year": int(dates[-1].year),
            "account_activity_gap": float((dates[-1] - dates[-2]).days) if len(dates) > 1 else np.nan,
            "has_valid_settlement_record": int(bool(settlement_days)),
            "inactivity_risk": LOWER_RISK if account in future_accounts else HIGHER_RISK,
        })
    return pd.DataFrame(rows)


def _candidate_cutoffs(groups: list[InvoiceGroup], window: int, lookback: int) -> list[pd.Timestamp]:
    dates = sorted(g.si_date for g in groups if g.rfm_eligible)
    if not dates:
        return []
    start = pd.Timestamp(dates[0]) + pd.DateOffset(months=min(lookback, 12))
    end = pd.Timestamp(dates[-1]) - pd.DateOffset(months=window)
    if start > end:
        return []
    cutoffs = list(pd.date_range(start=start, end=end, freq="6ME"))
    cutoffs.append(end)
    return sorted(set(pd.Timestamp(item).normalize() for item in cutoffs))


def _pipeline(params: dict, seed: int) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("tree", DecisionTreeClassifier(criterion="gini", random_state=seed, class_weight="balanced", **params)),
    ])


def _feasible(frame: pd.DataFrame, minimum: int) -> bool:
    if frame.empty or "inactivity_risk" not in frame:
        return False
    counts = frame["inactivity_risk"].value_counts()
    return len(counts) == 2 and int(counts.min()) >= minimum


def _temporal_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoffs = sorted(pd.Timestamp(value) for value in frame["cutoff_date"].unique())
    if len(cutoffs) < 2:
        return frame.iloc[0:0], frame.iloc[0:0]
    validation_cutoff = cutoffs[-1]
    return frame[frame["cutoff_date"] < validation_cutoff], frame[frame["cutoff_date"] == validation_cutoff]


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict:
    report = classification_report(actual, predicted, labels=[LOWER_RISK, HIGHER_RISK], output_dict=True, zero_division=0)
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "per_class": {
            label: {"precision": float(report[label]["precision"]), "recall": float(report[label]["recall"]),
                    "f1": float(report[label]["f1-score"]), "support": int(report[label]["support"])}
            for label in (LOWER_RISK, HIGHER_RISK)
        },
    }


def _window_frame(groups: list[InvoiceGroup], window: int, config: AnalyticsConfig) -> pd.DataFrame:
    frames = [build_cutoff_dataset(groups, cutoff, config.predictive_lookback_months, window, config.recent_transaction_months)
              for cutoff in _candidate_cutoffs(groups, window, config.predictive_lookback_months)]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _select_window(groups: list[InvoiceGroup], config: AnalyticsConfig) -> tuple[int, pd.DataFrame, list[dict]]:
    evidence: list[dict] = []
    best: tuple[float, int, int, pd.DataFrame] | None = None
    params = {"max_depth": 3, "min_samples_split": 4, "min_samples_leaf": 2, "ccp_alpha": 0.0}
    for window in config.candidate_outcome_windows:
        frame = _window_frame(groups, window, config)
        if frame.empty:
            evidence.append({"window_months": window, "status": "unavailable", "observations": 0})
            continue
        latest = max(pd.Timestamp(value) for value in frame["cutoff_date"].unique())
        development = frame[frame["cutoff_date"] < latest]
        train, validation = _temporal_split(development)
        viable = _feasible(train, config.cart_min_class_count) and not validation.empty
        score = 0.0
        if viable:
            model = _pipeline(params, config.random_seed)
            model.fit(train[CANDIDATE_FEATURES], train["inactivity_risk"])
            score = float(f1_score(validation["inactivity_risk"], model.predict(validation[CANDIDATE_FEATURES]), average="macro", zero_division=0))
        evidence.append({"window_months": window, "status": "viable" if viable else "insufficient development support",
                         "observations": len(frame), "development_observations": len(development), "macro_f1": score})
        candidate = (score, len(development), window, frame)
        if viable and (best is None or candidate[:2] > best[:2]):
            best = candidate
    return (best[2], best[3], evidence) if best else (0, pd.DataFrame(), evidence)


def _tune(train: pd.DataFrame, validation: pd.DataFrame, features: list[str], config: AnalyticsConfig) -> tuple[dict, float]:
    best: tuple[float, int, dict] | None = None
    for depth, split, leaf, alpha in product(config.cart_max_depth, (2, 4, 8), (1, 2, 4), (0.0, 0.005, 0.01)):
        params = {"max_depth": depth, "min_samples_split": split, "min_samples_leaf": leaf, "ccp_alpha": alpha}
        model = _pipeline(params, config.random_seed)
        model.fit(train[features], train["inactivity_risk"])
        score = float(f1_score(validation["inactivity_risk"], model.predict(validation[features]), average="macro", zero_division=0))
        complexity = model.named_steps["tree"].get_n_leaves()
        if best is None or score > best[0] or (np.isclose(score, best[0]) and complexity < best[1]):
            best = (score, complexity, params)
    assert best is not None
    return best[2], best[0]


def run_cart_analysis(invoice_groups: list[InvoiceGroup], config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG) -> CartResult:
    """Run development-only selection followed by one untouched chronological OOP test."""
    window, frame, window_evidence = _select_window(invoice_groups, config)
    if not window or frame.empty:
        result = _empty_result("Predictive Context Unavailable / Insufficient Data", config)
        return CartResult(**{**asdict(result), "candidate_window_evidence": window_evidence})
    cutoffs = sorted(pd.Timestamp(value) for value in frame["cutoff_date"].unique())
    oop_cutoff = cutoffs[-1]
    development = frame[frame["cutoff_date"] < oop_cutoff].copy()
    oop = frame[frame["cutoff_date"] == oop_cutoff].copy()
    train, validation = _temporal_split(development)
    if not _feasible(train, config.cart_min_class_count) or validation.empty or oop.empty:
        result = _empty_result("Predictive Context Unavailable / Insufficient Data", config, window)
        return CartResult(**{**asdict(result), "candidate_window_evidence": window_evidence})

    missingness = development[CANDIDATE_FEATURES].isna().mean()
    correlations = development[CANDIDATE_FEATURES].corr(method="spearman").fillna(0)
    redundancy = [{"feature_a": left, "feature_b": right, "spearman": float(correlations.loc[left, right])}
                  for index, left in enumerate(CANDIDATE_FEATURES) for right in CANDIDATE_FEATURES[index + 1:]
                  if abs(float(correlations.loc[left, right])) >= config.spearman_redundancy_threshold]

    broad_params, broad_score = _tune(train, validation, CANDIDATE_FEATURES, config)
    broad_model = _pipeline(broad_params, config.random_seed)
    broad_model.fit(train[CANDIDATE_FEATURES], train["inactivity_risk"])
    transformed = broad_model.named_steps["imputer"].get_feature_names_out(CANDIDATE_FEATURES)
    gini = {feature: 0.0 for feature in CANDIDATE_FEATURES}
    for name, importance in zip(transformed, broad_model.named_steps["tree"].feature_importances_, strict=False):
        base = next((feature for feature in CANDIDATE_FEATURES if name == feature or name.endswith(feature)), None)
        if base:
            gini[base] += float(importance)
    permutation = permutation_importance(broad_model, validation[CANDIDATE_FEATURES], validation["inactivity_risk"],
                                         scoring="f1_macro", n_repeats=10, random_state=config.random_seed)
    permutation_scores = dict(zip(CANDIDATE_FEATURES, map(float, permutation.importances_mean), strict=True))
    retained = [feature for feature in CANDIDATE_FEATURES
                if missingness[feature] < 0.80 and (gini[feature] > 0 or permutation_scores[feature] > 0)]
    for required in ("recency_days", "frequency_count", "has_valid_settlement_record"):
        if required not in retained:
            retained.append(required)
    retained = [feature for feature in CANDIDATE_FEATURES if feature in retained]
    if len(retained) == len(CANDIDATE_FEATURES):
        removable = [feature for feature in retained if feature not in {"recency_days", "frequency_count"}]
        if removable:
            retained.remove(min(removable, key=lambda f: gini[f] + max(0, permutation_scores[f])))
    reduced_params, reduced_score = _tune(train, validation, retained, config)
    use_reduced = reduced_score + 0.02 >= broad_score and len(retained) < len(CANDIDATE_FEATURES)
    selected = retained if use_reduced else list(CANDIDATE_FEATURES)
    selected_params = reduced_params if use_reduced else broad_params
    evidence = [{
        "feature": feature, "status": "retained" if feature in selected else "removed",
        "reason": "retained after data quality, importance, temporal utility, and interpretability review" if feature in selected
                  else "reduced set retained comparable development performance with lower complexity",
        "missing_rate": float(missingness[feature]), "gini_importance": gini[feature],
        "permutation_importance": permutation_scores[feature],
    } for feature in CANDIDATE_FEATURES]

    final_model = _pipeline(selected_params, config.random_seed)
    final_model.fit(development[selected], development["inactivity_risk"])
    oop_predicted = final_model.predict(oop[selected])
    metrics = _metrics(oop["inactivity_risk"], oop_predicted)
    majority = float(oop["inactivity_risk"].value_counts(normalize=True).max())
    matrix = confusion_matrix(oop["inactivity_risk"], oop_predicted, labels=[LOWER_RISK, HIGHER_RISK]).tolist()
    final_tree = final_model.named_steps["tree"]

    current_cutoff = max(g.si_date for g in invoice_groups if g.rfm_eligible)
    current = build_cutoff_dataset(invoice_groups, current_cutoff, config.predictive_lookback_months, window, config.recent_transaction_months)
    operational_model = _pipeline(selected_params, config.random_seed)
    operational_model.fit(frame[selected], frame["inactivity_risk"])
    current_predictions = operational_model.predict(current[selected]) if not current.empty else []
    return CartResult(
        status="Validated", outcome_window_months=window, feature_columns=selected, report=metrics,
        predictions=dict(zip(current.get("account", []), current_predictions, strict=False)),
        model_version=f"cart-{config.version}", lookback_months=config.predictive_lookback_months,
        development_periods=[cutoff.date().isoformat() for cutoff in cutoffs[:-1]], oop_period=oop_cutoff.date().isoformat(),
        majority_baseline=majority, confusion_matrix=matrix, feature_evidence=evidence,
        redundancy_flags=redundancy, gini_importance=gini, permutation_importance=permutation_scores,
        feature_set_comparison=[
            {"feature_set": "broader", "features": CANDIDATE_FEATURES, "development_macro_f1": broad_score},
            {"feature_set": "reduced", "features": retained, "development_macro_f1": reduced_score},
        ],
        hyperparameters=selected_params, tree_depth=int(final_tree.get_depth()), leaf_count=int(final_tree.get_n_leaves()),
        candidate_window_evidence=window_evidence,
    )


def train_cart_temporal(development_frame: pd.DataFrame, oop_frame: pd.DataFrame, random_seed: int = 42,
                        min_class_count: int = 2) -> CartResult:
    """Focused temporal trainer retained for controlled tests."""
    config = AnalyticsConfig(random_seed=random_seed, cart_min_class_count=min_class_count)
    available = [feature for feature in CANDIDATE_FEATURES if feature in development_frame.columns]
    if not available:
        available = [feature for feature in ("recency_days", "frequency", "monetary") if feature in development_frame.columns]
    if development_frame.empty or oop_frame.empty or not _feasible(development_frame, min_class_count):
        result = _empty_result("Predictive Context Unavailable / Insufficient Data", config)
        return CartResult(**{**asdict(result), "feature_columns": available})
    model = _pipeline({"max_depth": 3, "min_samples_split": 2, "min_samples_leaf": 1, "ccp_alpha": 0.0}, random_seed)
    model.fit(development_frame[available], development_frame["inactivity_risk"])
    predicted = model.predict(oop_frame[available])
    return CartResult(status="Validated", outcome_window_months=0, feature_columns=available,
                      report=_metrics(oop_frame["inactivity_risk"], predicted),
                      predictions=dict(zip(oop_frame["account"], predicted, strict=False)))
