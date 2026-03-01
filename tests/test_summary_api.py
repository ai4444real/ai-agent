from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth_google import require_google_user
from app.main import app


class RepoSummaryStub:
    def list_things(self, thing_type=None, from_ts=None, to_ts=None):
        return [
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "type": "caffe",
                "value_num": None,
                "value_text": "corto",
            },
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "type": "caffe",
                "value_num": None,
                "value_text": "lungo",
            },
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "type": "mood",
                "value_num": 4,
                "value_text": None,
            },
        ]


def test_summary_window_requires_google_auth():
    client = TestClient(app)
    r = client.get("/things/summary-window?days=8")
    assert r.status_code == 401


def test_summary_window_returns_aggregates(monkeypatch):
    import app.things_api as things_api

    app.dependency_overrides[require_google_user] = lambda: {"email": "user@example.com"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: RepoSummaryStub())

    client = TestClient(app)
    r = client.get("/things/summary-window?days=8", headers={"Authorization": "Bearer fake"})

    assert r.status_code == 200
    body = r.json()
    assert body["window_days"] == 8
    assert body["total_entries"] == 3
    assert body["by_type"]["caffe"] == 2
    assert body["coffee_today"] >= 0

    app.dependency_overrides.clear()
