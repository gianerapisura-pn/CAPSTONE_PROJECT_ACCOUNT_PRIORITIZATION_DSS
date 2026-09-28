from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AnalyticsConfig:
    version: str = "2026.09-final-locked"
    model_version: str = "extra_trees_stage8"
    model_family: str = "Extra Trees Classifier"
    model_sha256: str = "7c606fceb6a5e9515e68dc53430789352128ad2e1cad7bd2941c826bbcff91d8"
    target_horizon_months: int = 12
    candidate_outcome_windows: tuple[int, ...] = (3, 6, 12)
    predictive_lookback_months: int = 24
    recent_transaction_months: int = 12
    decision_threshold: float = 0.50
    random_seed: int = 42
    sensitivity_ranges: tuple[float, ...] = (0.10, 0.20, 0.30, 0.40)
    sensitivity_iterations: int = 100
    monetary_precision: Decimal = Decimal("0.01")
    development_cutoffs: tuple[str, ...] = (
        "2018-12-31", "2019-12-31", "2020-12-31",
        "2021-12-31", "2022-12-31",
    )
    outer_validation_years: tuple[int, ...] = (2020, 2021, 2022)
    backtest_cutoffs: tuple[str, ...] = (
        "2018-12-31", "2019-12-31", "2020-12-31", "2021-12-31",
        "2022-12-31", "2023-12-31", "2024-12-31",
    )
    backtest_horizon_months: int = 12

    def serializable(self) -> dict:
        data = asdict(self)
        data["monetary_precision"] = str(self.monetary_precision)
        return data


DEFAULT_ANALYTICS_CONFIG = AnalyticsConfig()