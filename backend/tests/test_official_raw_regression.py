"""Private final-baseline regression. Skips unless all authorized paths are provided."""
from collections import Counter
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import os
import joblib
import pandas as pd
import pytest
from app.analytics.predictive.future_transaction import score_extra_trees_artifact
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import parse_source_file
from app.services.analytics_runner import run_account_prioritization
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG

RAW = os.getenv("PESLC_OFFICIAL_RAW_PATH")
MODEL = os.getenv("PESLC_LOCKED_MODEL_PATH")
MASTER = os.getenv("PESLC_ACCOUNT_MASTER_PATH")
pytestmark = pytest.mark.skipif(
    not all((RAW, MODEL, MASTER)),
    reason="Authorized private final analytics inputs are not configured.")


def test_private_final_locked_end_to_end():
    raw_path, model_path, master_path = map(Path, (RAW, MODEL, MASTER))
    assert raw_path.is_file() and model_path.is_file() and master_path.is_file()
    parsed = parse_source_file(raw_path.name, raw_path.read_bytes())
    rows = [row for frame in parsed.frames.values()
            for row in dataframe_to_source_rows(frame, "official")]
    assert len(rows) == 363
    assert Counter(row.payment_status for row in rows) == {
        "Fully Paid": 292, "Cancelled": 71}
    groups = group_invoices(rows)
    valid = [x for x in groups if x.rfm_eligible]
    assert len(valid) == 282
    assert sum((x.si_amount for x in valid), Decimal("0")) == Decimal("167467524.93")
    master = pd.read_csv(master_path)
    name_column = next(x for x in master.columns if x.lower() in {
        "standardized_account_name", "account", "account_name"})
    eligible_column = next(x for x in master.columns if x.lower() == "b2b_priority_eligible")
    eligible = set(master.loc[
        master[eligible_column].astype(str).str.lower().isin({"true", "1", "yes"}),
        name_column].astype(str))
    assert len({x.standardized_account_name for x in groups}) == 85
    assert len(eligible) == 84
    content = model_path.read_bytes()
    assert sha256(content).hexdigest() == DEFAULT_ANALYTICS_CONFIG.model_sha256
    artifact = joblib.loads(content) if hasattr(joblib, "loads") else joblib.load(model_path)
    predictive = score_extra_trees_artifact(
        groups, artifact, pd.Timestamp("2026-09-21"), eligible,
        DEFAULT_ANALYTICS_CONFIG.model_version,
        DEFAULT_ANALYTICS_CONFIG.model_sha256)
    result = run_account_prioritization(
        groups, pd.Timestamp("2026-09-21"), eligible, predictive_result=predictive)
    assert len(result.priorities) == 84
    assert Counter(x["priority_group"] for x in result.priorities) == {
        "High": 28, "Medium": 28, "Low": 28}
    assert Counter(predictive.predictions.values()) == {"No Future Transaction": 84}
    assert result.critic_weights == pytest.approx({
        "recency": 0.374388292558304,
        "frequency": 0.19126358898879575,
        "monetary": 0.17978654445098569,
        "settlement": 0.2545615740019145,
    }, abs=1e-12)
    assert [x["account"] for x in result.priorities[:5]] == [
        "MEGAWORLD CORPORATION", "LOXON PHILIPPINES INC",
        "METRO WORX PROPERTIES INC", "RYXEN INC", "EXQUADRA INC"]
    assert sum(len(x["scenarios"]) for x in result.sensitivity) == 33600
    assert result.backtest["cutoff_count"] == 7
