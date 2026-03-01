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

### Insert mood

```bash
curl -X POST http://127.0.0.1:8000/things \
  -H "Content-Type: application/json" \
  -d '{"type":"mood","value_num":3}'
```

### List things

```bash
curl "http://127.0.0.1:8000/things?type=mood"
```

### Mood quick (Google login)

Open:

```text
http://127.0.0.1:8000/mood.html
```

Then login with Google and click mood `1..5`.
Main home is also available on `/` with mood + generic quick form.

### Trigger weekly report

```bash
curl -X POST http://127.0.0.1:8000/actions/weekly-report \
  -H "X-Trigger-Token: YOUR_TRIGGER_TOKEN"
```

### Read latest runs

```bash
curl "http://127.0.0.1:8000/actions/runs/latest?limit=10" \
  -H "X-Trigger-Token: YOUR_TRIGGER_TOKEN"
```

## 5) Deploy on Render

1. Create new Web Service from repo.
2. Runtime: Docker.
3. Set all env vars from `.env`.
4. Deploy and verify `/health`.

## 6) Scheduler on cron-job.org

- URL: `https://<render-app>/actions/weekly-report`
- Method: `POST`
- Header: `X-Trigger-Token: <TRIGGER_TOKEN>`
- Header: `Content-Type: application/json`
- Body: `{}`
- Schedule: Sunday 07:00 Europe/Zurich

## MVP included

- `POST /things`
- `GET /things`
- `POST /actions/weekly-report`
- `GET /health`
- Logging on `runs` and `messages`

## Not in MVP

- `daily-missing-check`
- data integrations in `data_snapshots`
- extended test suite / CI
