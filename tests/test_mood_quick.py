from fastapi.testclient import TestClient

from app.auth_google import require_google_user
from app.main import app


class RepoStub:
    def insert_thing(self, payload):
        return {
            "id": "33333333-3333-3333-3333-333333333333",
            "created_at": "2026-03-01T12:00:00+00:00",
            "type": payload["type"],
            "value_num": payload.get("value_num"),
            "value_text": payload.get("value_text"),
            "tags": None,
            "meta": payload.get("meta"),
        }


def test_mood_quick_requires_google_auth():
    client = TestClient(app)
    r = client.post("/things/mood-quick", json={"value_num": 3})
    assert r.status_code == 401

    r_text = client.post("/things/text-quick", json={"type": "note", "value_text": "hello"})
    assert r_text.status_code == 401


def test_mood_quick_success_with_google_override(monkeypatch):
    import app.things_api as things_api

    app.dependency_overrides[require_google_user] = lambda: {"email": "user@example.com"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: RepoStub())

    client = TestClient(app)
    r = client.post("/things/mood-quick", json={"value_num": 4})

    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "mood"
    assert int(body["value_num"]) == 4
    assert body["meta"]["google_email"] == "user@example.com"

    app.dependency_overrides.clear()


def test_text_quick_success_with_google_override(monkeypatch):
    import app.things_api as things_api

    app.dependency_overrides[require_google_user] = lambda: {"email": "user@example.com"}
    monkeypatch.setattr(things_api, "SupabaseRepo", lambda: RepoStub())

    client = TestClient(app)
    r = client.post("/things/text-quick", json={"type": "note", "value_text": "deep work 45m"})

    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "note"
    assert body["value_text"] == "deep work 45m"
    assert body["meta"]["google_email"] == "user@example.com"

    app.dependency_overrides.clear()
