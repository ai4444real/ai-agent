from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.auth_google import require_google_user
from app.main import app


class RepoMineReportStub:
    def __init__(self):
        self.last_owner_sub = None

    def create_run(self, action: str, input_summary=None, owner_sub=None, owner_email=None):
        return {"id": "77777777-7777-7777-7777-777777777777"}

    def list_things(self, thing_type=None, from_ts=None, to_ts=None, owner_sub=None):
        self.last_owner_sub = owner_sub
        return [{"type": "mood", "value_num": 3, "created_at": datetime.now(timezone.utc).isoformat()}]

    def get_config_text(self, key: str):
        return None

    def get_user_report_rules(self, owner_sub: str):
        return None

    def update_run_input_summary(self, run_id, input_summary):
        return {"id": run_id}

    def insert_message(self, channel, recipient, subject, body, action, run_id, owner_sub=None, owner_email=None):
        return {"id": "m1"}

    def finish_run(self, run_id, status: str, error=None):
        return {"id": run_id, "status": status}


class MailerOk:
    async def send_plain_text(self, subject: str, body: str, recipient=None):
        return None


class LLMNone:
    def generate_signal_and_micro_action(self, report_payload, rules_text=None):
        return None

    def generate_smart_weekly_report(self, context_payload, rules_text=None, tool_executor=None, max_rounds=6):
        return "Report smart test", [{"name": "get_window_coverage"}]


def test_weekly_report_mine_requires_google_auth():
    client = TestClient(app)
    r = client.post("/actions/weekly-report-mine")
    assert r.status_code == 401


def test_weekly_report_mine_filters_by_owner(monkeypatch):
    import app.actions_api as actions_api

    repo = RepoMineReportStub()
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-mine", "email": "mine@example.com"}
    monkeypatch.setattr(actions_api, "SupabaseRepo", lambda: repo)
    monkeypatch.setattr(actions_api, "mailer", MailerOk())
    monkeypatch.setattr(actions_api, "OpenAIReportHelper", lambda: LLMNone())

    client = TestClient(app)
    r = client.post("/actions/weekly-report-mine")

    assert r.status_code == 200
    assert repo.last_owner_sub == "sub-mine"

    app.dependency_overrides.clear()


def test_weekly_report_smart_mine_filters_by_owner(monkeypatch):
    import app.actions_api as actions_api

    repo = RepoMineReportStub()
    app.dependency_overrides[require_google_user] = lambda: {"sub": "sub-smart", "email": "smart@example.com"}
    monkeypatch.setattr(actions_api, "SupabaseRepo", lambda: repo)
    monkeypatch.setattr(actions_api, "mailer", MailerOk())
    monkeypatch.setattr(actions_api, "OpenAIReportHelper", lambda: LLMNone())

    client = TestClient(app)
    r = client.post("/actions/weekly-report-smart-mine")

    assert r.status_code == 200
    assert r.json()["action"] == "weekly_report_smart"
    assert repo.last_owner_sub == "sub-smart"

    app.dependency_overrides.clear()
