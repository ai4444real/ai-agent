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

    def create_run(self, action: str, input_summary=None):
        return {"id": "22222222-2222-2222-2222-222222222222"}

    def list_things(self, thing_type=None, from_ts=None, to_ts=None):
        return [{"value_num": 3}, {"value_num": 4}, {"value_num": 2}]

    def finish_run(self, run_id, status: str, error=None):
        self.finished.append({"run_id": run_id, "status": status, "error": error})
        return self.finished[-1]

    def insert_message(self, channel, recipient, subject, body, action, run_id):
        self.messages.append(
            {
                "channel": channel,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "action": action,
                "run_id": run_id,
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
    def generate_signal_and_micro_action(self, metrics):
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
        lambda: (
            datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        ),
    )
    monkeypatch.setattr(
        actions_api,
        "get_settings",
        lambda: SimpleNamespace(mail_to="ops@example.com"),
    )
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(trigger_token="test-token"))

    client = TestClient(app)
    r = client.post("/actions/weekly-report", headers={"X-Trigger-Token": "test-token"})

    assert r.status_code == 500
    assert len(mailer.calls) == 2
    assert mailer.calls[1]["subject"] == "Weekly report failed"
    assert repo.finished[-1]["status"] == "fail"
    assert repo.messages[-1]["action"] == "weekly_report_fail_alert"
