from copy import deepcopy

import pytest

from app.services.normalization_evidence import normalization_evidence


def publication():
    return [
        {"account": "A", "recency_days": 10, "frequency_count": 2,
         "monetary_value": 100, "average_settlement_days": 20,
         "normalized_recency": 1, "normalized_frequency": 0,
         "normalized_monetary": 0, "normalized_settlement": 1},
        {"account": "B", "recency_days": 30, "frequency_count": 6,
         "monetary_value": 500, "average_settlement_days": 60,
         "normalized_recency": 0, "normalized_frequency": 1,
         "normalized_monetary": 1, "normalized_settlement": 0},
    ]


def test_explanations_read_saved_population_without_mutating_it():
    rows = publication()
    before = deepcopy(rows)
    result = normalization_evidence(rows, "A", "saved-run", "2031-12-31")
    assert result["eligible_account_count"] == 2
    assert result["analysis_run_id"] == "saved-run"
    assert result["analysis_reference_date"] == "2031-12-31"
    for criterion in result["criteria"].values():
        assert criterion["status"] == "verified"
        assert criterion["calculated_normalized"] == criterion["saved_normalized"]
    assert result["criteria"]["recency"]["minimum"] == 10
    assert result["criteria"]["frequency"]["maximum"] == 6
    assert rows == before
    later = publication()
    later[1]["recency_days"] = 90
    assert normalization_evidence(later, "A", "later-run", "2035-12-31")["criteria"]["recency"]["maximum"] == 90
    assert result["criteria"]["recency"]["maximum"] == 30


def test_constant_criterion_uses_saved_half_without_division_by_zero():
    rows = publication()
    for row in rows:
        row["frequency_count"] = 5
        row["normalized_frequency"] = .5
    evidence = normalization_evidence(rows, "A", "constant", "2030-12-31")["criteria"]["frequency"]
    assert evidence["minimum"] == evidence["maximum"] == 5
    assert evidence["calculated_normalized"] == .5
    assert evidence["status"] == "verified"


@pytest.mark.parametrize("bad_value", [None, "not a number", float("inf"), float("nan"), True])
def test_incomplete_population_never_invents_ranges(bad_value):
    rows = publication()
    rows[1]["monetary_value"] = bad_value
    evidence = normalization_evidence(rows, "A", "incomplete", None)["criteria"]["monetary"]
    assert evidence["status"] == "unavailable"
    assert evidence["minimum"] is evidence["maximum"] is None
    assert evidence["saved_normalized"] == 0


def test_unranked_account_and_conflicting_result_are_not_given_invented_explanations():
    rows = publication()
    unranked = normalization_evidence(rows, "C", "saved-run", "2031-12-31")
    assert all(item["status"] == "unavailable" for item in unranked["criteria"].values())
    rows[0]["normalized_recency"] = .1
    evidence = normalization_evidence(rows, "A", "saved-run", "2031-12-31")["criteria"]["recency"]
    assert evidence["status"] == "unreconciled"
    assert evidence["saved_normalized"] == .1
    assert rows[0]["normalized_recency"] == .1
