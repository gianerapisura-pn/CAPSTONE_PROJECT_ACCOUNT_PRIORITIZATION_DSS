import json
from types import SimpleNamespace

import pandas as pd
import pytest

from app.services import prescriptive_evidence as evidence


def fixture_rows(monkeypatch):
    frame = pd.DataFrame([{'metric': 'first', 'value': 1}, {'metric': 'second', 'value': 2}])
    monkeypatch.setattr(evidence, 'read_package_csv', lambda _content, _member: frame)
    rows = []
    for scope, members in evidence.PURPOSEFUL_SUMMARIES.items():
        for member in members:
            for index, source in enumerate(frame.to_dict('records'), 1):
                payload = {'source_member': member, 'row': index, **source}
                rows.append(SimpleNamespace(
                    evidence_scope=scope,
                    source_package_hash=evidence.FINAL_PACKAGE_SHA256,
                    payload=json.loads(json.dumps(payload, sort_keys=True)),
                ))
    return rows


def database(rows):
    return SimpleNamespace(scalars=lambda _statement: SimpleNamespace(all=lambda: list(reversed(rows))))


def test_jsonb_key_order_and_database_row_order_do_not_change_evidence(monkeypatch):
    rows = fixture_rows(monkeypatch)
    assert evidence.unchanged_prescriptive_evidence(database(rows), b'verified-content')


@pytest.mark.parametrize('change', ['value', 'duplicate', 'missing'])
def test_jsonb_comparison_still_rejects_changed_or_incomplete_evidence(monkeypatch, change):
    rows = fixture_rows(monkeypatch)
    if change == 'value':
        rows[0].payload['value'] = 999
    elif change == 'duplicate':
        rows.append(rows[0])
    else:
        rows.pop()
    with pytest.raises(ValueError, match='differs from the revised package'):
        evidence.unchanged_prescriptive_evidence(database(rows), b'verified-content')
