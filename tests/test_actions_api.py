from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app


class RepoForLatest:
    def list_latest_runs(self, limit: int = 10):
        return [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "created_at": "2026-03-01T10:00:00+00:00",
                "action": "weekly_report",
                "status": "success",
                "input_summary": {"from": "x", "to": "y"},
                "error": None,
            }
        ][:limit]


class RepoForWeeklyFailure:
    def __init__(self):
        self.finished = []
        self.messages = []
        self.last_owner_sub = None

    def create_run(self, action: str, input_summary=None, owner_sub=None, owner_email=None):
        return {"id": "22222222-2222-2222-2222-222222222222"}

    def get_config_text(self, key: str):
        return None

    def get_user_report_rules(self, owner_sub: str):
        return None

    def list_things(self, thing_type=None, from_ts=None, to_ts=None, owner_sub=None):
        self.last_owner_sub = owner_sub
        return [{"value_num": 3}, {"value_num": 4}, {"value_num": 2}]

    def update_run_input_summary(self, run_id, input_summary):
        return {"id": run_id, "input_summary": input_summary}

    def finish_run(self, run_id, status: str, error=None):
        self.finished.append({"run_id": run_id, "status": status, "error": error})
        return self.finished[-1]

    def insert_message(self, channel, recipient, subject, body, action, run_id, owner_sub=None, owner_email=None):
        self.messages.append(
            {
                "channel": channel,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "action": action,
                "run_id": run_id,
                "owner_sub": owner_sub,
                "owner_email": owner_email,
            }
        )
        return self.messages[-1]


class FakeMailerFailThenPass:
    def __init__(self):
        self.calls = []

    async def send_plain_text(self, subject: str, body: str, recipient=None):
        self.calls.append({"subject": subject, "body": body, "recipient": recipient})
        if len(self.calls) == 1:
            raise RuntimeError("primary mail failed")


class FakeLLM:
    def generate_signal_and_micro_action(self, report_payload, rules_text=None):
        return None


def test_latest_runs_requires_token(monkeypatch):
    import app.actions_api as actions_api
    import app.auth as auth

    monkeypatch.setattr(actions_api, "SupabaseRepo", lambda: RepoForLatest())
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="test-token"))

    client = TestClient(app)

    r_unauth = client.get("/actions/runs/latest")
    assert r_unauth.status_code == 401

    r = client.get("/actions/runs/latest", headers={"X-Trigger-Token": "test-token"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["action"] == "weekly_report"


def test_weekly_report_failure_sends_alert(monkeypatch):
    import app.actions_api as actions_api
    import app.auth as auth

    repo = RepoForWeeklyFailure()
    mailer = FakeMailerFailThenPass()

    monkeypatch.setattr(actions_api, "SupabaseRepo", lambda: repo)
    monkeypatch.setattr(actions_api, "mailer", mailer)
    monkeypatch.setattr(actions_api, "OpenAIReportHelper", lambda: FakeLLM())
    monkeypatch.setattr(
        actions_api,
        "compute_week_window_utc",
        lambda **kwargs: (
            datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        actions_api,
        "get_settings",
        lambda: SimpleNamespace(mail_to="ops@example.com", report_window_days=8),
    )
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="test-token"))

    client = TestClient(app)
    r = client.post("/actions/weekly-report", headers={"X-Trigger-Token": "test-token"})

    assert r.status_code == 500
    assert len(mailer.calls) == 2
    assert mailer.calls[1]["subject"] == "Weekly report failed"
    assert repo.finished[-1]["status"] == "fail"
    assert repo.messages[-1]["action"] == "weekly_report_fail_alert"


def test_weekly_report_uses_owner_filter_when_provided(monkeypatch):
    import app.actions_api as actions_api
    import app.auth as auth

    repo = RepoForWeeklyFailure()
    mailer = FakeMailerFailThenPass()

    monkeypatch.setattr(actions_api, "SupabaseRepo", lambda: repo)
    monkeypatch.setattr(actions_api, "mailer", mailer)
    monkeypatch.setattr(actions_api, "OpenAIReportHelper", lambda: FakeLLM())
    monkeypatch.setattr(
        actions_api,
        "compute_week_window_utc",
        lambda **kwargs: (
            datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        actions_api,
        "get_settings",
        lambda: SimpleNamespace(mail_to="ops@example.com", report_window_days=8),
    )
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="test-token"))

    client = TestClient(app)
    r = client.post(
        "/actions/weekly-report",
        headers={"X-Trigger-Token": "test-token"},
        json={"owner_sub": "sub-xyz", "owner_email": "user@example.com"},
    )

    assert r.status_code == 500
    assert repo.last_owner_sub == "sub-xyz"
