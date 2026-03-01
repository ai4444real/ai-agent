from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


class ConfigRepoStub:
    def __init__(self):
        self.store = {"report_rules": "baseline rules"}

    def get_config_text(self, key: str):
        return self.store.get(key)

    def set_config_text(self, key: str, value_text: str):
        self.store[key] = value_text
        return {"key": key, "value_text": value_text}


def test_report_rules_requires_trigger_token(monkeypatch):
    import app.auth as auth
    import app.config_api as config_api

    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="tkn"))
    monkeypatch.setattr(config_api, "SupabaseRepo", lambda: ConfigRepoStub())

    client = TestClient(app)

    r = client.get("/config/report-rules")
    assert r.status_code == 401


def test_report_rules_get_and_put(monkeypatch):
    import app.auth as auth
    import app.config_api as config_api

    repo = ConfigRepoStub()
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="tkn"))
    monkeypatch.setattr(config_api, "SupabaseRepo", lambda: repo)

    client = TestClient(app)
    headers = {"X-Trigger-Token": "tkn"}

    r_get = client.get("/config/report-rules", headers=headers)
    assert r_get.status_code == 200
    assert r_get.json()["text"] == "baseline rules"

    r_put = client.put("/config/report-rules", headers=headers, json={"text": "new long rules"})
    assert r_put.status_code == 200
    assert r_put.json()["text"] == "new long rules"

    r_get2 = client.get("/config/report-rules", headers=headers)
    assert r_get2.status_code == 200
    assert r_get2.json()["text"] == "new long rules"
