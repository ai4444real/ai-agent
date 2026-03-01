from fastapi.testclient import TestClient

from app.main import app


class ConfigRepoStub:
    def __init__(self):
        self.user_store = {}
        self.tracker_store = {}

    def get_user_report_rules(self, owner_sub: str):
        return self.user_store.get(owner_sub)

    def set_user_report_rules(self, owner_sub: str, owner_email: str | None, value_text: str):
        self.user_store[owner_sub] = value_text
        return {"owner_sub": owner_sub, "owner_email": owner_email, "value_text": value_text}

    def get_user_tracker_config(self, owner_sub: str):
        return self.tracker_store.get(owner_sub)

    def set_user_tracker_config(self, owner_sub: str, owner_email: str | None, value_text: str):
        self.tracker_store[owner_sub] = value_text
        return {"owner_sub": owner_sub, "owner_email": owner_email, "value_text": value_text}


def test_report_rules_mine_requires_google_auth(monkeypatch):
    import app.config_api as config_api

    monkeypatch.setattr(config_api, "SupabaseRepo", lambda: ConfigRepoStub())
    client = TestClient(app)

    r = client.get("/config/report-rules-mine")
    assert r.status_code == 401

    r_tracker = client.get("/config/tracker-config-mine")
    assert r_tracker.status_code == 401


def test_report_rules_mine_get_put(monkeypatch):
    import app.config_api as config_api
    from app.auth_google import require_google_user

    repo = ConfigRepoStub()
    monkeypatch.setattr(config_api, "SupabaseRepo", lambda: repo)
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-1", "email": "user@example.com"}

    client = TestClient(app)

    r_get = client.get("/config/report-rules-mine")
    assert r_get.status_code == 200
    assert r_get.json()["text"] is None

    r_put = client.put("/config/report-rules-mine", json={"text": "my rules"})
    assert r_put.status_code == 200
    assert r_put.json()["text"] == "my rules"

    r_get2 = client.get("/config/report-rules-mine")
    assert r_get2.status_code == 200
    assert r_get2.json()["text"] == "my rules"

    app.dependency_overrides.clear()


def test_tracker_config_mine_get_put(monkeypatch):
    import app.config_api as config_api
    from app.auth_google import require_google_user

    repo = ConfigRepoStub()
    monkeypatch.setattr(config_api, "SupabaseRepo", lambda: repo)
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-1", "email": "user@example.com"}

    client = TestClient(app)

    r_get = client.get("/config/tracker-config-mine")
    assert r_get.status_code == 200
    assert r_get.json()["text"] is None

    payload = '[{"type":"mood","title":"Mood","valueKind":"num","choices":[{"value":1,"label":"1"}]}]'
    r_put = client.put("/config/tracker-config-mine", json={"text": payload})
    assert r_put.status_code == 200
    assert r_put.json()["text"] == payload

    r_get2 = client.get("/config/tracker-config-mine")
    assert r_get2.status_code == 200
    assert r_get2.json()["text"] == payload

    app.dependency_overrides.clear()
