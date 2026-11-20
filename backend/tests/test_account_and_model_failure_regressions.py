from copy import deepcopy
from datetime import date

import httpx
import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.db.models import (
    AnalyticsRun, AuditLog, Base, DimAccount, ImportBatch, InvoiceGroupRecord,
    PredictiveModelVersion, PredictiveStudyPrediction,
)
from app.db.repository import latest_successful_run, run_payload
from app.main import AccountContextRequest, account_detail, update_account_context
from app.schemas.account_filters import AccountFilters
from app.services.import_workflow import commit_source, preview_source
from app.services.model_lifecycle import future_transaction_for_current_run
from app.services.publication_workflow import publish_existing_source
from app.services.si_coverage import confirm_si_coverage
from app.services.storage import ModelStorage, SourceStorage
from app.services.study_predictions import FORECAST_ORIGIN, MODEL_VERSION


ADMIN = AuthenticatedUser("00000000-0000-4000-8000-000000000001", "administrator")
REFERENCE = date(2025, 12, 31)


@pytest.fixture
def published():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            batch = ImportBatch(file_name="synthetic.csv", file_hash="a" * 64, status="committed")
            db.add(batch)
            db.flush()
            for i, name in enumerate(("ALPHA", "BETA", "GAMMA"), start=1):
                account = DimAccount(
                    standardized_account_name=name, display_name=name, entity_type="Company",
                    business_category="Construction & Engineering", primary_business_type="Construction",
                    b2b_priority_eligible=True, account_status="Client-Confirmed Active",
                    last_verified=date(2026, 9, 19), verification_type="Client confirmation",
                    verification_date=date(2026, 9, 19), verification_basis="Synthetic confirmation",
                    status_confirming_role="PESLC client representative",
                    status_claim_scope="PESLC account actionability",
                    identity_source_type="Client confirmation", identity_source_reference="Synthetic registry",
                )
                db.add(account)
                db.flush()
                db.add(InvoiceGroupRecord(
                    invoice_group_id=f"invoice-{i}", import_batch_id=batch.import_batch_id,
                    account_key=account.account_key, standardized_account_name=name,
                    si_no=f"SI-{i}", si_date=date(2025, i, 1), si_amount=i * 100,
                    payment_status="Fully Paid", final_cr_date=date(2025, i, 15),
                    total_cr_amount=i * 100, total_ewt=0, reconciliation_amount=i * 100,
                    reconciliation_difference=0, reconciled=True, is_cancelled=False,
                    rfm_eligible=True, settlement_eligible=True, settlement_days=14,
                ))
            confirm_si_coverage(
                db, complete_through=REFERENCE, evidence_type="Client confirmation",
                evidence_reference="Synthetic coverage", evidence_basis="Synthetic SI records checked",
                confirmed_on=date(2026, 1, 1), recorded_by=ADMIN.user_id,
                source_batch_id=batch.import_batch_id,
            )
            run = publish_existing_source(db, REFERENCE, ADMIN.user_id, source="isolated_regression")
            db.commit()
            yield db, run
    finally:
        engine.dispose()


@pytest.mark.parametrize("role", ["administrator", "management"])
@pytest.mark.parametrize("include_official", [False, True])
def test_account_details_select_only_the_official_study_prediction(published, role, include_official):
    db, run = published
    account = db.scalar(select(DimAccount).where(DimAccount.standardized_account_name == "ALPHA"))
    for version in (MODEL_VERSION, "older-study-model"):
        db.add(PredictiveModelVersion(model_version=version, status="archived"))
    rows = [("older-study-model", FORECAST_ORIGIN), (MODEL_VERSION, date(2024, 12, 31))]
    if include_official:
        rows.append((MODEL_VERSION, FORECAST_ORIGIN))
    for version, origin in rows:
        db.add(PredictiveStudyPrediction(
            account_key=account.account_key, model_version=version, forecast_origin=origin,
            future_window_start=date(origin.year + 1, 1, 1), future_window_end=date(origin.year + 1, 12, 31),
            predicted_class="With Future Sales" if (version, origin) == (MODEL_VERSION, FORECAST_ORIGIN)
            else "With No Future Sales", source_package_hash="synthetic", source_package_member="synthetic",
        ))
    db.commit()
    before = deepcopy(run_payload(db, run))
    detail = account_detail(account.account_key, AuthenticatedUser(ADMIN.user_id, role), db, AccountFilters())
    if include_official:
        assert detail["study_predictive"] == {
            "predicted_future_transaction_class": "With Future Sales", "model_version": MODEL_VERSION,
            "forecast_origin": FORECAST_ORIGIN.isoformat(), "future_window_start": "2026-01-01",
            "future_window_end": "2026-12-31",
        }
    else:
        assert detail["study_predictive"] is None
    assert run_payload(db, run) == before
    assert latest_successful_run(db).analysis_run_id == run.analysis_run_id


@pytest.mark.parametrize("change,status_cleared,identity_cleared", [
    ({}, False, False),
    ({"verification_date": "2026-09-20"}, True, False),
    ({"last_verified": "2026-09-20"}, True, False),
    ({"business_category": "Industrial Services"}, False, True),
])
def test_context_save_preserves_unchanged_provenance_and_invalidates_actual_changes(
    published, change, status_cleared, identity_cleared,
):
    db, run = published
    account = db.scalar(select(DimAccount).where(DimAccount.standardized_account_name == "ALPHA"))
    values = {name: getattr(account, name) for name in AccountContextRequest.model_fields}
    values.update(change)
    request = AccountContextRequest.model_validate(values)
    before = deepcopy(run_payload(db, run))
    update_account_context(account.account_key, request, ADMIN, db)
    db.refresh(account)
    assert account.status_confirming_role == (None if status_cleared else "PESLC client representative")
    assert account.status_claim_scope == (None if status_cleared else "PESLC account actionability")
    assert account.identity_source_reference == (None if identity_cleared else "Synthetic registry")
    assert isinstance(account.verification_date, date)
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "account_context_updated"))
    if not change:
        assert audit.details["previous"] == audit.details["updated"]
    assert run_payload(db, run) == before
    assert latest_successful_run(db).analysis_run_id == run.analysis_run_id


def unavailable_storage(monkeypatch, db, error_type=httpx.ReadTimeout):
    model = PredictiveModelVersion(
        model_version=MODEL_VERSION, status="active", model_family="CatBoostClassifier",
        artifact_path="synthetic.joblib", artifact_hash=DEFAULT_ANALYTICS_CONFIG.model_sha256,
    )
    db.add(model)
    db.commit()

    def fail_read(self, path):
        if error_type is httpx.HTTPStatusError:
            request = httpx.Request("GET", "https://storage.invalid/synthetic.joblib")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("Synthetic unavailable storage", request=request, response=response)
        raise error_type("Synthetic storage failure; no network request")

    monkeypatch.setattr(ModelStorage, "get", fail_read)
    return model


@pytest.mark.parametrize("error_type", [
    httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError, httpx.HTTPStatusError,
])
def test_model_storage_http_failures_produce_explicit_unavailable_predictions(published, monkeypatch, error_type):
    db, run = published
    before = deepcopy(run_payload(db, run))
    model = unavailable_storage(monkeypatch, db, error_type)
    result = future_transaction_for_current_run(db, [], pd.Timestamp(REFERENCE), {"ALPHA"})
    assert result.status == "model_unavailable"
    assert result.predictions == {}
    assert result.model_version == MODEL_VERSION
    assert model.review_recommended is True
    assert model.status == "active"
    assert model.artifact_hash == DEFAULT_ANALYTICS_CONFIG.model_sha256
    assert run_payload(db, run) == before


@pytest.mark.parametrize("require_validated_model", [False, True])
def test_timeout_respects_publication_model_gate_and_preserves_previous_run(
    published, monkeypatch, require_validated_model,
):
    db, previous = published
    before = deepcopy(run_payload(db, previous))
    unavailable_storage(monkeypatch, db)
    if require_validated_model:
        with pytest.raises(ValueError, match="artifact is not validated"):
            publish_existing_source(db, REFERENCE, ADMIN.user_id, source="isolated_regression",
                                    require_validated_model=True)
        db.rollback()
        assert latest_successful_run(db).analysis_run_id == previous.analysis_run_id
    else:
        current = publish_existing_source(db, REFERENCE, ADMIN.user_id, source="isolated_regression")
        db.commit()
        output = run_payload(db, current)
        assert output["predictive"]["status"] == "model_unavailable"
        assert output["predictive"]["predictions"] == {}
        assert len(output["priorities"]) == 3
        assert latest_successful_run(db).analysis_run_id == current.analysis_run_id
    assert run_payload(db, previous) == before


def test_import_timeout_publishes_nonpredictive_results_without_rewriting_previous_run(published, monkeypatch):
    db, previous = published
    before = deepcopy(run_payload(db, previous))
    unavailable_storage(monkeypatch, db)
    content = (
        "ACCOUNT NAMES,SI NO.,SI DATE,SI AMOUNT,CR NO.,CR DATE,CR AMOUNT,EWT,PAYMENT MODE,PAYMENT STATUS\n"
        "ALPHA,SI-NEW,2025-11-01,150,CR-NEW,2025-11-15,150,0,Bank,Fully Paid\n"
    ).encode()
    monkeypatch.setattr(SourceStorage, "put", lambda *args: "synthetic-source")
    monkeypatch.setattr(SourceStorage, "get", lambda *args: content)
    preview = preview_source(db, ADMIN, "synthetic.csv", content)
    confirm_si_coverage(
        db, complete_through=REFERENCE, evidence_type="Client confirmation",
        evidence_reference="Synthetic import coverage", evidence_basis="Synthetic SI records checked",
        confirmed_on=date(2026, 1, 1), recorded_by=ADMIN.user_id,
        source_batch_id=preview["import_batch_id"],
    )
    db.commit()
    committed = commit_source(db, ADMIN, preview["import_batch_id"], REFERENCE)
    assert committed["status"] == "COMMITTED"
    current = db.get(AnalyticsRun, committed["analysis_run_id"])
    output = run_payload(db, current)
    assert output["predictive"]["status"] == "model_unavailable"
    assert output["predictive"]["predictions"] == {}
    assert len(output["priorities"]) == 3
    assert latest_successful_run(db).analysis_run_id == current.analysis_run_id
    assert run_payload(db, previous) == before
