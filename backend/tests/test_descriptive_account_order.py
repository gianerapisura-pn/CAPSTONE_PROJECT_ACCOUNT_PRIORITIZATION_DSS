from copy import deepcopy
from datetime import date, datetime, timezone
from io import BytesIO
from uuid import UUID

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import AuthenticatedUser, require_user
from app.db.models import AccountPriorityResult, AnalyticsRun, Base, DimAccount, RFMResult, SettlementResult
from app.db.repository import run_payload
from app.db.session import get_db
from app.main import app


@pytest.mark.parametrize('dataset,model', [('rfm', RFMResult), ('settlement', SettlementResult)])
def test_descriptive_account_order_is_global_stable_and_shared_with_exports(dataset, model):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    names = ['zulu', 'alpha', 'BRAVO', 'Alpha', 'ALPHA', 'bravo', 'delta', 'Echo',
             'foxtrot', 'GOLF', 'hotel', 'India', 'juliet', 'KILO', 'lima', 'Mike',
             'november', 'OSCAR', 'papa', 'Quebec', 'romeo', 'SIERRA', 'alpha']
    with Session(engine) as db:
        run = AnalyticsRun(status='successful', analysis_reference_date=date(2030, 12, 31),
                           completed_at=datetime(2031, 1, 1, tzinfo=timezone.utc))
        older = AnalyticsRun(status='successful', analysis_reference_date=date(2029, 12, 31),
                             completed_at=datetime(2030, 1, 1, tzinfo=timezone.utc))
        db.add_all([run, older])
        db.flush()
        expected = []
        for index, name in enumerate(names):
            key = str(UUID(int=index + 1))
            db.add(DimAccount(account_key=key, standardized_account_name=f'IDENTITY {index}', display_name=name))
            payload = ({'account': name, 'recency_days': index + 1, 'frequency': 50 - index,
                        'monetary': 1000 + index, 'r_score': 5, 'f_score': 4, 'm_score': 3,
                        'rfm_mean_score': 5 - index / 32}
                       if dataset == 'rfm' else
                       {'account': name, 'settlement_invoice_count': index + 1,
                        'average_settlement_days': 100 - index / 4, 'final_collection_days_max': 200 - index})
            db.add(model(analysis_run_id=run.analysis_run_id, account_key=key, payload=payload))
            db.add(AccountPriorityResult(analysis_run_id=run.analysis_run_id, account_key=key,
                                        standardized_account_name=name,
                                        payload={'account': name, 'priority_rank': len(names) - index,
                                                 'final_priority_score': index / 32}))
            expected.append((key, deepcopy(payload)))
        db.add(model(analysis_run_id=older.analysis_run_id, account_key=str(UUID(int=1)), payload={'account': 'AAA OLD RUN'}))
        db.commit()
        expected.sort(key=lambda item: (item[1]['account'].casefold(), item[1]['account'], item[0]))
        ordered = [payload for _, payload in expected]
        before = {row.id: deepcopy(row.payload) for row in db.scalars(select(model))}
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_user] = lambda: AuthenticatedUser('test-admin', 'administrator')
        try:
            client = TestClient(app)
            for reverse in ['OFF', 'ON']:
                # Deliberately change unordered retrieval to prove we do not rely on insertion order.
                db.execute(text(f'PRAGMA reverse_unordered_selects={reverse}'))
                for _ in range(2):
                    response = client.get(f'/analytics/{dataset}')
                    assert response.status_code == 200
                    rows = response.json()['items']
                    assert rows == ordered
                    assert [row for start in range(0, len(rows), 10) for row in rows[start:start + 10]] == ordered
                    assert [len(rows[start:start + 10]) for start in range(0, len(rows), 10)] == [10, 10, 3]
                for format in ['csv', 'xlsx']:
                    exported = client.get(f'/exports/{dataset}.{format}')
                    assert exported.status_code == 200
                    frame = (pd.read_csv(BytesIO(exported.content)) if format == 'csv'
                             else pd.read_excel(BytesIO(exported.content)))
                    assert frame['account'].tolist() == [row['account'] for row in ordered]
                    assert frame.drop(columns=['analysis_run_id', 'analysis_reference_date']).to_dict('records') == ordered
                    assert frame['analysis_run_id'].tolist() == [run.analysis_run_id] * len(ordered)
                priorities = run_payload(db, run)['priorities']
                assert [row['priority_rank'] for row in priorities] == list(range(1, len(names) + 1))
            assert {row.id: row.payload for row in db.scalars(select(model))} == before
        finally:
            app.dependency_overrides.clear()
    engine.dispose()
