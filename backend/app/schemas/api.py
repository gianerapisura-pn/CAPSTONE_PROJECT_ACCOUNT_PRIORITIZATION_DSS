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
    latest_evidence_date: str | None = None
    analysis_reference_required: bool = True
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
    analysis_reference_date: str
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
    analysis_reference_date: str | None = None


class ImportDetailResponse(ImportBatchResponse):
    issues: list[ValidationIssueResponse]
    quality_issue_rates: dict[str, float]
    cancelled_row_rate: float


class AnalyticsRunResponse(BaseModel):
    analysis_run_id: str
    analysis_reference_date: str | None = None
    latest_valid_si_date: str | None = None
    latest_final_cr_date: str | None = None
    methodology_version: str | None = None
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
    rfm_mean_score: float
    recency_days: int
    frequency: int
    frequency_count: int
    monetary: float
    monetary_value: float
    settlement_days_avg: float
    average_settlement_days: float
    valid_settlement_record_count: int
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
    latest_valid_si_date: str | None
    baseline_recency_weight: float | None
    baseline_frequency_weight: float | None
    baseline_monetary_weight: float | None
    baseline_settlement_weight: float | None
    r_score: int
    f_score: int
    m_score: int
    rfm_code: str
    predicted_future_transaction_class: str | None = None
    model_version: str | None = None


class AccountDecisionRowResponse(BaseModel):
    account_key: str
    account: str
    display_name: str
    entity_type: str | None = None
    business_category: str | None = None
    primary_business_type: str | None = None
    b2b_priority_eligible: bool
    account_status: str | None = None
    last_verified: str | None = None
    verification_type: str | None = None
    verification_date: str | None = None
    verification_basis: str | None = None
    current_actionable: bool
    criteria_complete: bool
    analysis_run_id: str
    analysis_reference_date: str | None = None
    latest_valid_si_date: str | None = None
    recency_days: int
    frequency: int
    frequency_count: int
    monetary: float
    monetary_value: float
    r_score: int
    f_score: int
    m_score: int
    rfm_code: str
    rfm_mean_score: float
    settlement_invoice_count: int
    valid_settlement_record_count: int
    average_settlement_days: float | None = None
    settlement_days_avg: float | None = None
    mcs_eligible: bool
    mcs_eligibility_reason: str | None = None
    is_ranked: bool
    ranking_status: str
    ranking_unavailable_reason: str | None = None
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
    predicted_future_transaction_class: str | None = None
    model_version: str | None = None


class AccountListResponse(BaseModel):
    items: list[AccountDecisionRowResponse]
    total: int
    page: int
    page_size: int
    analysis_run_id: str
    analysis_reference_date: str | None = None
    updated_at: str | None = None


class ModelSummaryResponse(BaseModel):
    status: str
    model_version: str | None = None
    model_family: str | None = None
    created_at: Any = None
    trained_through_date: Any = None
    selected_outcome_horizon: int | None = None
    retained_features: list[str] = Field(default_factory=list)
    decision_threshold: float | None = None
    artifact_hash: str | None = None
    last_validation_date: Any = None
    review_recommended: bool = False
    development_metrics: dict[str, Any] = Field(default_factory=dict)
    validation_metrics: dict[str, Any] = Field(default_factory=dict)
