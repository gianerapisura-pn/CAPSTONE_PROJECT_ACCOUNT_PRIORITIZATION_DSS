from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from io import BytesIO

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser, require_admin, require_user
from app.core.analytics_config import DEFAULT_ANALYTICS_CONFIG
from app.core.config import get_settings
from app.db.models import (
    AccountAlias, AccountAliasReview, AccountPriorityResult, AnalyticsRun, DimAccount, ImportBatch,
    ImportRowIssue, InvoiceGroupRecord, ModelRun, RFMResult, SensitivityScenarioRecord,
    PredictiveModelVersion, SensitivitySummaryRecord, SettlementResult,
)
from app.db.repository import audit, latest_successful_run, load_invoice_groups, persist_run_output, run_payload, serialize_run
from app.db.session import get_db, init_database
from app.imports.validators import REQUIRED_COLUMNS
from app.services.analytics_runner import run_account_prioritization
from app.services.import_workflow import commit_source, preview_source
from app.services.model_lifecycle import (
    active_model_version, cart_for_current_run, monitor_active_model,
    train_and_persist_model,
)
from app.schemas.api import (
    AccountPriorityResponse, AnalyticsRunResponse, ImportBatchResponse,
    ImportCommitResponse, ImportDetailResponse, ImportPreviewResponse,
    ModelSummaryResponse,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="PESLC Account Prioritization DSS API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


class CommitRequest(BaseModel):
    override_reason: str | None = None


class AliasDecisionRequest(BaseModel):
    status: str
    canonical_account_name: str | None = None
    reason: str


def _latest_or_404(db: Session) -> AnalyticsRun:
    run = latest_successful_run(db)
    if not run:
        raise HTTPException(404, "No successful analytical run is available.")
    return run


def _safe_sheet_value(value: object) -> object:
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


def _serialize_import_batch(row: ImportBatch) -> dict:
    return {
        "import_batch_id": row.import_batch_id, "file_name": row.file_name,
        "file_hash": row.file_hash, "uploaded_by": row.uploaded_by,
        "uploaded_at": row.uploaded_at.isoformat(),
        "committed_at": row.committed_at.isoformat() if row.committed_at else None,
        "status": row.status, "rows_discovered": row.rows_discovered,
        "rows_accepted": row.rows_accepted, "rows_flagged": row.rows_flagged,
        "rows_excluded": row.rows_excluded, "cancelled_count": row.cancelled_count,
        "analysis_run_id": row.analysis_run_id, "override_reason": row.override_reason,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode, "environment": settings.app_env}


@app.get("/auth/me")
def me(user: AuthenticatedUser = Depends(require_user)) -> dict:
    return asdict(user)


@app.get("/account-aliases/review")
def alias_review_queue(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AccountAliasReview).order_by(AccountAliasReview.status, AccountAliasReview.candidate_name)).all()
    return [{
        "alias_review_id": row.alias_review_id, "candidate_name": row.candidate_name,
        "possible_canonical_name": row.possible_canonical_name, "status": row.status,
        "reviewed_by": row.reviewed_by, "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "reason": row.reason,
    } for row in rows]


@app.post("/account-aliases/review/{review_id}")
def decide_alias(review_id: str, request: AliasDecisionRequest,
                 user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    from datetime import datetime, timezone

    row = db.get(AccountAliasReview, review_id)
    if not row:
        raise HTTPException(404, "Alias review candidate not found.")
    decision = request.status.strip().lower()
    reason = request.reason.strip()
    if decision not in {"approved", "rejected"} or not reason:
        raise HTTPException(422, "An approved/rejected decision and reason are required.")
    canonical = (request.canonical_account_name or row.possible_canonical_name or "").strip()
    if decision == "approved" and not canonical:
        raise HTTPException(422, "A canonical account name is required for approval.")
    if decision == "approved":
        existing = db.scalar(select(AccountAlias).where(AccountAlias.alias_name == row.candidate_name))
        if existing:
            existing.canonical_account_name = canonical
            existing.approved_by = user.user_id
            existing.approved_at = datetime.now(timezone.utc)
            existing.reason = reason
        else:
            db.add(AccountAlias(alias_name=row.candidate_name, canonical_account_name=canonical,
                                approved_by=user.user_id, reason=reason))
    row.status = decision
    row.possible_canonical_name = canonical or row.possible_canonical_name
    row.reviewed_by = user.user_id
    row.reviewed_at = datetime.now(timezone.utc)
    row.reason = reason
    audit(db, user.user_id, "alias_review_decided", "account_alias_review", review_id,
          {"status": decision, "canonical_account_name": canonical or None, "reason": reason})
    db.commit()
    return {"alias_review_id": review_id, "status": decision, "canonical_account_name": canonical or None}


@app.post("/imports/preview", response_model=ImportPreviewResponse)
async def preview_import(file: UploadFile = File(...), user: AuthenticatedUser = Depends(require_admin),
                         db: Session = Depends(get_db)) -> dict:
    return preview_source(db, user, file.filename or "upload", await file.read())


@app.post("/imports/{batch_id}/commit", response_model=ImportCommitResponse)
def commit_import(batch_id: str, request: CommitRequest, user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)) -> dict:
    return commit_source(db, user, batch_id, request.override_reason)


@app.get("/imports", response_model=list[ImportBatchResponse])
def import_history(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    batches = db.scalars(select(ImportBatch).order_by(desc(ImportBatch.uploaded_at))).all()
    return [_serialize_import_batch(row) for row in batches]


@app.get("/imports/{batch_id}/issues.csv")
def import_issues(batch_id: str, user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> Response:
    rows = db.scalars(select(ImportRowIssue).where(ImportRowIssue.import_batch_id == batch_id)).all()
    frame = pd.DataFrame([{
        "source_sheet": row.source_sheet, "row_number": row.row_number,
        "column": row.column_name, "issue_type": row.issue_type,
        "severity": row.severity, "message": row.message,
    } for row in rows])
    return Response(frame.to_csv(index=False), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="import-{batch_id}-issues.csv"'})


@app.get("/imports/template.{format}")
def import_template(format: str, user: AuthenticatedUser = Depends(require_admin)) -> Response:
    frame = pd.DataFrame(columns=REQUIRED_COLUMNS)
    if format == "csv":
        return Response(frame.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="peslc-import-template.csv"'})
    if format == "xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            frame.to_excel(writer, sheet_name="Source Data", index=False)
        return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": 'attachment; filename="peslc-import-template.xlsx"'})
    raise HTTPException(404, "Template format not found.")


@app.get("/imports/{batch_id}", response_model=ImportDetailResponse)
def import_detail(batch_id: str, user: AuthenticatedUser = Depends(require_admin),
                  db: Session = Depends(get_db)) -> dict:
    batch = db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(404, "Import batch not found.")
    issues = db.scalars(
        select(ImportRowIssue).where(ImportRowIssue.import_batch_id == batch_id)
        .order_by(ImportRowIssue.source_sheet, ImportRowIssue.row_number)
    ).all()
    denominator = max(batch.rows_discovered, 1)
    issue_counts: dict[str, int] = {}
    for issue in issues:
        issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1
    payload = _serialize_import_batch(batch)
    payload["issues"] = [{
        "source_sheet": row.source_sheet, "row_number": row.row_number,
        "column": row.column_name, "issue_type": row.issue_type,
        "severity": row.severity, "message": row.message,
    } for row in issues]
    payload["quality_issue_rates"] = {
        issue_type: count / denominator for issue_type, count in sorted(issue_counts.items())
    }
    payload["cancelled_row_rate"] = batch.cancelled_count / denominator
    return payload


@app.post("/analytics/run")
def run_analytics(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    groups = load_invoice_groups(db)
    if not groups:
        raise HTTPException(422, "No committed invoice data is available.")
    run = AnalyticsRun(status="running", code_version="final-alignment")
    db.add(run)
    db.flush()
    try:
        cart = cart_for_current_run(db, groups)
        result = asdict(run_account_prioritization(groups, cart_result=cart))
        persist_run_output(db, run, result)
        audit(db, user.user_id, "analytics_run", "analytics_run", run.analysis_run_id, {"status": run.status})
        db.commit()
        return serialize_run(run)
    except Exception as exc:
        db.rollback()
        failed = AnalyticsRun(status="failed", errors=[{"message": "Analytics run failed safely."}], code_version="final-alignment")
        db.add(failed)
        db.commit()
        raise HTTPException(500, "Analytics run failed; the previous successful run remains current.") from exc


@app.get("/analytics/latest")
def latest_analytics(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    return run_payload(db, _latest_or_404(db))


@app.get("/dashboard")
def dashboard(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    run = _latest_or_404(db)
    payload = run_payload(db, run)
    priorities = payload["priorities"]
    group_counts = {group: sum(row["priority_group"] == group for row in priorities) for group in ("High", "Medium", "Low")}
    risk_counts = {risk: sum(row.get("predicted_inactivity_risk") == risk for row in priorities)
                   for risk in ("Lower", "Higher")}
    total_accounts = db.scalar(select(func.count()).select_from(DimAccount)) or 0
    total_sales = sum(row.get("valid_si_sales", 0) for row in payload["business_baselines"])
    return {
        "run": serialize_run(run), "total_standardized_accounts": total_accounts,
        "mcs_eligible_accounts": int((run.eligible_account_counts or {}).get("mcs", len(priorities))), "priority_group_counts": group_counts,
        "risk_counts": risk_counts, "total_valid_historical_sales": total_sales,
        "critic_weights": run.critic_weights, "mcs_status": run.mcs_status, "cart_status": payload["cart"].get("status", "Unavailable"),
        "cart_horizon": payload["cart"].get("outcome_window_months"),
        "warnings": run.warnings or [],
        "top_accounts": priorities[:8], "sales_trend": payload["business_baselines"],
        "sensitivity": payload["sensitivity"],
    }


@app.get("/accounts")
def accounts(
    search: str = "", priority_group: str | None = None, predicted_inactivity_risk: str | None = None,
    inactivity_risk: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db),
) -> dict:
    run = _latest_or_404(db)
    rows = run_payload(db, run)["priorities"]
    if search:
        rows = [row for row in rows if search.lower() in row["account"].lower()]
    if priority_group:
        rows = [row for row in rows if row["priority_group"] == priority_group]
    risk_filter = predicted_inactivity_risk or inactivity_risk
    if risk_filter:
        rows = [row for row in rows if row.get("predicted_inactivity_risk") == risk_filter]
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "page": page,
            "page_size": page_size, "analysis_run_id": run.analysis_run_id,
            "updated_at": run.completed_at.isoformat() if run.completed_at else None}


@app.get("/accounts/{account_key}")
def account_detail(account_key: str, user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    account = db.get(DimAccount, account_key)
    if not account:
        account = db.scalar(select(DimAccount).where(DimAccount.standardized_account_name == account_key))
    if not account:
        raise HTTPException(404, "Account not found.")
    run = _latest_or_404(db)
    priority = db.scalar(select(AccountPriorityResult).where(AccountPriorityResult.analysis_run_id == run.analysis_run_id,
                                                               AccountPriorityResult.account_key == account.account_key))
    rfm = db.scalar(select(RFMResult).where(RFMResult.analysis_run_id == run.analysis_run_id, RFMResult.account_key == account.account_key))
    settlement = db.scalar(select(SettlementResult).where(SettlementResult.analysis_run_id == run.analysis_run_id,
                                                           SettlementResult.account_key == account.account_key))
    transactions = db.scalars(select(InvoiceGroupRecord).where(InvoiceGroupRecord.account_key == account.account_key)
                              .order_by(desc(InvoiceGroupRecord.si_date))).all()
    scenarios = db.scalars(select(SensitivityScenarioRecord).where(SensitivityScenarioRecord.analysis_run_id == run.analysis_run_id,
                                                                    SensitivityScenarioRecord.account_key == account.account_key)).all()
    ranks = [row.payload["scenario_rank"] for row in scenarios]
    movement = sum(row.payload["group_changed"] for row in scenarios) / len(scenarios) if scenarios else 0
    return {
        "account_key": account.account_key, "account": account.standardized_account_name,
        "priority": priority.payload if priority else None, "rfm": rfm.payload if rfm else None,
        "settlement": settlement.payload if settlement else None,
        "critic_weights": run.critic_weights,
        "sensitivity": {"minimum_rank": min(ranks) if ranks else None, "maximum_rank": max(ranks) if ranks else None,
                        "group_movement_rate": movement},
        "transactions": [{"invoice_group_id": row.invoice_group_id, "si_no": row.si_no,
                           "si_date": row.si_date.isoformat(), "si_amount": float(row.si_amount),
                           "final_cr_date": row.final_cr_date.isoformat() if row.final_cr_date else None,
                           "payment_status": row.payment_status, "reconciled": row.reconciled,
                           "review_reason": row.review_reason, "import_batch_id": row.import_batch_id} for row in transactions],
    }


@app.get("/analytics/rfm")
def rfm_analytics(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    run = _latest_or_404(db)
    return {"analysis_run_id": run.analysis_run_id, "cutoff_date": run.cutoff_date, "items": run_payload(db, run)["rfm"]}


@app.get("/analytics/settlement")
def settlement_analytics(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    run = _latest_or_404(db)
    return {"analysis_run_id": run.analysis_run_id, "items": run_payload(db, run)["settlement"]}


@app.get("/analytics/cart")
def cart_analytics(user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    run = _latest_or_404(db)
    return run_payload(db, run)["cart"]


@app.get("/analytics/sensitivity")
def sensitivity_analytics(account_key: str | None = None, user: AuthenticatedUser = Depends(require_user),
                          db: Session = Depends(get_db)) -> dict:
    run = _latest_or_404(db)
    summaries = run_payload(db, run)["sensitivity"]
    details = []
    if account_key:
        details = [row.payload for row in db.scalars(select(SensitivityScenarioRecord).where(
            SensitivityScenarioRecord.analysis_run_id == run.analysis_run_id,
            SensitivityScenarioRecord.account_key == account_key)).all()]
    return {"analysis_run_id": run.analysis_run_id, "critic_weights": run.critic_weights,
            "summaries": summaries, "account_scenarios": details}


@app.get("/runs")
def run_history(user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_run(run) for run in db.scalars(select(AnalyticsRun).order_by(desc(AnalyticsRun.started_at))).all()]


@app.get("/analytics/runs", response_model=list[AnalyticsRunResponse])
def analytics_run_history(
    user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db),
) -> list[dict]:
    return [serialize_run(run) for run in db.scalars(
        select(AnalyticsRun).order_by(desc(AnalyticsRun.started_at))
    ).all()]


@app.get("/analytics/runs/{run_id}")
def analytics_run_detail(
    run_id: str, user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    run = db.get(AnalyticsRun, run_id)
    if not run:
        raise HTTPException(404, "Analytics run not found.")
    return run_payload(db, run)


@app.get("/accounts/priorities", response_model=list[AccountPriorityResponse])
def account_priorities(
    user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db),
) -> list[dict]:
    return run_payload(db, _latest_or_404(db))["priorities"]


@app.get("/models/current", response_model=ModelSummaryResponse)
def current_model(
    user: AuthenticatedUser = Depends(require_user), db: Session = Depends(get_db),
) -> dict:
    model = active_model_version(db)
    if not model:
        return {"status": "model_unavailable", "model_version": None}
    return {
        "status": model.status, "model_version": model.model_version,
        "created_at": model.created_at, "trained_through_date": model.trained_through_date,
        "selected_outcome_horizon": model.selected_outcome_horizon,
        "retained_features": model.retained_features,
        "last_validation_date": model.last_validation_date,
        "review_recommended": model.review_recommended,
        "oop_metrics": model.oop_metrics,
    }


@app.post("/models/train-validate")
def train_validate_model(
    user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db),
) -> dict:
    groups = load_invoice_groups(db)
    if not groups:
        raise HTTPException(422, "No committed invoice data is available.")
    result = train_and_persist_model(db, groups)
    audit(db, user.user_id, "model_train_validate", "predictive_model", result.model_version,
          {"status": result.status})
    db.commit()
    return asdict(result)


@app.post("/models/monitor")
def monitor_model(
    user: AuthenticatedUser = Depends(require_admin), db: Session = Depends(get_db),
) -> dict:
    result = monitor_active_model(db, load_invoice_groups(db))
    audit(db, user.user_id, "model_monitor", "predictive_model",
          result.get("model_version"), {"status": result["status"]})
    db.commit()
    return result


@app.get("/settings/methodology")
def methodology(user: AuthenticatedUser = Depends(require_admin)) -> dict:
    return {
        "source_schema": list(REQUIRED_COLUMNS), "analytics_config": DEFAULT_ANALYTICS_CONFIG.serializable(),
        "rfm": "Account-level tie-preserving percentile quintiles; lower Recency is better.",
        "settlement": "Historical Settlement Duration uses only settlement evidence known by the current latest-valid-SI cutoff after invoice grouping.",
        "mcs": "CRITIC objectively weights separately normalized Recency, Frequency, Monetary, and Average Settlement Days. Composite RFM Score remains descriptive, while CART Inactivity Risk remains separate supporting predictive context.",
        "priority_groups": "Tie-preserving ranked thirds from each discriminatory four-criterion run.",
        "reproducibility": {
            "rfm_scoring": "favorable average rank mapped by min(5, ceil(5*r/N)); constant components score 3",
            "cart_horizons_months": [3, 6, 12],
            "cart_frequency_monetary_lookback_months": 24,
            "cart_recent_count_months": 12,
            "cart_redundancy_spearman_threshold": 0.80,
            "sensitivity_iterations_per_range": 100,
            "backtest_horizon_months": 12,
            "backtest_random_repetitions": 100,
            "random_seed": 42,
        },
        "future_data_rule": "Years and accounts are derived from validated committed data.",
    }


@app.get("/exports/{dataset}.{format}")
def export_dataset(dataset: str, format: str, user: AuthenticatedUser = Depends(require_user),
                   db: Session = Depends(get_db)) -> Response:
    run = _latest_or_404(db)
    payload = run_payload(db, run)
    sources = {
        "priorities": payload["priorities"], "rfm": payload["rfm"], "settlement": payload["settlement"],
        "sensitivity": payload["sensitivity"], "runs": [serialize_run(run)],
        "cart": [payload["cart"]], "transactions": [{"account": row.standardized_account_name,
            "si_no": row.si_no, "si_date": row.si_date, "si_amount": float(row.si_amount),
            "final_cr_date": row.final_cr_date, "import_batch_id": row.import_batch_id}
            for row in db.scalars(select(InvoiceGroupRecord)).all()],
    }
    if dataset not in sources or format not in {"csv", "xlsx"}:
        raise HTTPException(404, "Export dataset or format not found.")
    rows = [{key: _safe_sheet_value(value) for key, value in row.items()} for row in sources[dataset]]
    frame = pd.json_normalize(rows)
    frame.insert(0, "analysis_run_id", run.analysis_run_id)
    frame.insert(1, "analysis_cutoff", run.cutoff_date)
    audit(db, user.user_id, "export", dataset, run.analysis_run_id, {"format": format})
    db.commit()
    filename = f"peslc-{dataset}-{run.analysis_run_id}.{format}"
    currency_markers = ("amount", "monetary", "sales", "contribution")
    currency_columns = [
        column for column in frame.columns
        if any(marker in column.lower() for marker in currency_markers)
    ]
    if format == "csv":
        csv_frame = frame.copy()
        for column in currency_columns:
            csv_frame[column] = csv_frame[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.2f}"
            )
        return Response(csv_frame.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=dataset[:31])
        worksheet = writer.sheets[dataset[:31]]
        for column in currency_columns:
            position = frame.columns.get_loc(column) + 1
            for cells in worksheet.iter_cols(
                min_col=position, max_col=position, min_row=2, max_row=worksheet.max_row
            ):
                for cell in cells:
                    cell.number_format = "#,##0.00"
    return Response(output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/exports/priorities")
def export_priorities_query(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    return export_dataset("priorities", format, user, db)
