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
    warnings: list[str] = Field(default_factory=list)


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
    frequency_count: int
    monetary: float
    monetary_value: float
    recency_score: int
    frequency_score: int
    monetary_score: int
    settlement_days_avg: float
    average_settlement_days: float
    valid_settlement_record_count: int | None
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
    latest_valid_transaction_date: str | None
    latest_valid_si_date: str | None
    baseline_recency_weight: float | None
    baseline_frequency_weight: float | None
    baseline_monetary_weight: float | None
    baseline_settlement_weight: float | None
    predicted_inactivity_risk: str | None = None
    inactivity_risk: str | None = None
    model_version: str | None = None


class AccountDecisionRowResponse(BaseModel):
    account_key: str
    account: str
    analysis_run_id: str
    analysis_cutoff: str | None = None
    latest_valid_si_date: str | None = None
    latest_valid_transaction_date: str | None = None
    recency_days: int
    frequency: int
    frequency_count: int
    monetary: float
    monetary_value: float
    recency_score: int
    frequency_score: int
    monetary_score: int
    rfm_score: float
    settlement_invoice_count: int
    valid_settlement_record_count: int
    average_settlement_days: float | None = None
    settlement_days_avg: float | None = None
    mcs_eligible: bool
    mcs_eligibility_reason: str | None = None
    normalized_recency: float | None = None
    normalized_frequency: float | None = None
    normalized_monetary: float | None = None
    normalized_settlement: float | None = None
    recency_contribution: float | None = None
    frequency_contribution: float | None = None
    monetary_contribution: float | None = None
    settlement_contribution: float | None = None
    final_priority_score: float | None = None
    priority_rank: int | None = None
    priority_group: str | None = None
    baseline_recency_weight: float | None = None
    baseline_frequency_weight: float | None = None
    baseline_monetary_weight: float | None = None
    baseline_settlement_weight: float | None = None
    predicted_inactivity_risk: str | None = None
    inactivity_risk: str | None = None
    model_version: str | None = None


class AccountListResponse(BaseModel):
    items: list[AccountDecisionRowResponse]
    total: int
    page: int
    page_size: int
    analysis_run_id: str
    updated_at: str | None = None

class ModelSummaryResponse(BaseModel):
    status: str
    model_version: str | None = None
    created_at: Any = None
    development_data_through: Any = None
    untouched_oop_cutoff: Any = None
    artifact_validation_date: Any = None
    current_scoring_cutoff: Any = None
    monitoring_origin_date: Any = None
    selected_outcome_horizon: int | None = None
    retained_features: list[str] = Field(default_factory=list)
    last_validation_date: Any = None
    review_recommended: bool = False
    oop_metrics: dict[str, Any] = Field(default_factory=dict)
