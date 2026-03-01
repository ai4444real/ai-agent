from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth_google import require_google_user
from app.main import app


class RepoDeleteMineStub:
    def __init__(self):
        self.deleted = []

    def get_thing_by_id_owner(self, thing_id: str, owner_sub: str):
        if thing_id == "66666666-6666-6666-6666-666666666666" and owner_sub == "sub-1":
            return {
                "id": thing_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "type": "mood",
                "value_num": 3,
            }
        return None

    def delete_thing_by_id_owner(self, thing_id: str, owner_sub: str):
        self.deleted.append((thing_id, owner_sub))


def test_delete_my_thing_requires_google_auth():
    client = TestClient(app)
    r = client.delete("/things-mine/66666666-6666-6666-6666-666666666666")
    assert r.status_code == 401


def test_delete_my_thing_success(monkeypatch):
    import app.things_api as things_api

    repo = RepoDeleteMineStub()
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-1", "email": "u@example.com"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: repo)

    client = TestClient(app)
    r = client.delete("/things-mine/66666666-6666-6666-6666-666666666666")

    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert repo.deleted == [("66666666-6666-6666-6666-666666666666", "sub-1")]

    app.dependency_overrides.clear()


def test_delete_my_thing_not_found(monkeypatch):
    import app.things_api as things_api

    repo = RepoDeleteMineStub()
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-1", "email": "u@example.com"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: repo)

    client = TestClient(app)
    r = client.delete("/things-mine/77777777-7777-7777-7777-777777777777")

    assert r.status_code == 404

    app.dependency_overrides.clear()
