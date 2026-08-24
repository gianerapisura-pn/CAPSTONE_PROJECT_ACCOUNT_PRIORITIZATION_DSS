from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG, AnalyticsConfig
from app.etl.invoices import InvoiceGroup

LOWER_RISK = "Lower"
HIGHER_RISK = "Higher"
TARGET_COLUMN = "realized_inactivity_outcome"
CANDIDATE_FEATURES = [
    "recency_days",
    "frequency_count",
    "monetary_value",
    "avg_settlement_days",
    "account_activity_gap",
    "has_valid_settlement_record",
    "recent_transaction_count",
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
    majority_baseline_report: dict | None = None
    confusion_matrix: list[list[int]] | None = None
    feature_evidence: list[dict] | None = None
    redundancy_flags: list[dict] | None = None
    gini_importance: dict[str, float] | None = None
    permutation_importance: dict[str, float] | None = None
    permutation_importance_std: dict[str, float] | None = None
    feature_set_comparison: list[dict] | None = None
    hyperparameters: dict | None = None
    tree_depth: int | None = None
    leaf_count: int | None = None
    candidate_window_evidence: list[dict] | None = None
    historical_target_field: str = TARGET_COLUMN
    operational_prediction_field: str = "predicted_inactivity_risk"


def _empty_result(status: str, config: AnalyticsConfig, window: int = 0) -> CartResult:
    return CartResult(
        status=status,
        outcome_window_months=window,
        feature_columns=[],
        report={},
        predictions={},
        lookback_months=config.predictive_lookback_months,
        development_periods=list(config.cart_development_cutoffs),
        oop_period=config.cart_oop_cutoff,
        feature_evidence=[],
        redundancy_flags=[],
        gini_importance={},
        permutation_importance={},
        permutation_importance_std={},
        feature_set_comparison=[],
        candidate_window_evidence=[],
    )


def build_cutoff_dataset(
    invoice_groups: list[InvoiceGroup],
    cutoff_date: pd.Timestamp,
    lookback_months: int,
    outcome_window_months: int,
    recent_months: int = 12,
    include_outcome: bool = True,
) -> pd.DataFrame:
    """Build predictors from evidence known by cutoff and an optional realized outcome."""
    cutoff = pd.Timestamp(cutoff_date)
    valid = [group for group in invoice_groups if group.rfm_eligible]
    history = [group for group in valid if group.si_date <= cutoff]
    if not history:
        return pd.DataFrame()
    future_end = cutoff + pd.DateOffset(months=outcome_window_months)
    if include_outcome and max(group.si_date for group in valid) < future_end:
        return pd.DataFrame()
    feature_start = cutoff - pd.DateOffset(months=lookback_months)
    recent_start = cutoff - pd.DateOffset(months=recent_months)
    future_accounts = {
        group.standardized_account_name
        for group in valid
        if cutoff < group.si_date <= future_end
    }
    rows: list[dict] = []
    for account in sorted({group.standardized_account_name for group in history}):
        account_history = sorted(
            (group for group in history if group.standardized_account_name == account),
            key=lambda group: group.si_date,
        )
        window_history = [
            group for group in account_history if feature_start < group.si_date <= cutoff
        ]
        dates = [group.si_date for group in account_history]
        settlement_days = [
            group.settlement_days
            for group in account_history
            if group.settlement_eligible
            and group.final_cr_date is not None
            and group.final_cr_date <= cutoff
            and group.settlement_days is not None
        ]
        row = {
            "account": account,
            "cutoff_date": cutoff,
            "recency_days": int((cutoff - dates[-1]).days),
            "frequency_count": len(window_history),
            "monetary_value": float(sum((group.si_amount for group in window_history), start=0)),
            "avg_settlement_days": float(np.mean(settlement_days)) if settlement_days else np.nan,
            "account_activity_gap": float((dates[-1] - dates[-2]).days) if len(dates) > 1 else np.nan,
            "has_valid_settlement_record": int(bool(settlement_days)),
            "recent_transaction_count": sum(recent_start < date <= cutoff for date in dates),
            "latest_transaction_year": int(dates[-1].year),
        }
        if include_outcome:
            row[TARGET_COLUMN] = LOWER_RISK if account in future_accounts else HIGHER_RISK
        rows.append(row)
    return pd.DataFrame(rows)


def _pipeline(params: dict, seed: int) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("tree", DecisionTreeClassifier(criterion="gini", random_state=seed, **params)),
    ])


def _feasible(frame: pd.DataFrame, minimum: int) -> bool:
    if frame.empty or TARGET_COLUMN not in frame:
        return False
    counts = frame[TARGET_COLUMN].value_counts()
    return len(counts) == 2 and int(counts.min()) >= minimum


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict:
    report = classification_report(
        actual,
        predicted,
        labels=[LOWER_RISK, HIGHER_RISK],
        output_dict=True,
        zero_division=0,
    )
    accuracy = float(accuracy_score(actual, predicted))
    return {
        "accuracy": accuracy,
        "classification_error": 1.0 - accuracy,
        "macro_f1": float(f1_score(actual, predicted, average="macro", zero_division=0)),
        "class_distribution": {
            label: int((actual == label).sum()) for label in (LOWER_RISK, HIGHER_RISK)
        },
        "per_class": {
            label: {
                "precision": float(report[label]["precision"]),
                "recall": float(report[label]["recall"]),
                "f1": float(report[label]["f1-score"]),
                "support": int(report[label]["support"]),
            }
            for label in (LOWER_RISK, HIGHER_RISK)
        },
    }


def classification_metrics(actual, predicted) -> dict:
    return _metrics(pd.Series(actual), np.asarray(predicted))


def _window_frame(groups: list[InvoiceGroup], window: int, config: AnalyticsConfig) -> pd.DataFrame:
    frames = [
        build_cutoff_dataset(
            groups,
            pd.Timestamp(cutoff),
            config.predictive_lookback_months,
            window,
            config.recent_transaction_months,
        )
        for cutoff in config.cart_cutoffs
    ]
    frames = [frame for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _walk_forward_scores(
    frame: pd.DataFrame,
    features: list[str],
    params: dict,
    config: AnalyticsConfig,
) -> tuple[float, float, int]:
    macro_scores: list[float] = []
    errors: list[float] = []
    for validation_cutoff in map(pd.Timestamp, config.cart_development_cutoffs[1:]):
        train = frame[frame["cutoff_date"] < validation_cutoff]
        validation = frame[frame["cutoff_date"] == validation_cutoff]
        if not _feasible(train, config.cart_min_class_count) or validation.empty:
            continue
        model = _pipeline(params, config.random_seed)
        model.fit(train[features], train[TARGET_COLUMN])
        metrics = _metrics(validation[TARGET_COLUMN], model.predict(validation[features]))
        macro_scores.append(metrics["macro_f1"])
        errors.append(metrics["classification_error"])
    if not macro_scores:
        return 0.0, 1.0, 0
    return float(np.mean(macro_scores)), float(np.mean(errors)), len(macro_scores)


def _grid(config: AnalyticsConfig):
    for depth in config.cart_max_depth:
        for split in config.cart_min_samples_split:
            for leaf in config.cart_min_samples_leaf:
                yield {
                    "max_depth": depth,
                    "min_samples_split": split,
                    "min_samples_leaf": leaf,
                }


def _tune(frame: pd.DataFrame, features: list[str], config: AnalyticsConfig) -> tuple[dict, float, float]:
    candidates: list[tuple[float, float, int, int, int, dict]] = []
    for params in _grid(config):
        macro_f1, error, folds = _walk_forward_scores(frame, features, params, config)
        if folds:
            candidates.append((
                macro_f1,
                -error,
                -params["max_depth"],
                params["min_samples_leaf"],
                params["min_samples_split"],
                params,
            ))
    if not candidates:
        return {}, 0.0, 1.0
    best = max(candidates)
    return best[-1], best[0], -best[1]


def _development_supported_features(
    missingness: pd.Series,
    gini_importance: dict[str, float],
    permutation_scores: dict[str, float],
) -> list[str]:
    """Build a reduced set from development evidence without mandatory business features."""
    selected = {
        feature
        for feature in CANDIDATE_FEATURES
        if missingness[feature] < 0.80
        and (gini_importance[feature] > 0 or permutation_scores[feature] > 0)
    }
    if "avg_settlement_days" in selected:
        selected.add("has_valid_settlement_record")
    return [feature for feature in CANDIDATE_FEATURES if feature in selected]


def _select_window(
    groups: list[InvoiceGroup], config: AnalyticsConfig
) -> tuple[int, pd.DataFrame, list[dict]]:
    evidence: list[dict] = []
    candidates: list[tuple[float, float, int, int, pd.DataFrame]] = []
    default_params = {
        "max_depth": config.cart_max_depth[0],
        "min_samples_split": config.cart_min_samples_split[0],
        "min_samples_leaf": config.cart_min_samples_leaf[0],
    }
    for order, window in enumerate(config.candidate_outcome_windows):
        frame = _window_frame(groups, window, config)
        development = frame[frame["cutoff_date"].isin(map(pd.Timestamp, config.cart_development_cutoffs))] if not frame.empty else frame
        macro_f1, error, folds = _walk_forward_scores(
            development, list(CANDIDATE_FEATURES), default_params, config
        ) if not development.empty else (0.0, 1.0, 0)
        counts = development[TARGET_COLUMN].value_counts() if not development.empty else pd.Series(dtype=int)
        evidence.append({
            "window_months": window,
            "status": "viable" if folds else "insufficient development support",
            "observations": len(frame),
            "development_observations": len(development),
            "development_folds": folds,
            "lower_count": int(counts.get(LOWER_RISK, 0)),
            "higher_count": int(counts.get(HIGHER_RISK, 0)),
            "mean_macro_f1": macro_f1 if folds else None,
            "mean_classification_error": error if folds else None,
        })
        if folds:
            candidates.append((macro_f1, -error, -order, window, frame))
    if not candidates:
        return 0, pd.DataFrame(), evidence
    best = max(candidates)
    return best[3], best[4], evidence


def run_cart_analysis(
    invoice_groups: list[InvoiceGroup],
    config: AnalyticsConfig = DEFAULT_ANALYTICS_CONFIG,
    include_artifact: bool = False,
) -> CartResult | tuple[CartResult, dict | None]:
    """Select on development only, then evaluate and preserve one frozen OOP artifact."""
    def finish(result: CartResult, artifact: dict | None = None):
        return (result, artifact) if include_artifact else result

    window, frame, window_evidence = _select_window(invoice_groups, config)
    if not window or frame.empty:
        empty = _empty_result("Predictive Context Unavailable / Insufficient Data", config)
        return finish(CartResult(**{**asdict(empty), "candidate_window_evidence": window_evidence}))

    development = frame[
        frame["cutoff_date"].isin(map(pd.Timestamp, config.cart_development_cutoffs))
    ].copy()
    oop = frame[frame["cutoff_date"] == pd.Timestamp(config.cart_oop_cutoff)].copy()
    if not _feasible(development, config.cart_min_class_count) or oop.empty:
        empty = _empty_result("Predictive Context Unavailable / Insufficient Data", config, window)
        return finish(CartResult(**{**asdict(empty), "candidate_window_evidence": window_evidence}))

    missingness = development[CANDIDATE_FEATURES].isna().mean()
    correlations = development[CANDIDATE_FEATURES].corr(method="spearman").fillna(0.0)
    redundancy = [
        {"feature_a": left, "feature_b": right, "spearman": float(correlations.loc[left, right])}
        for index, left in enumerate(CANDIDATE_FEATURES)
        for right in CANDIDATE_FEATURES[index + 1:]
        if abs(float(correlations.loc[left, right])) >= config.spearman_redundancy_threshold
    ]

    broad_params, broad_score, broad_error = _tune(development, list(CANDIDATE_FEATURES), config)
    if not broad_params:
        empty = _empty_result("Predictive Context Unavailable / Insufficient Data", config, window)
        return finish(CartResult(**{**asdict(empty), "candidate_window_evidence": window_evidence}))

    broad_model = _pipeline(broad_params, config.random_seed)
    broad_model.fit(development[CANDIDATE_FEATURES], development[TARGET_COLUMN])
    gini = dict(zip(
        CANDIDATE_FEATURES,
        map(float, broad_model.named_steps["tree"].feature_importances_),
        strict=True,
    ))

    validation_cutoff = pd.Timestamp(config.cart_development_cutoffs[-1])
    importance_train = development[development["cutoff_date"] < validation_cutoff]
    importance_validation = development[development["cutoff_date"] == validation_cutoff]
    permutation_scores = {feature: 0.0 for feature in CANDIDATE_FEATURES}
    permutation_std = {feature: 0.0 for feature in CANDIDATE_FEATURES}
    if _feasible(importance_train, config.cart_min_class_count) and not importance_validation.empty:
        importance_model = _pipeline(broad_params, config.random_seed)
        importance_model.fit(importance_train[CANDIDATE_FEATURES], importance_train[TARGET_COLUMN])
        measured = permutation_importance(
            importance_model,
            importance_validation[CANDIDATE_FEATURES],
            importance_validation[TARGET_COLUMN],
            scoring="f1_macro",
            n_repeats=10,
            random_state=config.random_seed,
        )
        permutation_scores = dict(zip(CANDIDATE_FEATURES, map(float, measured.importances_mean), strict=True))
        permutation_std = dict(zip(CANDIDATE_FEATURES, map(float, measured.importances_std), strict=True))

    retained = _development_supported_features(missingness, gini, permutation_scores)
    reduced_params, reduced_score, reduced_error = (
        _tune(development, retained, config) if retained else ({}, 0.0, 1.0)
    )
    use_reduced = bool(
        reduced_params
        and len(retained) < len(CANDIDATE_FEATURES)
        and (
            reduced_score > broad_score
            or (np.isclose(reduced_score, broad_score) and reduced_error <= broad_error)
        )
    )
    selected = retained if use_reduced else list(CANDIDATE_FEATURES)
    selected_params = reduced_params if use_reduced else broad_params
    evidence = [{
        "feature": feature,
        "status": "retained" if feature in selected else "removed",
        "reason": (
            "Retained with the nullable Settlement feature to represent structural evidence availability."
            if feature == "has_valid_settlement_record"
            and "avg_settlement_days" in selected
            and gini[feature] <= 0
            and permutation_scores[feature] <= 0
            else "Retained after business relevance, missingness, leakage, redundancy, importance, and temporal validation review."
            if feature in selected
            else "Removed by the development-only reduced-set comparison; OOP evidence was not used."
        ),
        "missing_rate": float(missingness[feature]),
        "gini_importance": gini[feature],
        "permutation_importance": permutation_scores[feature],
        "permutation_importance_std": permutation_std[feature],
    } for feature in CANDIDATE_FEATURES]

    frozen_model = _pipeline(selected_params, config.random_seed)
    frozen_model.fit(development[selected], development[TARGET_COLUMN])
    oop_predicted = frozen_model.predict(oop[selected])
    metrics = _metrics(oop[TARGET_COLUMN], oop_predicted)
    dummy = DummyClassifier(strategy="most_frequent", random_state=config.random_seed)
    dummy.fit(development[selected], development[TARGET_COLUMN])
    dummy_predicted = dummy.predict(oop[selected])
    majority_report = _metrics(oop[TARGET_COLUMN], dummy_predicted)
    matrix = confusion_matrix(
        oop[TARGET_COLUMN], oop_predicted, labels=[LOWER_RISK, HIGHER_RISK]
    ).tolist()
    tree = frozen_model.named_steps["tree"]

    current_cutoff = max(group.si_date for group in invoice_groups if group.rfm_eligible)
    current = build_cutoff_dataset(
        invoice_groups,
        current_cutoff,
        config.predictive_lookback_months,
        window,
        config.recent_transaction_months,
        include_outcome=False,
    )
    current_predictions = frozen_model.predict(current[selected]) if not current.empty else []
    result = CartResult(
        status="Validated",
        outcome_window_months=window,
        feature_columns=selected,
        report=metrics,
        predictions=dict(zip(current.get("account", []), current_predictions, strict=False)),
        model_version=f"cart-{config.version}",
        lookback_months=config.predictive_lookback_months,
        development_periods=list(config.cart_development_cutoffs),
        oop_period=config.cart_oop_cutoff,
        majority_baseline=majority_report["accuracy"],
        majority_baseline_report=majority_report,
        confusion_matrix=matrix,
        feature_evidence=evidence,
        redundancy_flags=redundancy,
        gini_importance=gini,
        permutation_importance=permutation_scores,
        permutation_importance_std=permutation_std,
        feature_set_comparison=[
            {
                "feature_set": "broader",
                "features": CANDIDATE_FEATURES,
                "development_macro_f1": broad_score,
                "development_classification_error": broad_error,
            },
            {
                "feature_set": "reduced",
                "features": retained,
                "development_macro_f1": reduced_score,
                "development_classification_error": reduced_error,
            },
        ],
        hyperparameters=selected_params,
        tree_depth=int(tree.get_depth()),
        leaf_count=int(tree.get_n_leaves()),
        candidate_window_evidence=window_evidence,
    )
    artifact = {
        "pipeline": frozen_model,
        "feature_columns": selected,
        "outcome_window_months": window,
        "lookback_months": config.predictive_lookback_months,
        "recent_months": config.recent_transaction_months,
        "trained_cutoffs": list(config.cart_development_cutoffs),
        "oop_cutoff": config.cart_oop_cutoff,
        "majority_class": str(development[TARGET_COLUMN].mode().iloc[0]),
        "imputation_values": {feature: None if pd.isna(value) else float(value) for feature, value in zip(selected, frozen_model.named_steps["imputer"].statistics_, strict=True)},
        "result_metadata": {**asdict(result), "predictions": {}},
    }
    return finish(result, artifact)


def score_cart_artifact(invoice_groups: list[InvoiceGroup], artifact: dict) -> CartResult:
    """Score current accounts with a previously validated, frozen CART artifact."""
    eligible = [group for group in invoice_groups if group.rfm_eligible]
    metadata = dict(artifact["result_metadata"])
    if not eligible:
        metadata["predictions"] = {}
        return CartResult(**metadata)
    cutoff = max(group.si_date for group in eligible)
    current = build_cutoff_dataset(
        invoice_groups,
        cutoff,
        int(artifact["lookback_months"]),
        int(artifact["outcome_window_months"]),
        int(artifact["recent_months"]),
        include_outcome=False,
    )
    features = list(artifact["feature_columns"])
    predicted = artifact["pipeline"].predict(current[features]) if not current.empty else []
    metadata["predictions"] = dict(zip(current.get("account", []), predicted, strict=False))
    return CartResult(**metadata)


def train_cart_temporal(
    development_frame: pd.DataFrame,
    oop_frame: pd.DataFrame,
    random_seed: int = 42,
    min_class_count: int = 2,
) -> CartResult:
    """Focused trainer for tests; it uses only the declared production grid."""
    config = AnalyticsConfig(random_seed=random_seed, cart_min_class_count=min_class_count)
    development = development_frame.copy()
    oop = oop_frame.copy()
    if TARGET_COLUMN not in development and "inactivity_risk" in development:
        development[TARGET_COLUMN] = development["inactivity_risk"]
        oop[TARGET_COLUMN] = oop["inactivity_risk"]
    available = [feature for feature in CANDIDATE_FEATURES if feature in development.columns]
    if not available:
        available = [
            feature for feature in ("recency_days", "frequency", "monetary")
            if feature in development.columns
        ]
    if development.empty or oop.empty or not _feasible(development, min_class_count):
        empty = _empty_result("Predictive Context Unavailable / Insufficient Data", config)
        return CartResult(**{**asdict(empty), "feature_columns": available})
    params = {
        "max_depth": config.cart_max_depth[0],
        "min_samples_split": config.cart_min_samples_split[0],
        "min_samples_leaf": config.cart_min_samples_leaf[0],
    }
    model = _pipeline(params, random_seed)
    model.fit(development[available], development[TARGET_COLUMN])
    predicted = model.predict(oop[available])
    baseline = DummyClassifier(strategy="most_frequent", random_state=random_seed)
    baseline.fit(development[available], development[TARGET_COLUMN])
    baseline_predicted = baseline.predict(oop[available])
    report = _metrics(oop[TARGET_COLUMN], predicted)
    baseline_report = _metrics(oop[TARGET_COLUMN], baseline_predicted)
    return CartResult(
        status="Validated",
        outcome_window_months=0,
        feature_columns=available,
        report=report,
        predictions=dict(zip(oop["account"], predicted, strict=False)),
        majority_baseline=baseline_report["accuracy"],
        majority_baseline_report=baseline_report,
        confusion_matrix=confusion_matrix(
            oop[TARGET_COLUMN], predicted, labels=[LOWER_RISK, HIGHER_RISK]
        ).tolist(),
        hyperparameters=params,
        tree_depth=model.named_steps["tree"].get_depth(),
        leaf_count=model.named_steps["tree"].get_n_leaves(),
    )
