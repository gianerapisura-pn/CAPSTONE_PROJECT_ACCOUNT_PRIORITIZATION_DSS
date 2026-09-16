from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


UUID_STRING = Uuid(as_uuid=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    import_batch_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_by: Mapped[str | None] = mapped_column(UUID_STRING)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32))
    rows_discovered: Mapped[int] = mapped_column(Integer, default=0)
    rows_accepted: Mapped[int] = mapped_column(Integer, default=0)
    rows_flagged: Mapped[int] = mapped_column(Integer, default=0)
    rows_excluded: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(Text)
    override_reason: Mapped[str | None] = mapped_column(Text)
    analysis_run_id: Mapped[str | None] = mapped_column(UUID_STRING)


class ImportRowIssue(Base):
    __tablename__ = "import_row_issues"
    import_row_issue_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.import_batch_id"), index=True)
    source_sheet: Mapped[str | None] = mapped_column(String(255))
    row_number: Mapped[int | None] = mapped_column(Integer)
    column_name: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    issue_type: Mapped[str] = mapped_column(String(80), default="validation")


class RawSourceRow(Base):
    __tablename__ = "raw_source_rows"
    raw_source_row_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.import_batch_id"), index=True)
    source_sheet: Mapped[str] = mapped_column(String(255))
    source_row_number: Mapped[int] = mapped_column(Integer)
    customer_name_raw: Mapped[str | None] = mapped_column(Text)
    si_no: Mapped[str | None] = mapped_column(Text)
    si_date_raw: Mapped[str | None] = mapped_column(Text)
    si_amount_raw: Mapped[str | None] = mapped_column(Text)
    cr_no: Mapped[str | None] = mapped_column(Text)
    cr_date_raw: Mapped[str | None] = mapped_column(Text)
    cr_amount_raw: Mapped[str | None] = mapped_column(Text)
    ewt_raw: Mapped[str | None] = mapped_column(Text)
    payment_mode_raw: Mapped[str | None] = mapped_column(Text)
    payment_status_raw: Mapped[str | None] = mapped_column(Text)
    canonical_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DimAccount(Base):
    __tablename__ = "dim_account"
    account_key: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    standardized_account_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AccountAlias(Base):
    __tablename__ = "account_aliases"
    account_alias_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    alias_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    canonical_account_name: Mapped[str] = mapped_column(String(255), index=True)
    approved_by: Mapped[str | None] = mapped_column(UUID_STRING)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reason: Mapped[str | None] = mapped_column(Text)


class AccountAliasReview(Base):
    __tablename__ = "account_alias_review"
    alias_review_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    possible_canonical_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(UUID_STRING)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)


class InvoiceGroupRecord(Base):
    __tablename__ = "invoice_groups"
    invoice_group_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    import_batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.import_batch_id"), index=True)
    account_key: Mapped[str | None] = mapped_column(ForeignKey("dim_account.account_key"), index=True)
    standardized_account_name: Mapped[str] = mapped_column(String(255), index=True)
    si_no: Mapped[str] = mapped_column(String(255))
    si_date: Mapped[datetime] = mapped_column(Date)
    si_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    payment_status: Mapped[str] = mapped_column(String(80))
    final_cr_date: Mapped[datetime | None] = mapped_column(Date)
    total_cr_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    total_ewt: Mapped[float] = mapped_column(Numeric(18, 2))
    reconciliation_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    reconciliation_difference: Mapped[float] = mapped_column(Numeric(18, 2))
    reconciled: Mapped[bool] = mapped_column(Boolean)
    review_reason: Mapped[str | None] = mapped_column(Text)
    is_cancelled: Mapped[bool] = mapped_column(Boolean)
    conflicting_invoice: Mapped[bool] = mapped_column(Boolean, default=False)
    rfm_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    settlement_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    settlement_days: Mapped[int | None] = mapped_column(Integer)


class InvoiceGroupLineage(Base):
    __tablename__ = "invoice_group_rows"
    invoice_group_id: Mapped[str] = mapped_column(
        ForeignKey("invoice_groups.invoice_group_id"), primary_key=True
    )
    raw_source_row_id: Mapped[str] = mapped_column(
        ForeignKey("raw_source_rows.raw_source_row_id"), primary_key=True
    )


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"
    analysis_run_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    cutoff_date: Mapped[datetime | None] = mapped_column(Date)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_import_batch_id: Mapped[str | None] = mapped_column(UUID_STRING)
    status: Mapped[str] = mapped_column(String(40), index=True)
    mcs_status: Mapped[str | None] = mapped_column(String(40))
    critic_weights: Mapped[dict] = mapped_column(JSON, default=dict)
    row_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    eligible_account_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str | None] = mapped_column(String(120))
    predictive_status: Mapped[str | None] = mapped_column(String(80))
    effective_config: Mapped[dict] = mapped_column(JSON, default=dict)
    context_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    code_version: Mapped[str | None] = mapped_column(String(80))


class RFMResult(Base):
    __tablename__ = "fact_account_rfm"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    account_key: Mapped[str] = mapped_column(ForeignKey("dim_account.account_key"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("analysis_run_id", "account_key"),)


class SettlementResult(Base):
    __tablename__ = "fact_historical_settlement"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    account_key: Mapped[str] = mapped_column(ForeignKey("dim_account.account_key"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("analysis_run_id", "account_key"),)


class AccountPriorityResult(Base):
    __tablename__ = "account_priority_results"
    account_priority_result_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    account_key: Mapped[str] = mapped_column(ForeignKey("dim_account.account_key"), index=True)
    standardized_account_name: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("analysis_run_id", "account_key"),)


class ModelRun(Base):
    __tablename__ = "model_runs"
    model_run_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    model_version: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)


class PredictiveModelVersion(Base):
    __tablename__ = "predictive_model_versions"
    predictive_model_version_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    model_version: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    status: Mapped[str] = mapped_column(String(40), index=True)
    trained_through_date: Mapped[datetime | None] = mapped_column(Date)
    selected_outcome_horizon: Mapped[int | None] = mapped_column(Integer)
    predictive_lookback_months: Mapped[int | None] = mapped_column(Integer)
    recent_transaction_months: Mapped[int | None] = mapped_column(Integer)
    retained_features: Mapped[list] = mapped_column(JSON, default=list)
    preprocessing_config: Mapped[dict] = mapped_column(JSON, default=dict)
    tree_hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)
    random_seed: Mapped[int | None] = mapped_column(Integer)
    development_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    oop_cutoff: Mapped[datetime | None] = mapped_column(Date)
    oop_metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    last_validation_date: Mapped[datetime | None] = mapped_column(Date)
    method_version: Mapped[str | None] = mapped_column(String(80))
    code_version: Mapped[str | None] = mapped_column(String(80))
    artifact_path: Mapped[str | None] = mapped_column(Text)
    artifact_hash: Mapped[str | None] = mapped_column(String(64))
    review_recommended: Mapped[bool] = mapped_column(Boolean, default=False)


class PredictiveMonitoringEvaluation(Base):
    __tablename__ = "predictive_monitoring_evaluations"
    predictive_monitoring_evaluation_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    predictive_model_version_id: Mapped[str] = mapped_column(
        ForeignKey("predictive_model_versions.predictive_model_version_id"), index=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    cutoff_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(60))
    review_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class PredictiveHorizonEvaluation(Base):
    __tablename__ = "predictive_horizon_evaluations"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    predictive_model_version_id: Mapped[str] = mapped_column(
        ForeignKey("predictive_model_versions.predictive_model_version_id"), index=True
    )
    horizon_months: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class PredictiveFeatureDecision(Base):
    __tablename__ = "predictive_feature_decisions"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    predictive_model_version_id: Mapped[str] = mapped_column(
        ForeignKey("predictive_model_versions.predictive_model_version_id"), index=True
    )
    feature_name: Mapped[str] = mapped_column(String(120))
    retained: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[dict] = mapped_column(JSON)


class PredictiveOOPEvaluation(Base):
    __tablename__ = "predictive_oop_evaluations"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    predictive_model_version_id: Mapped[str] = mapped_column(
        ForeignKey("predictive_model_versions.predictive_model_version_id"), index=True
    )
    oop_cutoff: Mapped[datetime | None] = mapped_column(Date)
    payload: Mapped[dict] = mapped_column(JSON)


class SensitivitySummaryRecord(Base):
    __tablename__ = "sensitivity_results"
    sensitivity_result_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    weight_range: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)


class SensitivityScenarioRecord(Base):
    __tablename__ = "fact_sensitivity_analysis"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    weight_range: Mapped[float] = mapped_column(Float, index=True)
    iteration: Mapped[int] = mapped_column(Integer)
    account_key: Mapped[str] = mapped_column(ForeignKey("dim_account.account_key"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class RankingBacktestRecord(Base):
    __tablename__ = "ranking_backtests"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class BusinessBaselineRecord(Base):
    __tablename__ = "business_baseline_results"
    id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analytics_runs.analysis_run_id"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class AuditLog(Base):
    __tablename__ = "audit_log"
    audit_log_id: Mapped[str] = mapped_column(UUID_STRING, primary_key=True, default=uid)
    actor_user_id: Mapped[str | None] = mapped_column(UUID_STRING)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
