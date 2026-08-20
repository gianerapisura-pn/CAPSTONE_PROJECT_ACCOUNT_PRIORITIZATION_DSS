from __future__ import annotations

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.auth.dependencies import AuthenticatedUser, require_admin, require_user
from app.core.config import get_settings
from app.etl.invoices import dataframe_to_source_rows, group_invoices
from app.imports.validators import parse_source_file, validate_rows
from app.services.analytics_runner import run_account_prioritization

settings = get_settings()
app = FastAPI(title="PESLC Account Prioritization DSS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "demo_mode": settings.demo_mode}


@app.post("/imports/preview")
async def preview_import(file: UploadFile = File(...), user: AuthenticatedUser = Depends(require_user)) -> dict:
    content = await file.read()
    parsed = parse_source_file(file.filename or "upload", content)
    row_issues = []
    rows_discovered = 0
    for frame in parsed.frames.values():
        rows_discovered += len(frame)
        row_issues.extend(validate_rows(frame))
    return {
        "file_name": file.filename,
        "file_hash": parsed.file_hash,
        "sheets": list(parsed.frames.keys()),
        "rows_discovered": rows_discovered,
        "issues": [issue.__dict__ for issue in [*parsed.issues, *row_issues]],
        "can_commit": not any(issue.severity == "error" for issue in [*parsed.issues, *row_issues]),
    }


@app.post("/analytics/run-demo")
async def run_demo(file: UploadFile = File(...), user: AuthenticatedUser = Depends(require_admin)) -> dict:
    content = await file.read()
    parsed = parse_source_file(file.filename or "upload", content)
    all_issues = list(parsed.issues)
    frames = []
    for frame in parsed.frames.values():
        all_issues.extend(validate_rows(frame))
        frames.append(frame)
    if any(issue.severity == "error" for issue in all_issues):
        raise HTTPException(status_code=422, detail=[issue.__dict__ for issue in all_issues])
    rows = []
    for frame in frames:
        rows.extend(dataframe_to_source_rows(frame, import_batch_id=parsed.file_hash[:12]))
    invoice_groups = group_invoices(rows)
    result = run_account_prioritization(invoice_groups)
    return result.__dict__
