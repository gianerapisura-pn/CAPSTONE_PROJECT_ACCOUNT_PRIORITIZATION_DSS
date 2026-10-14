from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthenticatedUser
from app.db.models import Base, ImportBatch, InvoiceGroupRecord, SICoverageConfirmation
from app.services.import_workflow import commit_source, preview_source
from app.services.si_coverage import confirm_si_coverage, latest_verified_si_coverage, require_si_coverage
from app.services.storage import SourceStorage
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import parse_source_file
from app.auth.dependencies import require_admin
from app.main import app
from fastapi.routing import APIRoute


ADMIN = AuthenticatedUser("00000000-0000-4000-8000-000000000001", "administrator")
HEADER = "ACCOUNT NAMES,SI NO.,SI DATE,SI AMOUNT,CR NO.,CR DATE,CR AMOUNT,EWT,PAYMENT MODE,PAYMENT STATUS\n"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _preview(db, monkeypatch, content: bytes):
    monkeypatch.setattr(SourceStorage, "put", lambda self, batch_id, name, data: "private/test.csv")
    monkeypatch.setattr(SourceStorage, "get", lambda self, path: content)
    return preview_source(db, ADMIN, "test.csv", content)


def test_coverage_is_independent_of_reference_and_immutable_when_superseded(db):
    with pytest.raises(ValueError, match="No independently recorded"):
        require_si_coverage(db, date(2025, 12, 31))
    batch = ImportBatch(file_name="source.csv", file_hash="a" * 64, status="previewed")
    db.add(batch)
    db.flush()
    first = confirm_si_coverage(
        db, complete_through=date(2025, 12, 31), evidence_type="Client confirmation",
        evidence_reference="Client letter ref 123", evidence_basis="Client reviewed SI coverage",
        confirmed_on=date(2026, 1, 2), recorded_by=ADMIN.user_id,
        source_batch_id=batch.import_batch_id,
    )
    assert require_si_coverage(db, date(2025, 12, 31), batch.import_batch_id) is first
    with pytest.raises(ValueError, match="No independently recorded"):
        require_si_coverage(db, date(2025, 12, 31))
    assert latest_verified_si_coverage(db) is None
    batch.status = "committed"
    db.flush()
    assert latest_verified_si_coverage(db) == date(2025, 12, 31)
    replacement = confirm_si_coverage(
        db, complete_through=date(2025, 11, 30), evidence_type="Client confirmation",
        evidence_reference="Corrected letter ref 124", evidence_basis="Correction to SI coverage",
        confirmed_on=date(2026, 1, 3), recorded_by=ADMIN.user_id,
        source_batch_id=batch.import_batch_id,
        supersedes_confirmation_id=first.confirmation_id,
    )
    assert first.superseded_at is not None
    assert replacement.supersedes_confirmation_id == first.confirmation_id
    with pytest.raises(ValueError, match="No independently recorded"):
        require_si_coverage(db, date(2025, 12, 31))


def test_noncritical_collection_issue_keeps_si_but_not_settlement(db, monkeypatch):
    content = (HEADER + "ACME,SI-1,2025-07-01,100,CR-1,2025-07-10,bad,0,Bank,Fully Paid\n").encode()
    preview = _preview(db, monkeypatch, content)
    assert preview["can_commit"] is True
    assert (preview["rows_accepted"], preview["rows_flagged"], preview["rows_quarantined"]) == (0, 1, 0)
    with pytest.raises(HTTPException, match="complete-through"):
        commit_source(db, ADMIN, preview["import_batch_id"], date(2025, 12, 31))
    confirm_si_coverage(
        db, complete_through=date(2025, 12, 31), evidence_type="Client confirmation",
        evidence_reference="Letter ref 123", evidence_basis="Confirmed no further valid SI",
        confirmed_on=date(2026, 1, 2), recorded_by=ADMIN.user_id,
        source_batch_id=preview["import_batch_id"],
    )
    db.commit()
    result = commit_source(db, ADMIN, preview["import_batch_id"], date(2025, 12, 31))
    assert result["status"] == "COMMITTED"
    invoice = db.scalar(select(InvoiceGroupRecord))
    assert invoice.rfm_eligible is True
    assert invoice.settlement_eligible is False


def test_critical_si_issue_blocks_publication_and_keeps_preview(db, monkeypatch):
    content = (HEADER + "ACME,,2025-07-01,100,,,,,Bank,Fully Paid\n").encode()
    preview = _preview(db, monkeypatch, content)
    assert preview["can_commit"] is False
    assert preview["rows_quarantined"] == 1
    assert preview["publication_blockers"]
    with pytest.raises(HTTPException, match="Critical"):
        commit_source(db, ADMIN, preview["import_batch_id"], date(2025, 12, 31))
    assert db.get(ImportBatch, preview["import_batch_id"]).status == "previewed"


def test_structural_file_error_counts_discovered_rows_as_blocked(db, monkeypatch):
    preview = _preview(db, monkeypatch, b"ACCOUNT NAMES,SI NO.\nACME,SI-1\n")
    assert preview["rows_discovered"] == 1
    assert preview["rows_blocked"] == 1
    assert preview["rows_accepted"] == 0
    assert not preview["can_commit"]


def test_malformed_xlsx_is_a_preview_issue_not_a_server_error(db, monkeypatch):
    monkeypatch.setattr(SourceStorage, "put", lambda self, batch_id, name, data: "private/bad.xlsx")
    preview = preview_source(db, ADMIN, "bad.xlsx", b"not an excel archive")
    assert not preview["can_commit"]
    assert any(issue["issue_type"] == "file_parse" for issue in preview["issues"])


def test_changed_source_after_preview_is_rejected(db, monkeypatch):
    content = (HEADER + "ACME,SI-1,2025-07-01,100,,,,,Bank,Fully Paid\n").encode()
    preview = _preview(db, monkeypatch, content)
    monkeypatch.setattr(SourceStorage, "get", lambda self, path: content + b"changed")
    with pytest.raises(HTTPException, match="changed"):
        commit_source(db, ADMIN, preview["import_batch_id"], date(2025, 12, 31))
    assert db.scalar(select(SICoverageConfirmation)) is None


def test_missing_ewt_requires_independent_full_cr_reconciliation():
    content = (HEADER
               + "ACME,SI-1,2025-07-01,100,CR-1,2025-07-10,100,,Bank,Fully Paid\n"
               + "ACME,SI-2,2025-07-02,100,CR-2,2025-07-11,90,,Bank,Fully Paid\n").encode()
    frame = parse_source_file("source.csv", content).frames["CSV"]
    groups = {group.si_no: group for group in group_invoices(dataframe_to_source_rows(frame))}
    assert groups["SI-1"].settlement_eligible  # Full CR independently proves settlement.
    assert not groups["SI-2"].settlement_eligible


def test_si_coverage_routes_require_administrator():
    for path in ("/si-coverage",):
        routes = [route for route in app.routes if isinstance(route, APIRoute)
                  and route.path == path]
        assert {next(iter(route.methods)) for route in routes} == {"GET", "POST"}
        for route in routes:
            assert require_admin in {dependency.call for dependency in route.dependant.dependencies}
