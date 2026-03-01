# Minimal Accountability Server (MVP)

FastAPI service that stores things (mood), runs scheduled actions, sends email reports, and logs runs/messages on Supabase.

## 1) Setup Supabase

1. Create a Supabase project.
2. Run `schema.sql` in SQL editor.
3. Copy `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

## 2) Environment variables

Create `.env`:

```env
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
TRIGGER_TOKEN=
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
MAIL_FROM=
MAIL_TO=
APP_TIMEZONE=Europe/Zurich
REPORT_WINDOW_DAYS=8
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
GOOGLE_CLIENT_ID=
GOOGLE_ALLOWED_EMAILS=
```

## 3) Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## 4) API

### Tracker app (Google login)

Open:

```text
http://127.0.0.1:8000/
```

Then login with Google and use tracker cards.
Home is config-driven: trackers load from `/config/tracker-config-mine` (if present), otherwise fallback to default config in `static/index.html` (`DEFAULT_TRACKER_CONFIGS`). Choices post to `/things/choice-quick`.
Weekly report uses a configurable time window (`REPORT_WINDOW_DAYS`, default `8`) and aggregates all tracked types before calling AI.

### Read my things

```bash
curl "http://127.0.0.1:8000/things-mine?type=mood" \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN"
```

### Trigger weekly report

```bash
curl -X POST http://127.0.0.1:8000/actions/weekly-report \
  -H "X-Trigger-Token: YOUR_TRIGGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"owner_sub":"YOUR_OWNER_SUB","owner_email":"you@example.com"}'
```

### Trigger my weekly report

```bash
curl -X POST http://127.0.0.1:8000/actions/weekly-report-mine \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN"
```

### Read latest runs

```bash
curl "http://127.0.0.1:8000/actions/runs/latest?limit=10" \
  -H "X-Trigger-Token: YOUR_TRIGGER_TOKEN"
```

### Report rules config (per user)

Get:

```bash
curl "http://127.0.0.1:8000/config/report-rules-mine" \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN"
```

Put:

```bash
curl -X PUT "http://127.0.0.1:8000/config/report-rules-mine" \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"your long report rules here"}'
```

### Tracker config (per user)

Get:

```bash
curl "http://127.0.0.1:8000/config/tracker-config-mine" \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN"
```

Put:

```bash
curl -X PUT "http://127.0.0.1:8000/config/tracker-config-mine" \
  -H "Authorization: Bearer YOUR_GOOGLE_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"[{\"type\":\"mood\",\"title\":\"Mood\",\"valueKind\":\"num\",\"choices\":[{\"value\":1,\"label\":\"1\"}]}]"}'
```

## 5) Deploy on Render

1. Create new Web Service from repo.
2. Runtime: Docker.
3. Set all env vars from `.env`.
4. Deploy and verify `/health`.

## 6) Scheduler on cron-job.org

- URL: `https://<render-app>/actions/weekly-report-dispatch`
- Method: `POST`
- Header: `X-Trigger-Token: <TRIGGER_TOKEN>`
- Header: `Content-Type: application/json`
- Body: `{}`
- Schedule: Sunday 07:00 Europe/Zurich

## MVP included

- `POST /things/choice-quick`
- `GET /things-mine`
- `POST /actions/weekly-report-mine`
- `POST /actions/weekly-report-dispatch`
- `GET /health`
- Logging on `runs` and `messages`

## Not in MVP

- `daily-missing-check`
- data integrations in `data_snapshots`
- extended test suite / CI
