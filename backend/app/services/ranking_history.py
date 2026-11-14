"""Read-only access to fixed study rankings, separate from operational publications."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import math
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import PrescriptiveValidationEvidence
from app.services.additional_validation_evidence import EVIDENCE_VERSION as TRANSITION_VERSION
from app.services.locked_packages import (
    FINAL_PACKAGE_SHA256, PREVIOUS_QA_PACKAGE_SHA256,
    read_package_csv, read_package_member, verified_package,
)

EVIDENCE_VERSION = "study-ranking-history-v1"
SCOPE = "annual_account_rankings"
MEMBERS = ("01_DATA/08_BACKTEST/rankings.csv", "01_DATA/06_PRIORITY/current_priority.csv",
           "01_DATA/08_BACKTEST/annual_rank_changes.csv")


def ranking_rows(content: bytes) -> list[dict]:
    historical, current, changes = [read_package_csv(content, member).to_dict("records") for member in MEMBERS]
    digests = {member: sha256(read_package_member(content, member)).hexdigest() for member in MEMBERS}
    transitions = {(int(r["to_year"]), r["account_key"]): r for r in changes}
    if len(historical) != 456 or len(current) != 83:
        raise ValueError("Study ranking source counts are inconsistent.")
    if len(changes) != 455 or len(transitions) != 455:
        raise ValueError("Duplicate or missing study transitions.")
    result = []
    for official, source in [(False, historical), (True, current)]:
        for r in source:
            cutoff = str(r["analysis_reference"] if official else r["cutoff"])
            year = date.fromisoformat(cutoff).year
            result.append({
                "account_key": str(r["account_key"]), "account_name": str(r["account_name"]),
                "cutoff": cutoff, "year": year, "study_reference_date": "2025-12-31",
                "rank": int(r["priority_rank"] if official else r["historical_rank"]),
                "fps": float(r["final_priority_score"] if official else r["historical_fps"]),
                "priority_group": str(r["priority_group"]),
                "designation": "Official study baseline" if official else "Completed historical backtest",
                "evaluation_end": "2026-12-31" if official else str(r["evaluation_end"]),
                "outcome_status": "pending" if official else "observed",
                "subsequent_si_value": None if official else float(r["future_sales_12m"]),
                "source_member": MEMBERS[1 if official else 0],
                "source_member_sha256": digests[MEMBERS[1 if official else 0]],
            })
    keyed = {(r["year"], r["account_key"]): r for r in result}
    populations = {year: sum(r["year"] == year for r in result) for year in {r["year"] for r in result}}
    if len(keyed) != 539 or populations != {2018: 49, 2019: 57, 2020: 62, 2021: 66, 2022: 68, 2023: 76, 2024: 78, 2025: 83}:
        raise ValueError("Study ranking population differs from the approved source.")
    for r in result:
        if not math.isfinite(r["fps"]) or r["rank"] < 1 or r["rank"] > populations[r["year"]] or r["priority_group"] not in {"High", "Medium", "Low"}:
            raise ValueError("Invalid saved study ranking.")
        r["population"] = populations[r["year"]]
        r["previous"] = None
        t = transitions.get((r["year"], r["account_key"]))
        if t:
            previous = keyed.get((int(t["from_year"]), r["account_key"]))
            if previous is None or int(t["from_year"]) != r["year"] - 1:
                raise ValueError("Study transition has no consecutive-year source.")
            for side, source in [("old", previous), ("new", r)]:
                if (source["rank"] != int(t["historical_rank_" + side]) or
                    source["priority_group"] != t["priority_group_" + side] or
                    not math.isclose(source["fps"], float(t["historical_fps_" + side]), abs_tol=1e-12)):
                    raise ValueError("Study transition differs from saved ranking.")
            r["previous"] = {key: previous[key] for key in ("year", "rank", "fps", "population", "priority_group")}
            r["previous"].update({"positions": previous["rank"] - r["rank"],
                                  "group_changed": previous["priority_group"] != r["priority_group"],
                                  "source_member": MEMBERS[2], "source_member_sha256": digests[MEMBERS[2]]})
    return sorted(result, key=lambda r: (r["year"], r["rank"], r["account_key"]))


def seed_ranking_history(db: Session, package_path: str | Path) -> int:
    _, content = verified_package(package_path, FINAL_PACKAGE_SHA256)
    expected = ranking_rows(content)
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('study-ranking-history-v1'))"))
    # Existing transition evidence is retained and must agree with the same verified member.
    old = db.scalars(select(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == TRANSITION_VERSION,
        PrescriptiveValidationEvidence.evidence_scope == "annual_rank_changes")).all()
    approved = read_package_csv(content, MEMBERS[2]).to_dict("records")
    expected_transitions = {(int(r["to_year"]), str(r["account_key"])): r for r in approved}
    if len(old) != len(expected_transitions):
        raise ValueError("Registered transition evidence is unavailable or incomplete.")
    seen = set()
    for record in old:
        payload = record.payload
        key = (int(payload["to_year"]), str(payload["account_key"]))
        if (key in seen or key not in expected_transitions or
            record.source_package_hash not in {FINAL_PACKAGE_SHA256, PREVIOUS_QA_PACKAGE_SHA256} or
            payload.get("source_member_sha256") != sha256(read_package_member(content, MEMBERS[2])).hexdigest() or
            any(payload.get(k) != v for k, v in expected_transitions[key].items())):
            raise ValueError("Registered transitions differ from verified study evidence.")
        seen.add(key)
    existing = db.scalars(select(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION)).all()
    if existing:
        actual = {(r.payload.get("year"), r.payload.get("account_key")): r for r in existing}
        if len(actual) != len(existing) or len(actual) != len(expected) or any(
            (r["year"], r["account_key"]) not in actual or
            actual[(r["year"], r["account_key"])].payload != r or
            actual[(r["year"], r["account_key"])].evidence_scope != SCOPE or
            actual[(r["year"], r["account_key"])].source_package_hash != FINAL_PACKAGE_SHA256 for r in expected):
            raise ValueError("Existing ranking history differs from verified evidence.")
        return len(expected)
    db.add_all([PrescriptiveValidationEvidence(evidence_version=EVIDENCE_VERSION,
        evidence_scope=SCOPE, comparator=SCOPE, payload=r, source_package_hash=FINAL_PACKAGE_SHA256) for r in expected])
    return len(expected)


def ranking_history(db: Session, year: int | None, search: str, page: int, page_size: int) -> dict:
    records = db.scalars(select(PrescriptiveValidationEvidence).where(
        PrescriptiveValidationEvidence.evidence_version == EVIDENCE_VERSION,
        PrescriptiveValidationEvidence.evidence_scope == SCOPE)).all()
    if not records:
        raise ValueError("Verified study ranking history is unavailable.")
    rows = [r.payload for r in records]
    if (any(r.source_package_hash != FINAL_PACKAGE_SHA256 for r in records) or
        len({(r.get("year"), r.get("account_key")) for r in rows}) != len(rows) or
        any(not all(k in r for k in ("year", "rank", "fps", "account_key", "account_name", "population")) for r in rows) or
        len(rows) != 539):
        raise ValueError("Registered study ranking evidence failed integrity checks.")
    years = sorted({r["year"] for r in rows})
    selected_year = years[-1] if year is None else year
    if selected_year not in years:
        raise LookupError("Choose a year available in the registered study.")
    population = sum(r["year"] == selected_year for r in rows)
    query = search.strip().casefold()
    matching = sorted((r for r in rows if r["year"] == selected_year and query in r["account_name"].casefold()),
                      key=lambda r: (r["rank"], r["account_key"]))
    total = len(matching)
    page = min(page, max(1, math.ceil(total / page_size)))
    return {"evidence_status": "available", "study_reference_date": rows[0]["study_reference_date"],
            "years": years, "year": selected_year, "population": population,
            "total": total, "page": page, "page_size": page_size,
            "items": matching[(page - 1) * page_size:page * page_size]}
