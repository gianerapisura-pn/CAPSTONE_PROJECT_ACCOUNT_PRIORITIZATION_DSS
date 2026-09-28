from __future__ import annotations
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, datetime, timezone
from io import BytesIO
import json
import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from app.auth.dependencies import AuthenticatedUser, require_admin, require_user
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.core.config import get_settings, validate_runtime_configuration
from app.db.models import (
    AccountAlias, AccountAliasReview, AnalyticsRun, CollectionCorrectionReview, DimAccount, ImportBatch,
    ImportRowIssue, InvoiceGroupRecord, RFMResult, SensitivityScenarioRecord,
    SettlementResult,
)
from app.db.repository import (
    CLIENT_CONFIRMED_ACTIVE,
    CLIENT_CONFIRMED_CLOSED,
    audit,
    b2b_analytical_accounts,
    current_account_rows,
    current_actionable_accounts,
    filter_current_account_rows,
    latest_successful_run,
    load_invoice_groups,
    persist_run_output,
    run_payload,
    serialize_run,
)
from app.db.session import get_db, init_database
from app.imports.validators import REQUIRED_COLUMNS
from app.schemas.api import (
    AccountListResponse, AccountPriorityResponse, AnalyticsRunResponse, ImportBatchResponse,
    ImportCommitResponse, ImportDetailResponse, ImportPreviewResponse, ModelSummaryResponse,
)
from app.services.analytics_runner import run_account_prioritization, validate_analysis_reference
from app.services.import_workflow import (
    commit_source, preview_source, resolve_collection_correction,
)
from app.services.model_lifecycle import (
    active_model_version, future_transaction_for_current_run, monitor_registered_predictions,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_configuration(settings)
    init_database()
    yield


app = FastAPI(title="PESLC Account Prioritization DSS API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class CommitRequest(BaseModel):
    analysis_reference_date: date


class RunRequest(BaseModel):
    analysis_reference_date: date


class MonitorRequest(BaseModel):
    as_of_date: date


class AliasDecisionRequest(BaseModel):
    status: str
    canonical_account_name: str | None = None
    reason: str


class CollectionCorrectionDecisionRequest(BaseModel):
    selected_raw_source_row_id: str
    reason: str

class AccountContextRequest(BaseModel):
    entity_type: str | None = None
    business_category: str | None = None
    primary_business_type: str | None = None
    b2b_priority_eligible: bool
    account_status: str | None = None
    last_verified: date | None = None
    verification_type: str | None = None
    verification_date: date | None = None
    verification_basis: str | None = None


ACCOUNT_ENTITY_TYPES = {
    "Company",
    "Property/Building",
    "Condominium Association",
    "Educational Institution",
    "Religious/Nonprofit Institution",
    "Individual/Personal",
    "Other Business/Organization",
}
VERIFIED_ACCOUNT_STATUSES = {
    CLIENT_CONFIRMED_ACTIVE,
    CLIENT_CONFIRMED_CLOSED,
}


def _latest_or_404(db):
    run = latest_successful_run(db)
    if not run:
        raise HTTPException(404, "No successful analytical run is available.")
    return run


def _safe(value):
    return "'" + value if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"} else value


def _currency(column):
    leaf = column.rsplit(".", 1)[-1].lower()
    return (not leaf.endswith("_contribution") and
            (leaf in {"monetary", "monetary_value", "valid_si_sales"} or
             leaf.endswith("_amount") or leaf.endswith("_sales")))


def _batch(row):
    return {
        "import_batch_id": row.import_batch_id, "file_name": row.file_name,
        "file_hash": row.file_hash, "uploaded_by": row.uploaded_by,
        "uploaded_at": row.uploaded_at.isoformat(),
        "committed_at": row.committed_at.isoformat() if row.committed_at else None,
        "status": row.status, "rows_discovered": row.rows_discovered,
        "rows_accepted": row.rows_accepted, "rows_flagged": row.rows_flagged,
        "rows_excluded": row.rows_excluded, "cancelled_count": row.cancelled_count,
        "analysis_run_id": row.analysis_run_id,
        "analysis_reference_date": (row.analysis_reference_date.isoformat()
                                    if row.analysis_reference_date else None),
    }


@app.get("/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode, "environment": settings.app_env}


@app.get("/auth/me")
def me(user: AuthenticatedUser = Depends(require_user)):
    return asdict(user)


@app.get("/account-aliases/review")
def alias_queue(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"alias_review_id": x.alias_review_id, "candidate_name": x.candidate_name,
             "possible_canonical_name": x.possible_canonical_name, "status": x.status,
             "reviewed_by": x.reviewed_by,
             "reviewed_at": x.reviewed_at.isoformat() if x.reviewed_at else None,
             "reason": x.reason}
            for x in db.scalars(select(AccountAliasReview).order_by(
                AccountAliasReview.status, AccountAliasReview.candidate_name)).all()]


@app.post("/account-aliases/review/{review_id}")
def decide_alias(review_id: str, request: AliasDecisionRequest,
                 user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(AccountAliasReview, review_id)
    if not row:
        raise HTTPException(404, "Alias review candidate not found.")
    decision, reason = request.status.strip().lower(), request.reason.strip()
    canonical = (request.canonical_account_name or row.possible_canonical_name or "").strip()
    if decision not in {"approved", "rejected"} or not reason:
        raise HTTPException(422, "An approved/rejected decision and reason are required.")
    if decision == "approved" and not canonical:
        raise HTTPException(422, "A canonical account name is required.")
    if decision == "approved":
        alias = db.scalar(select(AccountAlias).where(AccountAlias.alias_name == row.candidate_name))
        if alias:
            alias.canonical_account_name, alias.approved_by = canonical, user.user_id
            alias.approved_at, alias.reason = datetime.now(timezone.utc), reason
        else:
            db.add(AccountAlias(alias_name=row.candidate_name,
                                canonical_account_name=canonical,
                                approved_by=user.user_id, reason=reason))
    row.status, row.reviewed_by, row.reason = decision, user.user_id, reason
    row.reviewed_at = datetime.now(timezone.utc)
    row.possible_canonical_name = canonical or row.possible_canonical_name
    audit(db, user.user_id, "alias_review_decided", "account_alias_review", review_id,
          {"status": decision, "canonical_account_name": canonical or None})
    db.commit()
    return {"alias_review_id": review_id, "status": decision,
            "canonical_account_name": canonical or None}


@app.get("/collection-corrections")
def collection_correction_queue(
    status: str = Query("pending", pattern="^(pending|resolved|all)$"),
    user: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(CollectionCorrectionReview).order_by(
        CollectionCorrectionReview.status,
        CollectionCorrectionReview.detected_at,
    )).all()
    return [{
        "collection_correction_review_id": row.collection_correction_review_id,
        "collection_identity": row.collection_identity,
        "invoice_identity": row.invoice_identity,
        "raw_source_row_ids": row.raw_source_row_ids or [],
        "status": row.status,
        "selected_raw_source_row_id": row.selected_raw_source_row_id,
        "detected_at": row.detected_at.isoformat(),
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "reason": row.reason,
    } for row in rows if status == "all" or row.status == status]


@app.post("/collection-corrections/{review_id}/resolve")
def resolve_correction(
    review_id: str,
    request: CollectionCorrectionDecisionRequest,
    user: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = resolve_collection_correction(
        db, user, review_id, request.selected_raw_source_row_id, request.reason
    )
    db.commit()
    return {
        "collection_correction_review_id": row.collection_correction_review_id,
        "status": row.status,
        "selected_raw_source_row_id": row.selected_raw_source_row_id,
        "analytics_publication_required": True,
    }

@app.get("/account-context")
def account_context_queue(
    status: str = Query("pending", pattern="^(pending|all)$"),
    user: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(DimAccount).order_by(DimAccount.standardized_account_name)).all()
    items = []
    for row in rows:
        basic_pending = any(value in (None, "") for value in (
            row.entity_type,
            row.business_category,
            row.primary_business_type,
        ))
        verified_b2b_pending = row.b2b_priority_eligible and any(
            value in (None, "") for value in (
                row.account_status,
                row.last_verified,
                row.verification_type,
                row.verification_date,
                row.verification_basis,
            )
        )
        pending = basic_pending or verified_b2b_pending
        if status == "pending" and not pending:
            continue
        items.append({
            "account_key": row.account_key,
            "account": row.standardized_account_name,
            "display_name": row.display_name,
            "entity_type": row.entity_type,
            "business_category": row.business_category,
            "primary_business_type": row.primary_business_type,
            "account_status": row.account_status,
            "last_verified": row.last_verified.isoformat() if row.last_verified else None,
            "verification_type": row.verification_type,
            "verification_date": (
                row.verification_date.isoformat() if row.verification_date else None
            ),
            "verification_basis": row.verification_basis,
            "b2b_priority_eligible": row.b2b_priority_eligible,
            "current_actionable": (
                row.b2b_priority_eligible
                and row.account_status == CLIENT_CONFIRMED_ACTIVE
            ),
            "verification_status": "pending" if pending else "verified",
        })
    return {
        "items": items,
        "total": len(items),
        "publication_note": (
            "Context changes do not mutate a published run. Run analytics explicitly to publish "
            "a new immutable decision result."
        ),
    }

@app.patch("/account-context/{account_key}")
def update_account_context(account_key: str, request: AccountContextRequest,
                           user: AuthenticatedUser = Depends(require_admin),
                           db: Session = Depends(get_db)):
    row = db.get(DimAccount, account_key)
    if not row:
        raise HTTPException(404, "Account not found.")
    values = request.model_dump()
    required = ("entity_type", "business_category", "primary_business_type")
    if any(values.get(field) in (None, "") for field in required):
        raise HTTPException(422, "Complete account identity context is required.")
    if values["entity_type"] not in ACCOUNT_ENTITY_TYPES:
        raise HTTPException(422, "Entity type is outside the controlled taxonomy.")
    if values["b2b_priority_eligible"] and values["entity_type"] == "Individual/Personal":
        raise HTTPException(422, "Individual/Personal context cannot be marked B2B eligible.")
    if values["account_status"] and values["account_status"] not in VERIFIED_ACCOUNT_STATUSES:
        raise HTTPException(422, "Account status is outside the controlled verified statuses.")
    if values["b2b_priority_eligible"]:
        provenance = (
            "account_status", "last_verified", "verification_type",
            "verification_date", "verification_basis",
        )
        if any(values.get(field) in (None, "") for field in provenance):
            raise HTTPException(
                422, "Verified B2B context requires status, dates, and provenance."
            )
        if values["verification_type"] != "Client confirmation":
            raise HTTPException(
                422, "Current verified status requires Client confirmation provenance."
            )
    previous = {
        field: getattr(row, field).isoformat() if isinstance(getattr(row, field), date)
        else getattr(row, field)
        for field in values
    }
    for field, value in values.items():
        setattr(row, field, value)
    audit(db, user.user_id, "account_context_updated", "dim_account", account_key, {
        "previous": previous,
        "updated": request.model_dump(mode="json"),
        "publication_required": True,
    })
    db.commit()
    return {
        "account_key": account_key,
        **request.model_dump(mode="json"),
        "publication_required": True,
    }


@app.post("/imports/preview", response_model=ImportPreviewResponse)
async def preview_import(file: UploadFile = File(...),
                         user: AuthenticatedUser = Depends(require_admin),
                         db: Session = Depends(get_db)):
    return preview_source(db, user, file.filename or "upload", await file.read())


@app.post("/imports/{batch_id}/commit", response_model=ImportCommitResponse)
def commit_import(batch_id: str, request: CommitRequest,
                  user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)):
    return commit_source(db, user, batch_id, request.analysis_reference_date)


@app.get("/imports", response_model=list[ImportBatchResponse])
def imports(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    return [_batch(x) for x in db.scalars(
        select(ImportBatch).order_by(desc(ImportBatch.uploaded_at))).all()]


@app.get("/imports/{batch_id}/issues.csv")
def import_issues(batch_id: str, user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)):
    rows = db.scalars(select(ImportRowIssue).where(
        ImportRowIssue.import_batch_id == batch_id)).all()
    frame = pd.DataFrame([{"source_sheet": x.source_sheet, "row_number": x.row_number,
                           "column": x.column_name, "issue_type": x.issue_type,
                           "severity": x.severity, "message": x.message} for x in rows])
    return Response(frame.to_csv(index=False), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{batch_id}-issues.csv"'})


@app.get("/imports/template.{format}")
def import_template(format: str, user: AuthenticatedUser = Depends(require_admin)):
    frame = pd.DataFrame(columns=REQUIRED_COLUMNS)
    if format == "csv":
        return Response(frame.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="peslc-import-template.csv"'})
    if format == "xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            frame.to_excel(writer, sheet_name="Source Data", index=False)
        return Response(output.getvalue(),
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": 'attachment; filename="peslc-import-template.xlsx"'})
    raise HTTPException(404, "Template format not found.")


@app.get("/imports/{batch_id}", response_model=ImportDetailResponse)
def import_detail(batch_id: str, user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Import batch not found.")
    issues = db.scalars(select(ImportRowIssue).where(
        ImportRowIssue.import_batch_id == batch_id)
        .order_by(ImportRowIssue.source_sheet, ImportRowIssue.row_number)).all()
    counts = {}
    for row in issues:
        counts[row.issue_type] = counts.get(row.issue_type, 0) + 1
    result = _batch(batch)
    result.update({
        "issues": [{"source_sheet": x.source_sheet, "row_number": x.row_number,
                    "column": x.column_name, "issue_type": x.issue_type,
                    "severity": x.severity, "message": x.message} for x in issues],
        "quality_issue_rates": {key: value / max(batch.rows_discovered, 1)
                                for key, value in sorted(counts.items())},
        "cancelled_row_rate": batch.cancelled_count / max(batch.rows_discovered, 1),
    })
    return result


@app.post("/analytics/run")
def run_analytics(request: RunRequest, user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)):
    groups = load_invoice_groups(db)
    if not groups:
        raise HTTPException(422, "No committed invoice data is available.")
    try:
        validate_analysis_reference(groups, pd.Timestamp(request.analysis_reference_date))
        b2b_accounts = b2b_analytical_accounts(db)
        actionable_accounts = current_actionable_accounts(db)
        predictive = future_transaction_for_current_run(
            db, groups, pd.Timestamp(request.analysis_reference_date), b2b_accounts)
        result = asdict(run_account_prioritization(
            groups, pd.Timestamp(request.analysis_reference_date), b2b_accounts,
            actionable_accounts, predictive_result=predictive))
        run = AnalyticsRun(status="running",
                           analysis_reference_date=request.analysis_reference_date,
                           methodology_version=DEFAULT_ANALYTICS_CONFIG.version,
                           code_version=DEFAULT_ANALYTICS_CONFIG.version)
        db.add(run)
        db.flush()
        persist_run_output(db, run, result)
        audit(db, user.user_id, "analytics_run", "analytics_run", run.analysis_run_id,
              {"analysis_reference_date": request.analysis_reference_date.isoformat()})
        db.commit()
        return serialize_run(run)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, "Analytics run failed; the previous successful run remains current.") from exc


@app.get("/analytics/latest")
def latest_analytics(user: AuthenticatedUser = Depends(require_admin),
                     db: Session = Depends(get_db)):
    return run_payload(db, _latest_or_404(db))


@app.get("/dashboard")
def dashboard(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)):
    run, payload = _latest_or_404(db), None
    payload = run_payload(db, run)
    priorities, accounts = payload["priorities"], payload["accounts"]
    classes = ("Future Transaction", "No Future Transaction")
    return {
        "run": serialize_run(run),
        "historical_identities": int(
            payload["context_metrics"].get("historical_account_count", 0)
        ),
        "b2b_analytical_accounts": len(accounts),
        "current_actionable_accounts": sum(x["current_actionable"] for x in accounts),
        "total_standardized_accounts": len(accounts),
        "mcs_eligible_accounts": sum(x["mcs_eligible"] for x in accounts),
        "ranked_accounts": sum(x["is_ranked"] for x in accounts),
        "priority_group_counts": {x: sum(r["priority_group"] == x for r in priorities)
                                  for x in ("High", "Medium", "Low")},
        "prediction_class_counts": {
            x: sum(r.get("predicted_future_transaction_class") == x for r in accounts)
            for x in classes},
        "total_valid_historical_sales": sum(
            x.get("all_recorded_sales", 0) for x in payload["business_baselines"]),
        "warnings": run.warnings or [], "top_accounts": priorities[:8],
        "stability": ({"minimum_spearman": min(x["min_spearman"] for x in payload["sensitivity"]),
                       "maximum_group_movement_rate": max(
                           x["max_group_movement_rate"] for x in payload["sensitivity"])}
                      if payload["sensitivity"] else None),
    }


@app.get("/accounts/priorities", response_model=list[AccountPriorityResponse])
def account_priorities(user: AuthenticatedUser = Depends(require_user),
                       db: Session = Depends(get_db)):
    return run_payload(db, _latest_or_404(db))["priorities"]


@app.get("/accounts", response_model=AccountListResponse)
def accounts(search: str = "", priority_group: str | None = None,
             predicted_future_transaction_class: str | None = None,
             eligibility: str | None = Query(None, pattern="^(ranked|not_ranked)$"),
             page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=500),
             user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)):
    run = _latest_or_404(db)
    rows = filter_current_account_rows(
        current_account_rows(db, run), search, priority_group,
        predicted_future_transaction_class, eligibility)
    start = (page - 1) * page_size
    reference = run.analysis_reference_date or run.cutoff_date
    return {"items": rows[start:start + page_size], "total": len(rows), "page": page,
            "page_size": page_size, "analysis_run_id": run.analysis_run_id,
            "analysis_reference_date": reference.isoformat() if reference else None,
            "updated_at": run.completed_at.isoformat() if run.completed_at else None}


@app.get("/accounts/{account_key}")
def account_detail(account_key: str, user: AuthenticatedUser = Depends(require_user),
                   db: Session = Depends(get_db)):
    account = db.get(DimAccount, account_key) or db.scalar(select(DimAccount).where(
        DimAccount.standardized_account_name == account_key))
    if not account:
        raise HTTPException(404, "Account not found.")
    run = _latest_or_404(db)
    decision = next((x for x in current_account_rows(db, run)
                     if x["account_key"] == account.account_key), None)
    if not decision:
        raise HTTPException(404, "Account is not part of the latest verified B2B run.")
    rfm = db.scalar(select(RFMResult).where(RFMResult.analysis_run_id == run.analysis_run_id,
                                            RFMResult.account_key == account.account_key))
    settlement = db.scalar(select(SettlementResult).where(
        SettlementResult.analysis_run_id == run.analysis_run_id,
        SettlementResult.account_key == account.account_key))
    transactions = db.scalars(select(InvoiceGroupRecord).where(
        InvoiceGroupRecord.account_key == account.account_key)
        .order_by(desc(InvoiceGroupRecord.si_date))).all()
    scenarios = db.scalars(select(SensitivityScenarioRecord).where(
        SensitivityScenarioRecord.analysis_run_id == run.analysis_run_id,
        SensitivityScenarioRecord.account_key == account.account_key)).all()
    ranks = [x.payload["scenario_rank"] for x in scenarios]
    return {
        "account_key": account.account_key, "account": decision["account"],
        "context": {key: decision.get(key) for key in (
            "entity_type", "business_category", "primary_business_type",
            "b2b_priority_eligible", "account_status", "last_verified",
            "verification_type", "verification_date", "verification_basis",
            "current_actionable")},
        "decision": decision, "priority": decision if decision["is_ranked"] else None,
        "rfm": rfm.payload if rfm else None,
        "settlement": settlement.payload if settlement else None,
        "predictive": {
            "predicted_future_transaction_class":
                decision["predicted_future_transaction_class"],
            "model_version": decision["model_version"]},
        "critic_weights": run.critic_weights or {},
        "sensitivity": ({"minimum_rank": min(ranks), "maximum_rank": max(ranks),
                         "group_movement_rate": sum(
                             bool(x.payload["group_changed"]) for x in scenarios) / len(scenarios)}
                        if scenarios else None),
        "transactions": [{"invoice_group_id": x.invoice_group_id, "si_no": x.si_no,
                          "si_date": x.si_date.isoformat(), "si_amount": float(x.si_amount),
                          "final_cr_date": x.final_cr_date.isoformat() if x.final_cr_date else None,
                          "payment_status": x.payment_status, "reconciled": x.reconciled,
                          "review_reason": x.review_reason,
                          "import_batch_id": x.import_batch_id} for x in transactions],
    }


@app.get("/analytics/rfm")
def rfm(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    run = _latest_or_404(db)
    return {"analysis_run_id": run.analysis_run_id,
            "analysis_reference_date": serialize_run(run)["analysis_reference_date"],
            "items": run_payload(db, run)["rfm"]}


@app.get("/analytics/settlement")
def settlement(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    run = _latest_or_404(db)
    return {"analysis_run_id": run.analysis_run_id,
            "analysis_reference_date": serialize_run(run)["analysis_reference_date"],
            "items": run_payload(db, run)["settlement"]}


@app.get("/analytics/predictive")
def predictive(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    return run_payload(db, _latest_or_404(db))["predictive"]


@app.get("/analytics/cart", include_in_schema=False)
def cart_redirect(user: AuthenticatedUser = Depends(require_admin)):
    return RedirectResponse("/analytics/predictive", status_code=308)


@app.get("/analytics/sensitivity")
def sensitivity(account_key: str | None = None,
                user: AuthenticatedUser = Depends(require_admin),
                db: Session = Depends(get_db)):
    run, payload = _latest_or_404(db), None
    payload = run_payload(db, run)
    details = []
    if account_key:
        details = [x.payload for x in db.scalars(select(SensitivityScenarioRecord).where(
            SensitivityScenarioRecord.analysis_run_id == run.analysis_run_id,
            SensitivityScenarioRecord.account_key == account_key)).all()]
    return {"analysis_run_id": run.analysis_run_id, "critic_weights": run.critic_weights,
            "summaries": payload["sensitivity"], "critic_influence": payload["critic_influence"],
            "account_scenarios": details}


@app.get("/runs")
@app.get("/analytics/runs", response_model=list[AnalyticsRunResponse])
def runs(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    return [serialize_run(x) for x in db.scalars(
        select(AnalyticsRun).order_by(desc(AnalyticsRun.started_at))).all()]


@app.get("/analytics/runs/{run_id}")
def run_detail(run_id: str, user: AuthenticatedUser = Depends(require_admin),
               db: Session = Depends(get_db)):
    run = db.get(AnalyticsRun, run_id)
    if not run:
        raise HTTPException(404, "Analytics run not found.")
    return run_payload(db, run)


@app.get("/models/current", response_model=ModelSummaryResponse)
def current_model(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)):
    model = active_model_version(db)
    if not model:
        return {"status": "model_unavailable", "model_version": None}
    return {"status": model.status, "model_version": model.model_version,
            "model_family": model.model_family, "created_at": model.created_at,
            "trained_through_date": model.trained_through_date,
            "selected_outcome_horizon": model.selected_outcome_horizon,
            "retained_features": model.retained_features,
            "decision_threshold": model.decision_threshold,
            "artifact_hash": model.artifact_hash,
            "last_validation_date": model.last_validation_date,
            "review_recommended": model.review_recommended,
            "development_metrics": model.development_metrics,
            "validation_metrics": model.oop_metrics}


@app.post("/models/monitor")
def monitor(request: MonitorRequest, user: AuthenticatedUser = Depends(require_admin),
            db: Session = Depends(get_db)):
    result = monitor_registered_predictions(db, load_invoice_groups(db), request.as_of_date)
    audit(db, user.user_id, "model_monitor", "predictive_model", None,
          {"status": result["status"], "as_of_date": request.as_of_date.isoformat()})
    db.commit()
    return result


@app.get("/settings/methodology")
def methodology(user: AuthenticatedUser = Depends(require_admin)):
    return {
        "source_schema": list(REQUIRED_COLUMNS),
        "analytics_config": DEFAULT_ANALYTICS_CONFIG.serializable(),
        "analysis_reference_date": "Administrator-selected and not earlier than accepted SI/CR evidence.",
        "eligibility": ("Explicitly verified B2B accounts enter RFM and prediction; "
                        "current MCS additionally requires Client-Confirmed Active status "
                        "and complete decision criteria."),
        "rfm": "q20/q40/q60/q80 empirical quintiles with linear interpolation and ties preserved.",
        "settlement": "Observed SI-to-final-valid-CR duration using only cutoff-known, reconciled, nonnegative evidence.",
        "predictive": "Frozen Extra Trees stage-8 artifact; 12-month Future Transaction target; seven cutoff-safe predictors.",
        "mcs": "CRITIC weights normalized Recency, Frequency, Monetary, and Historical Settlement Duration.",
        "priority_groups": "Tie-preserving ranked thirds from each discriminatory four-criterion run.",
        "backtest": "Seven annual cutoffs (2018-2024) with exact k/n random expectation.",
        "future_data_rule": "Years and accounts are derived from validated committed data.",
    }


@app.get("/exports/{dataset}.{format}")
def export(dataset: str, format: str, search: str = "", priority_group: str | None = None,
           predicted_future_transaction_class: str | None = None,
           eligibility: str | None = Query(None, pattern="^(ranked|not_ranked)$"),
           user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)):
    supported = {"priorities", "rfm", "settlement", "sensitivity", "runs",
                 "predictive", "transactions"}
    if dataset not in supported or format not in {"csv", "xlsx"}:
        raise HTTPException(404, "Export dataset or format not found.")
    if dataset != "priorities" and user.role != "administrator":
        raise HTTPException(403, "Administrator permission is required.")
    run, payload = _latest_or_404(db), None
    payload = run_payload(db, run)
    sources = {
        "priorities": filter_current_account_rows(
            payload["accounts"], search, priority_group,
            predicted_future_transaction_class, eligibility),
        "rfm": payload["rfm"], "settlement": payload["settlement"],
        "sensitivity": payload["sensitivity"], "runs": [serialize_run(run)],
        "predictive": [payload["predictive"]],
        "transactions": [{"account": x.standardized_account_name, "si_no": x.si_no,
                          "si_date": x.si_date, "si_amount": float(x.si_amount),
                          "final_cr_date": x.final_cr_date,
                          "import_batch_id": x.import_batch_id}
                         for x in db.scalars(select(InvoiceGroupRecord)).all()],
    }
    rows = [{key: _safe(value) for key, value in row.items()} for row in sources[dataset]]
    frame = pd.json_normalize(rows)
    if "analysis_run_id" not in frame:
        frame.insert(0, "analysis_run_id", run.analysis_run_id)
    if "analysis_reference_date" not in frame:
        frame.insert(1, "analysis_reference_date",
                     serialize_run(run)["analysis_reference_date"])
    audit(db, user.user_id, "export", dataset, run.analysis_run_id, {"format": format})
    db.commit()
    name = f"peslc-{dataset}-{run.analysis_run_id}.{format}"
    currency = [x for x in frame.columns if _currency(x)]
    if format == "csv":
        copy = frame.copy()
        for column in currency:
            copy[column] = copy[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.2f}")
        return Response(copy.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=dataset[:31])
        sheet = writer.sheets[dataset[:31]]
        for column in currency:
            position = frame.columns.get_loc(column) + 1
            for cells in sheet.iter_cols(min_col=position, max_col=position,
                                         min_row=2, max_row=sheet.max_row):
                for cell in cells:
                    cell.number_format = "#,##0.00"
    return Response(output.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/exports/priorities")
def export_priorities(format: str = Query("csv", pattern="^(csv|xlsx)$"),
                      search: str = "", priority_group: str | None = None,
                      predicted_future_transaction_class: str | None = None,
                      eligibility: str | None = Query(None, pattern="^(ranked|not_ranked)$"),
                      user: AuthenticatedUser = Depends(require_user),
                      db: Session = Depends(get_db)):
    return export("priorities", format, search, priority_group,
                  predicted_future_transaction_class, eligibility, user, db)
