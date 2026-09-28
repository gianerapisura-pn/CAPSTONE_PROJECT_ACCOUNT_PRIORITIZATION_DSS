from __future__ import annotations

import argparse

import pandas as pd
from sqlalchemy import select

from app.db.models import DimAccount
from app.db.repository import audit
from app.db.session import SessionLocal, init_database
from app.etl.standardization import standardize_account_name
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256,
    read_package_csv,
    verified_package,
)


def bootstrap(db, package_path: str, actor: str | None = None) -> dict:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    master = read_package_csv(content, "01_DATA/01_ACCOUNTS/account_master.csv")
    statuses = read_package_csv(content, "01_DATA/01_ACCOUNTS/account_status.csv")
    required_master = {
        "account_key", "account_name", "entity_type", "business_category", "primary_business_type"
    }
    required_status = {"account_key", "account_status", "last_verified"}
    if set(master.columns) != required_master:
        raise ValueError(f"Unexpected account_master.csv schema: {list(master.columns)}")
    if set(statuses.columns) != required_status:
        raise ValueError(f"Unexpected account_status.csv schema: {list(statuses.columns)}")
    merged = master.merge(statuses, on="account_key", how="left", validate="one_to_one")
    if len(merged) != 85:
        raise ValueError(f"Locked account master must contain 85 identities; found {len(merged)}.")
    existing = {
        row.standardized_account_name: row
        for row in db.scalars(select(DimAccount)).all()
    }
    updated = 0
    eligible = 0
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
        row.account_status = None if pd.isna(source["account_status"]) else str(source["account_status"]).strip()
        verified = pd.to_datetime(source["last_verified"], errors="coerce")
        row.last_verified = None if pd.isna(verified) else verified.date()
        row.b2b_priority_eligible = row.entity_type != "Individual/Personal"
        eligible += int(row.b2b_priority_eligible)
        updated += 1
    if eligible != 84:
        raise ValueError(f"Locked verified-B2B population must contain 84 identities; found {eligible}.")
    audit(db, actor, "locked_account_context_bootstrap", "dim_account", None, {
        "package_sha256": FINAL_PACKAGE_SHA256,
        "identity_count": updated,
        "verified_b2b_count": eligible,
        "publication_required": True,
    })
    return {"identity_count": updated, "verified_b2b_count": eligible}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load verified account master/status context from the authorized final package."
    )
    parser.add_argument("package", help="PESLC_FINAL_ANALYTICS_COMPLETE_FINAL_LOCKED.zip")
    parser.add_argument("--actor", default=None, help="Administrator UUID for audit attribution")
    args = parser.parse_args()
    init_database()
    with SessionLocal() as db:
        try:
            result = bootstrap(db, args.package, args.actor)
            db.commit()
            print(
                f"Verified {result['identity_count']} identities; "
                f"{result['verified_b2b_count']} are B2B eligible. Publish a new analytics run."
            )
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()