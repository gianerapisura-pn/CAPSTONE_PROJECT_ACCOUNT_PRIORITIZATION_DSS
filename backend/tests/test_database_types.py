from uuid import uuid4

from sqlalchemy import Uuid, create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from app.db.models import (
    AccountAlias,
    AccountAliasReview,
    AccountPriorityResult,
    AnalyticsRun,
    AuditLog,
    Base,
    BusinessBaselineRecord,
    DimAccount,
    ImportBatch,
    ImportRowIssue,
    InvoiceGroupLineage,
    InvoiceGroupRecord,
    ModelRun,
    PredictiveFeatureDecision,
    PredictiveHorizonEvaluation,
    PredictiveModelVersion,
    PredictiveMonitoringEvaluation,
    PredictiveOOPEvaluation,
    RFMResult,
    RankingBacktestRecord,
    RawSourceRow,
    SensitivityScenarioRecord,
    SensitivitySummaryRecord,
    SettlementResult,
    UserProfile,
)


UUID_COLUMNS = {
    UserProfile: ("user_id",),
    ImportBatch: ("import_batch_id", "uploaded_by", "analysis_run_id"),
    ImportRowIssue: ("import_row_issue_id", "import_batch_id"),
    RawSourceRow: ("raw_source_row_id", "import_batch_id"),
    DimAccount: ("account_key",),
    AccountAlias: ("account_alias_id", "approved_by"),
    AccountAliasReview: ("alias_review_id", "reviewed_by"),
    InvoiceGroupRecord: ("import_batch_id", "account_key"),
    InvoiceGroupLineage: ("raw_source_row_id",),
    AnalyticsRun: ("analysis_run_id", "latest_import_batch_id"),
    RFMResult: ("id", "analysis_run_id", "account_key"),
    SettlementResult: ("id", "analysis_run_id", "account_key"),
    AccountPriorityResult: ("account_priority_result_id", "analysis_run_id", "account_key"),
    ModelRun: ("model_run_id", "analysis_run_id"),
    PredictiveModelVersion: ("predictive_model_version_id",),
    PredictiveMonitoringEvaluation: (
        "predictive_monitoring_evaluation_id",
        "predictive_model_version_id",
    ),
    PredictiveHorizonEvaluation: ("id", "predictive_model_version_id"),
    PredictiveFeatureDecision: ("id", "predictive_model_version_id"),
    PredictiveOOPEvaluation: ("id", "predictive_model_version_id"),
    SensitivitySummaryRecord: ("sensitivity_result_id", "analysis_run_id"),
    SensitivityScenarioRecord: ("id", "analysis_run_id", "account_key"),
    RankingBacktestRecord: ("id", "analysis_run_id"),
    BusinessBaselineRecord: ("id", "analysis_run_id"),
    AuditLog: ("audit_log_id", "actor_user_id"),
}


def test_postgresql_uuid_columns_compile_as_native_uuid():
    dialect = postgresql.dialect()
    for model, names in UUID_COLUMNS.items():
        for name in names:
            column_type = model.__table__.columns[name].type
            assert isinstance(column_type, Uuid), f"{model.__name__}.{name}"
            assert column_type.as_uuid is False
            assert column_type.compile(dialect=dialect).upper() == "UUID"


def test_uuid_string_values_round_trip_through_sqlite_and_foreign_key_filters():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    account_id = str(uuid4())
    run_id = str(uuid4())
    result_id = str(uuid4())

    with Session(engine) as db:
        db.add(DimAccount(
            account_key=account_id,
            standardized_account_name="UUID CONTRACT ACCOUNT",
            display_name="UUID Contract Account",
        ))
        db.add(AnalyticsRun(analysis_run_id=run_id, status="successful"))
        db.add(RFMResult(
            id=result_id,
            analysis_run_id=run_id,
            account_key=account_id,
            payload={"account": "UUID CONTRACT ACCOUNT"},
        ))
        db.commit()

        stored = db.scalar(select(RFMResult).where(
            RFMResult.analysis_run_id == run_id,
            RFMResult.account_key == account_id,
        ))
        assert stored is not None
        assert stored.id == result_id
        assert stored.analysis_run_id == run_id
        assert stored.account_key == account_id
        assert isinstance(stored.account_key, str)
