from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, DimAccount
from app.db.repository import ensure_accounts
from scripts import bootstrap_account_context


def test_locked_account_master_status_provenance_and_population_contract(monkeypatch):
    keys = [f"A{index:03d}" for index in range(1, 86)]
    names = [f"BUSINESS {index}" for index in range(1, 86)]
    names[62] = "ROD DE GUIA"
    names[63] = "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY"
    master = pd.DataFrame({
        "account_key": keys,
        "account_name": names,
        "entity_type": ["Individual/Personal" if key == "A063" else "Company" for key in keys],
        "business_category": ["Personal" if key == "A063" else "Corporate" for key in keys],
        "primary_business_type": ["Personal" if key == "A063" else "Construction" for key in keys],
    })
    b2b_keys = [key for key in keys if key != "A063"]
    status = pd.DataFrame({
        "account_key": b2b_keys,
        "account_status": [
            "Client-Confirmed Closed" if key == "A064" else "Client-Confirmed Active"
            for key in b2b_keys
        ],
    })
    provenance = pd.DataFrame({
        "account_key": b2b_keys,
        "account_status": status["account_status"],
        "source_type": ["Client confirmation"] * 84,
        "confirmed_on": ["2026-09-20"] * 84,
        "confirming_role": ["PESLC client representative"] * 84,
        "claim_scope": ["PESLC account actionability"] * 84,
        "basis": ["Direct PESLC confirmation collected for the study"] * 84,
    })
    identity = master[["account_key", "account_name", "entity_type", "primary_business_type"]].copy()
    identity["source_type"] = "Client confirmation"
    identity["source_reference"] = "PESLC account master"
    identity["source_url"] = None
    identity["source_checked_on"] = "2026-10-04"
    identity["note"] = "Approved context"
    mapping = master[["primary_business_type", "business_category"]].drop_duplicates()
    monkeypatch.setattr(bootstrap_account_context, "verified_package", lambda path, digest: (path, b"verified"))
    def source(_content, suffix):
        if suffix.endswith("account_status.csv"):
            return status.copy()
        if suffix.endswith("status_provenance.csv"):
            return provenance.copy()
        if suffix.endswith("account_master_provenance.csv"):
            return identity.copy()
        if suffix.endswith("business_type_mapping.csv"):
            return mapping.copy()
        return master.copy()
    monkeypatch.setattr(bootstrap_account_context, "read_package_csv", source)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = bootstrap_account_context.bootstrap(db, "authorized.zip")
        db.commit()
        rows = db.scalars(select(DimAccount)).all()
        assert result == {
            "historical_identity_count": 85,
            "b2b_analytical_count": 84,
            "current_actionable_count": 83,
        }
        personal = next(row for row in rows if row.standardized_account_name == "ROD DE GUIA")
        assert personal.b2b_priority_eligible is False
        assert personal.account_status is None
        closed = next(row for row in rows if row.standardized_account_name.startswith("ROSTRAM"))
        assert closed.b2b_priority_eligible is True
        assert closed.account_status == "Client-Confirmed Closed"
        assert closed.verification_type == "Client confirmation"
        assert closed.verification_date == date(2026, 9, 20)
        assert closed.verification_basis == "Direct PESLC confirmation collected for the study"
        assert closed.status_claim_scope == "PESLC account actionability"
        assert closed.identity_source_reference == "PESLC account master"


def test_unknown_future_account_defaults_ineligible():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        account = ensure_accounts(db, ["UNKNOWN FUTURE ACCOUNT"])["UNKNOWN FUTURE ACCOUNT"]
        assert account.b2b_priority_eligible is False
        assert account.entity_type is None
        assert account.last_verified is None
