from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Base, DimAccount
from app.db.repository import ensure_accounts
from scripts import bootstrap_account_context


def test_locked_account_master_schema_status_merge_and_b2b_rule(monkeypatch):
    names = ["ROD DE GUIA"] + [f"BUSINESS {index}" for index in range(1, 85)]
    master = pd.DataFrame({
        "account_key": [f"K{index}" for index in range(85)],
        "account_name": names,
        "entity_type": ["Individual/Personal"] + ["Business/Organization"] * 84,
        "business_category": ["Personal"] + ["Corporate"] * 84,
        "primary_business_type": ["Personal"] + ["Construction"] * 84,
    })
    status = pd.DataFrame({
        "account_key": [f"K{index}" for index in range(85)],
        "account_status": ["Verified"] * 85,
        "last_verified": ["2026-09-21"] * 85,
    })
    monkeypatch.setattr(bootstrap_account_context, "verified_package",
                        lambda path, digest: (path, b"verified"))
    monkeypatch.setattr(
        bootstrap_account_context,
        "read_package_csv",
        lambda content, suffix: status.copy() if suffix.endswith("account_status.csv") else master.copy(),
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = bootstrap_account_context.bootstrap(db, "authorized.zip")
        db.commit()
        rows = db.scalars(select(DimAccount)).all()
        assert result == {"identity_count": 85, "verified_b2b_count": 84}
        assert len(rows) == 85
        personal = next(row for row in rows if row.standardized_account_name == "ROD DE GUIA")
        assert personal.b2b_priority_eligible is False
        assert personal.account_status == "Verified"
        assert personal.last_verified == date(2026, 9, 21)


def test_unknown_future_account_defaults_ineligible():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        account = ensure_accounts(db, ["UNKNOWN FUTURE ACCOUNT"])["UNKNOWN FUTURE ACCOUNT"]
        assert account.b2b_priority_eligible is False
        assert account.entity_type is None
        assert account.last_verified is None