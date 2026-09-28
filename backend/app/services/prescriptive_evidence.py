from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import PrescriptiveValidationEvidence
from app.services.locked_packages import (
    PRESCRIPTIVE_PACKAGE_SHA256,
    csv_members_under,
    verified_package,
)

EVIDENCE_VERSION = "prescriptive-robustness-locked-v1"


def _json_value(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _column(frame: pd.DataFrame, candidates: set[str]) -> str | None:
    for name in frame.columns:
        normalized = re.sub(r"[^a-z0-9]+", "_", str(name).casefold()).strip("_")
        if normalized in candidates:
            return str(name)
    return None


def seed_prescriptive_validation_evidence(db: Session, package_path: str | Path) -> dict:
    _, content = verified_package(package_path, PRESCRIPTIVE_PACKAGE_SHA256)
    db.execute(delete(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION
    ))
    counts = {"weighting_robustness": 0, "aggregation_robustness": 0}
    for name, frame in csv_members_under(content, ""):
        lowered = name.casefold()
        if any(term in lowered for term in ("entropy", "equal_weight", "weighting")):
            scope = "weighting_robustness"
        elif any(term in lowered for term in ("topsis", "aggregation")):
            scope = "aggregation_robustness"
        else:
            continue
        comparator_column = _column(
            frame,
            {"method", "model", "comparator", "weighting_method", "aggregation_method"},
        )
        for index, source in enumerate(frame.to_dict(orient="records"), start=1):
            payload = {
                "source_member": name,
                "row": index,
                **{str(key): _json_value(value) for key, value in source.items()},
            }
            comparator = str(source.get(comparator_column) or Path(name).stem) if comparator_column else Path(name).stem
            db.add(PrescriptiveValidationEvidence(
                evidence_version=EVIDENCE_VERSION,
                evidence_scope=scope,
                comparator=comparator,
                payload=payload,
                source_package_hash=PRESCRIPTIVE_PACKAGE_SHA256,
            ))
            counts[scope] += 1
    if not all(counts.values()):
        raise ValueError(
            "Verified package did not expose both weighting and aggregation robustness evidence."
        )
    return counts