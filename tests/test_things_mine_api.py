from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth_google import require_google_user
from app.main import app


class RepoMineStub:
    def __init__(self):
        self.last_owner_sub = None

    def list_things(self, thing_type=None, from_ts=None, to_ts=None, owner_sub=None):
        self.last_owner_sub = owner_sub
        return [
            {
                "id": "55555555-5555-5555-5555-555555555555",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "type": thing_type or "mood",
                "value_num": 3,
                "value_text": None,
                "tags": None,
                "meta": {"owner_sub": owner_sub},
            }
        ]


def test_things_mine_requires_google_auth():
    client = TestClient(app)
    r = client.get("/things/mine")
    assert r.status_code == 401


def test_things_mine_filters_by_owner(monkeypatch):
    import app.things_api as things_api

    repo = RepoMineStub()
    app.dependency_overrides[require_google_user] = lambda: {"email": "user@example.com", "sub": "sub-123"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: repo)

    client = TestClient(app)
    r = client.get("/things/mine?type=mood")

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["type"] == "mood"
    assert repo.last_owner_sub == "sub-123"

    app.dependency_overrides.clear()
