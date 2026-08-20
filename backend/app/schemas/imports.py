from pydantic import BaseModel


class ValidationIssueSchema(BaseModel):
    row_number: int | None
    column: str | None
    severity: str
    message: str


class ImportPreviewSchema(BaseModel):
    file_name: str | None
    file_hash: str
    sheets: list[str]
    rows_discovered: int
    issues: list[ValidationIssueSchema]
    can_commit: bool
