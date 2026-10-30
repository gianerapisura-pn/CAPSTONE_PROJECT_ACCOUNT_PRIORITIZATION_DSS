from typing import Literal

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AccountFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: str = Field(default="", max_length=200)
    priority_group: Literal["High", "Medium", "Low"] | None = None
    predicted_future_transaction_class: Literal["With Future Sales", "With No Future Sales"] | None = None
    eligibility: Literal["ranked", "not_ranked", "all"] | None = None
    business_category: str | None = Field(default=None, min_length=1, max_length=200)
    primary_business_type: str | None = Field(default=None, min_length=1, max_length=200)
    account_status: str | None = Field(default=None, min_length=1, max_length=100)
    rfm_component: Literal["Recency", "Frequency", "Monetary"] | None = None
    rfm_score: int | None = Field(default=None, ge=1, le=5)
    settlement_range: Literal["Below 30", "30-<60", "60-<90", "90-<120", "120+"] | None = None
    sort_by: Literal["rank", "account", "score"] = "rank"
    sort_direction: Literal["asc", "desc"] = "asc"


def read_account_filters(request: Request) -> AccountFilters:
    # Pagination and export format are validated by their route parameters.
    allowed_route_fields = {"page", "page_size"} if request.url.path.startswith("/accounts") else {"format"}
    params = {key: value for key, value in request.query_params.items() if key not in allowed_route_fields}
    if any(len(request.query_params.getlist(key)) > 1 for key in request.query_params):
        raise HTTPException(422, "Specify each account filter once.")
    try:
        return AccountFilters.model_validate(params)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_context=False)) from error


def validate_snapshot_filters(rows, filters: AccountFilters):
    options = {field: sorted({row[field] for row in rows if row.get(field)})
               for field in ("business_category", "primary_business_type", "account_status")}
    for field, choices in options.items():
        selected = getattr(filters, field)
        if selected is not None and selected not in choices:
            raise HTTPException(422, f"Unknown {field} for the published account population.")
    return options
