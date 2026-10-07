from __future__ import annotations
import json
from sqlalchemy import Uuid, create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.db.models import Base


def make_engine():
    url = get_settings().database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=make_engine())


DEMO_ADDITIONS = {
    "import_batches": {
        "analysis_reference_date": "DATE",
    },
    "dim_account": {
        "entity_type": "VARCHAR(80)",
        "business_category": "VARCHAR(160)",
        "primary_business_type": "VARCHAR(160)",
        "b2b_priority_eligible": "BOOLEAN NOT NULL DEFAULT 0",
        "account_status": "VARCHAR(80)",
        "last_verified": "DATE",
        "verification_type": "VARCHAR(120)",
        "verification_date": "DATE",
        "verification_basis": "TEXT",
        "status_confirming_role": "VARCHAR(160)",
        "status_claim_scope": "VARCHAR(160)",
        "identity_source_type": "VARCHAR(160)",
        "identity_source_reference": "TEXT",
        "identity_source_url": "TEXT",
        "identity_source_checked_on": "DATE",
        "identity_source_note": "TEXT",
    },
    "fact_account_context": {
        "status_confirming_role": "VARCHAR(160)",
        "status_claim_scope": "VARCHAR(160)",
        "identity_source_type": "VARCHAR(160)",
        "identity_source_reference": "TEXT",
        "identity_source_url": "TEXT",
        "identity_source_checked_on": "DATE",
        "identity_source_note": "TEXT",
    },
    "analytics_runs": {
        "analysis_reference_date": "DATE",
        "latest_valid_si_date": "DATE",
        "latest_final_cr_date": "DATE",
        "methodology_version": "VARCHAR(80)",
        "mcs_status": "VARCHAR(40)",
        "context_metrics": "JSON DEFAULT '{}'",
        "row_counts": "JSON NOT NULL DEFAULT '{}'",
        "eligible_account_counts": "JSON NOT NULL DEFAULT '{}'",
        "model_version": "VARCHAR(120)",
        "predictive_status": "VARCHAR(80)",
    },
    "predictive_model_versions": {
        "model_family": "VARCHAR(120)",
        "model_parameters": "JSON DEFAULT '{}'",
        "target_definition": "TEXT",
        "primary_selection_metric": "VARCHAR(120)",
        "decision_threshold": "FLOAT",
    },
    "import_row_issues": {
        "issue_type": "VARCHAR(80) NOT NULL DEFAULT 'validation'",
    },
    "invoice_groups": {
        "conflicting_invoice": "BOOLEAN NOT NULL DEFAULT 0",
        "rfm_eligible": "BOOLEAN NOT NULL DEFAULT 0",
        "settlement_eligible": "BOOLEAN NOT NULL DEFAULT 0",
        "settlement_days": "INTEGER",
    },
    "raw_source_rows": {
        "customer_name_raw": "TEXT",
        "si_no": "TEXT",
        "si_date_raw": "TEXT",
        "si_amount_raw": "TEXT",
        "cr_no": "TEXT",
        "cr_date_raw": "TEXT",
        "cr_amount_raw": "TEXT",
        "ewt_raw": "TEXT",
        "payment_mode_raw": "TEXT",
        "payment_status_raw": "TEXT",
    },
}

RAW_SOURCE_KEYS = {
    "customer_name_raw": ("ACCOUNT NAMES", "CUSTOMER NAME"),
    "si_no": ("SI NO.",),
    "si_date_raw": ("SI DATE",),
    "si_amount_raw": ("SI AMOUNT",),
    "cr_no": ("CR NO.",),
    "cr_date_raw": ("CR DATE",),
    "cr_amount_raw": ("CR AMOUNT",),
    "ewt_raw": ("EWT",),
    "payment_mode_raw": ("PAYMENT MODE",),
    "payment_status_raw": ("PAYMENT STATUS",),
}


def _ensure_demo_schema() -> None:
    """Apply additive compatibility columns to an existing isolated SQLite database."""
    engine = SessionLocal.kw["bind"]
    with engine.begin() as connection:
        schema = inspect(connection)
        tables = set(schema.get_table_names())
        added: dict[str, set[str]] = {}
        for table_name, additions in DEMO_ADDITIONS.items():
            if table_name not in tables:
                continue
            columns = {column["name"] for column in schema.get_columns(table_name)}
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{name}" {sql_type}'
                    ))
                    added.setdefault(table_name, set()).add(name)

        if added.get("raw_source_rows"):
            changed = added["raw_source_rows"]
            rows = connection.execute(text(
                "SELECT raw_source_row_id, canonical_payload FROM raw_source_rows"
            )).all()
            for row_id, payload in rows:
                source = json.loads(payload) if payload else {}
                values = {
                    name: next((str(source[key]) for key in keys
                                if source.get(key) is not None), None)
                    for name, keys in RAW_SOURCE_KEYS.items() if name in changed
                }
                if values:
                    assignments = ", ".join(f'"{name}" = :{name}' for name in values)
                    connection.execute(text(
                        f'UPDATE raw_source_rows SET {assignments} WHERE raw_source_row_id = :row_id'
                    ), {**values, "row_id": row_id})

        if added.get("invoice_groups"):
            changed = added["invoice_groups"]
            if "conflicting_invoice" in changed:
                connection.execute(text(
                    "UPDATE invoice_groups SET conflicting_invoice = CASE WHEN EXISTS ("
                    "SELECT 1 FROM invoice_groups other WHERE "
                    "other.standardized_account_name = invoice_groups.standardized_account_name "
                    "AND other.si_no = invoice_groups.si_no "
                    "AND other.si_date = invoice_groups.si_date "
                    "AND CAST(other.si_amount AS NUMERIC) != "
                    "CAST(invoice_groups.si_amount AS NUMERIC)) THEN 1 ELSE 0 END"
                ))
            if "rfm_eligible" in changed:
                connection.execute(text(
                    "UPDATE invoice_groups SET rfm_eligible = CASE WHEN "
                    "payment_status = 'Fully Paid' AND conflicting_invoice = 0 "
                    "AND si_date IS NOT NULL AND CAST(si_amount AS NUMERIC) > 0 "
                    "THEN 1 ELSE 0 END"
                ))
            if "settlement_eligible" in changed:
                connection.execute(text(
                    "UPDATE invoice_groups SET settlement_eligible = CASE WHEN "
                    "payment_status = 'Fully Paid' AND conflicting_invoice = 0 "
                    "AND final_cr_date IS NOT NULL AND reconciled = 1 "
                    "AND julianday(final_cr_date) >= julianday(si_date) "
                    "THEN 1 ELSE 0 END"
                ))
            if "settlement_days" in changed:
                connection.execute(text(
                    "UPDATE invoice_groups SET settlement_days = "
                    "CASE WHEN settlement_eligible = 1 THEN "
                    "CAST(julianday(final_cr_date) - julianday(si_date) AS INTEGER) "
                    "ELSE NULL END"
                ))

        legacy_ids = {
            "demo-administrator": "00000000-0000-4000-8000-000000000001",
            "demo-management": "00000000-0000-4000-8000-000000000002",
        }
        for table_name, column_name in (
            ("import_batches", "uploaded_by"), ("account_aliases", "approved_by"),
            ("account_alias_review", "reviewed_by"), ("audit_log", "actor_user_id"),
        ):
            if table_name not in tables:
                continue
            columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
            if column_name not in columns:
                continue
            for legacy_id, uuid_id in legacy_ids.items():
                connection.execute(text(
                    f'UPDATE "{table_name}" SET "{column_name}" = :uuid_id '
                    f'WHERE "{column_name}" = :legacy_id'
                ), {"uuid_id": uuid_id, "legacy_id": legacy_id})

        for table in Base.metadata.sorted_tables:
            if table.name not in tables:
                continue
            for column in table.columns:
                if isinstance(column.type, Uuid):
                    connection.execute(text(
                        f'UPDATE "{table.name}" SET "{column.name}" = '
                        f'replace("{column.name}", \'-\', \'\') '
                        f'WHERE length("{column.name}") = 36'
                    ))


def init_database() -> None:
    settings = get_settings()
    if settings.demo_mode or settings.app_env == "test":
        Base.metadata.create_all(bind=SessionLocal.kw["bind"])
        _ensure_demo_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
