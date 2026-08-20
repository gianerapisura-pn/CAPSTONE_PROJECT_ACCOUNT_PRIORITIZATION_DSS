from dataclasses import asdict, dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AnalyticsConfig:
    version: str = "2026.08.prototype"
    candidate_outcome_windows: tuple[int, ...] = (3, 6, 12)
    predictive_lookback_months: int = 24
    recent_transaction_months: int = 12
    spearman_redundancy_threshold: float = 0.80
    random_seed: int = 42
    sensitivity_ranges: tuple[float, ...] = (0.10, 0.20, 0.30, 0.40)
    sensitivity_iterations: int = 100
    random_baseline_repetitions: int = 100
    monetary_precision: Decimal = Decimal("0.01")
    cart_min_class_count: int = 2
    cart_max_depth: tuple[int, ...] = (2, 3, 4, 5)

    def serializable(self) -> dict:
        data = asdict(self)
        data["monetary_precision"] = str(self.monetary_precision)
        return data


DEFAULT_ANALYTICS_CONFIG = AnalyticsConfig()
