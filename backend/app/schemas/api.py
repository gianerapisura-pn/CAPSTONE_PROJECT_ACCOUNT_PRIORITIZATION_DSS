from typing import Any

from pydantic import BaseModel, Field


class ValidationIssueResponse(BaseModel):
    row_number: int | None = None
    column: str | None = None
    severity: str
    message: str
    issue_type: str = "validation"
    source_sheet: str | None = None


class ImportPreviewResponse(BaseModel):
    import_batch_id: str
    file_name: str
    file_hash: str
    sheets: list[str]
    rows_discovered: int
    cancelled_count: int
    issues: list[ValidationIssueResponse]
    duplicate_committed_file: bool
    quality_rates: dict[str, float]
    can_commit: bool
    status: str


class ImportCommitResponse(BaseModel):
    status: str
    import_batch_id: str
    analysis_run_id: str
    prioritized_accounts: int
    cutoff_date: str | None = None


class ImportBatchResponse(BaseModel):
    import_batch_id: str
    file_name: str
    file_hash: str
    uploaded_by: str | None = None
    uploaded_at: str
    committed_at: str | None = None
    status: str
    rows_discovered: int
    rows_accepted: int
    rows_flagged: int
    rows_excluded: int
    cancelled_count: int
    analysis_run_id: str | None = None
    override_reason: str | None = None


class ImportDetailResponse(ImportBatchResponse):
    issues: list[ValidationIssueResponse]
    quality_issue_rates: dict[str, float]
    cancelled_row_rate: float


class AnalyticsRunResponse(BaseModel):
    analysis_run_id: str
    cutoff_date: str | None = None
    started_at: str
    completed_at: str | None = None
    status: str
    mcs_status: str
    critic_weights: dict[str, float]
    warnings: list[Any]
    duration_seconds: float | None = None
    latest_import_batch_id: str | None = None
    row_counts: dict[str, int]
    eligible_account_counts: dict[str, int]
    model_version: str | None = None
    predictive_status: str | None = None


class AccountPriorityResponse(BaseModel):
    account: str
    rfm_score: float
    recency_days: int
    frequency: int
    monetary: float
    recency_score: int
    frequency_score: int
    monetary_score: int
    settlement_days_avg: float
    normalized_recency: float
    normalized_frequency: float
    normalized_monetary: float
    normalized_settlement: float
    recency_contribution: float
    frequency_contribution: float
    monetary_contribution: float
    settlement_contribution: float
    final_priority_score: float
    priority_rank: int
    priority_group: str
    latest_valid_transaction: str
    inactivity_risk: str | None = None
    model_version: str | None = None


class ModelSummaryResponse(BaseModel):
    status: str
    model_version: str | None = None
    created_at: Any = None
    trained_through_date: Any = None
    selected_outcome_horizon: int | None = None
    retained_features: list[str] = Field(default_factory=list)
    last_validation_date: Any = None
    review_recommended: bool = False
    oop_metrics: dict[str, Any] = Field(default_factory=dict)
