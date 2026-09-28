from __future__ import annotations

import argparse

import pandas as pd
from sqlalchemy import select

from app.db.models import DimAccount
from app.db.repository import (
    CLIENT_CONFIRMED_ACTIVE,
    CLIENT_CONFIRMED_CLOSED,
    audit,
)
from app.db.session import SessionLocal, init_database
from app.etl.standardization import standardize_account_name
from app.services.locked_packages import FINAL_PACKAGE_SHA256, read_package_csv, verified_package

MASTER_MEMBER = "01_DATA/01_ACCOUNTS/account_master.csv"
STATUS_MEMBER = "01_DATA/01_ACCOUNTS/account_status.csv"
PROVENANCE_MEMBER = "01_DATA/01_ACCOUNTS/status_provenance.csv"


def _require_schema(frame: pd.DataFrame, expected: list[str], name: str) -> None:
    if list(frame.columns) != expected:
        raise ValueError(f"Unexpected {name} schema: {list(frame.columns)}")


def bootstrap(db, package_path: str, actor: str | None = None) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    master = read_package_csv(content, MASTER_MEMBER)
    statuses = read_package_csv(content, STATUS_MEMBER)
    provenance = read_package_csv(content, PROVENANCE_MEMBER)
    _require_schema(master, ["account_key", "account_name", "entity_type", "business_category", "primary_business_type"], "account_master.csv")
    _require_schema(statuses, ["account_key", "account_status", "last_verified"], "account_status.csv")
    _require_schema(provenance, ["account_key", "verification_type", "verification_date", "basis"], "status_provenance.csv")
    if len(master) != 85:
        raise ValueError(f"Locked account master must contain 85 identities; found {len(master)}.")
    personal = master.loc[master["entity_type"] == "Individual/Personal"]
    if len(personal) != 1 or personal.iloc[0]["account_key"] != "A063" or standardize_account_name(personal.iloc[0]["account_name"]) != "ROD DE GUIA":
        raise ValueError("The sole historical Individual/Personal identity must be A063 ROD DE GUIA.")
    b2b = master.loc[master["entity_type"] != "Individual/Personal"]
    b2b_keys = set(b2b["account_key"].astype(str))
    if len(b2b_keys) != 84 or set(statuses["account_key"].astype(str)) != b2b_keys or set(provenance["account_key"].astype(str)) != b2b_keys:
        raise ValueError("B2B master, status, and provenance key sets must match exactly across 84 identities.")
    status_counts = statuses["account_status"].value_counts().to_dict()
    if status_counts != {CLIENT_CONFIRMED_ACTIVE: 83, CLIENT_CONFIRMED_CLOSED: 1}:
        raise ValueError(f"Unexpected account status distribution: {status_counts}")
    closed = statuses.loc[statuses["account_status"] == CLIENT_CONFIRMED_CLOSED]
    closed_master = closed.merge(master, on="account_key", validate="one_to_one")
    if closed_master.iloc[0]["account_key"] != "A064" or standardize_account_name(closed_master.iloc[0]["account_name"]) != "ROSTRAM PROTECTIVE SYSTEM METIER COMPANY":
        raise ValueError("The sole closed B2B identity must be A064 ROSTRAM PROTECTIVE SYSTEM METIER COMPANY.")
    if set(provenance["verification_type"].astype(str)) != {"Client confirmation"}:
        raise ValueError("All B2B provenance must use Client confirmation.")
    if set(provenance["basis"].astype(str)) != {"Direct PESLC client confirmation"}:
        raise ValueError("All B2B provenance must use the direct PESLC client-confirmation basis.")

    merged = master.merge(statuses, on="account_key", how="left", validate="one_to_one").merge(
        provenance, on="account_key", how="left", validate="one_to_one"
    )
    existing = {row.standardized_account_name: row for row in db.scalars(select(DimAccount)).all()}
    for source in merged.to_dict(orient="records"):
        name = standardize_account_name(source["account_name"])
        row = existing.get(name)
        if row is None:
            row = DimAccount(standardized_account_name=name, display_name=name)
            db.add(row)
            existing[name] = row
        row.entity_type = str(source["entity_type"]).strip()
        row.business_category = str(source["business_category"]).strip()
        row.primary_business_type = str(source["primary_business_type"]).strip()
        row.b2b_priority_eligible = row.entity_type != "Individual/Personal"
        row.account_status = None if pd.isna(source["account_status"]) else str(source["account_status"]).strip()
        last_verified = pd.to_datetime(source["last_verified"], errors="coerce")
        row.last_verified = None if pd.isna(last_verified) else last_verified.date()
        row.verification_type = None if pd.isna(source["verification_type"]) else str(source["verification_type"]).strip()
        verification_date = pd.to_datetime(source["verification_date"], errors="coerce")
        row.verification_date = None if pd.isna(verification_date) else verification_date.date()
        row.verification_basis = None if pd.isna(source["basis"]) else str(source["basis"]).strip()
    result = {"historical_identity_count": 85, "b2b_analytical_count": 84, "current_actionable_count": 83}
    audit(db, actor, "locked_account_context_bootstrap", "dim_account", None, {
        "package_sha256": FINAL_PACKAGE_SHA256, **result, "publication_required": True,
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Load verified account context from the authorized final package.")
    parser.add_argument("package", help="PESLC_FINAL_ANALYTICS_LOCKED.zip")
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            result = bootstrap(db, args.package, args.actor)
            db.commit()
            print(
                f"Verified {result['historical_identity_count']} identities; "
                f"{result['b2b_analytical_count']} are B2B analytical and "
                f"{result['current_actionable_count']} are currently actionable. Publish a new analytics run."
            )
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()