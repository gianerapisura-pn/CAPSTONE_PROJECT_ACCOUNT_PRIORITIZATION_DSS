"""Disposable synthetic CI publication; never a reproduction of client study data.

The original parity test reads this fixture unchanged. Real-study reconciliation
is separate private evidence. No source ZIP, model binary or credential is needed.
"""
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
import json
import sys

import pandas as pd
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.db.models import (
    AnalyticsRun, Base, DimAccount, PredictiveModelVersion,
    PrescriptiveValidationEvidence, AccountPriorityResult,
)
from app.db.repository import persist_run_output
from app.etl.invoices import InvoiceGroup
from app.services.analytics_runner import run_account_prioritization
from app.services.study_predictions import MODEL_VERSION, MODEL_ARTIFACT_SHA256
from app.services.additional_validation_evidence import EVIDENCE_VERSION
from app.services.locked_packages import FINAL_QA_PACKAGE_SHA256


def prepare(destination):
    path = Path(destination).resolve()
    if path.exists():
        raise FileExistsError("Refusing to replace an existing review database")
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine("sqlite:///" + path.as_posix())
    Base.metadata.create_all(engine)
    reference = pd.Timestamp("2025-12-31")
    groups = []
    try:
        with Session(engine) as db:
            for index in range(1, 9):
                name = f"SYNTHETIC CI ACCOUNT {index:02d}"
                db.add(DimAccount(
                    standardized_account_name=name, display_name=name,
                    b2b_priority_eligible=True, account_status="Client-Confirmed Active",
                    entity_type="Company", business_category="Synthetic CI only",
                    verification_basis="Generated test fixture; no real client verification",
                ))
                for number in range(1, index + 1):
                    si = reference - pd.Timedelta(days=index * 12 + number)
                    amount = Decimal(index * 100 + number)
                    groups.append(InvoiceGroup(
                        invoice_group_id=f"ci-{index}-{number}",
                        standardized_account_name=name, si_no=f"CI-{index}-{number}",
                        si_date=si, si_amount=amount, payment_status="Fully Paid",
                        final_cr_date=si + pd.Timedelta(days=index),
                        total_cr_amount=amount, reconciliation_amount=amount,
                        reconciliation_difference=Decimal("0"), reconciled=True,
                    ))
            db.flush()
            names = {group.standardized_account_name for group in groups}
            result = asdict(run_account_prioritization(groups, reference, names))
            run = AnalyticsRun(status="running")
            db.add(run)
            db.flush()
            persist_run_output(db, run, result)
            # Read-contract registry metadata only: no fitted model or inference
            # is claimed. The approved identifiers select the report's evidence
            # branch; the synthetic marker distinguishes this from study proof.
            db.add(PredictiveModelVersion(
                model_version=MODEL_VERSION, artifact_hash=MODEL_ARTIFACT_SHA256,
                status="active", model_family="Synthetic CI registry metadata only",
                model_parameters={"synthetic_ci_fixture": True, "inference_executed": False},
            ))
            db.add(PrescriptiveValidationEvidence(
                evidence_version=EVIDENCE_VERSION, evidence_scope="group_pooled_outcomes",
                comparator="Synthetic CI read-contract fixture",
                source_package_hash=FINAL_QA_PACKAGE_SHA256,
                payload={"synthetic_ci_fixture": True, "source": "Generated test data; not package evidence"},
            ))
            db.commit()
            count = db.scalar(select(func.count()).select_from(AccountPriorityResult))
            assert count == len(names)
            print(json.dumps({"fixture_type": "SYNTHETIC CI ONLY", "ranked_accounts": count,
                              "real_study_reconciliation": False, "model_inference_executed": False}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    prepare(sys.argv[1])
