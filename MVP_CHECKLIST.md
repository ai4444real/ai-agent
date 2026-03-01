# MVP Checklist (Delivery-First)

Data: 2026-03-01  
Obiettivo: arrivare al primo MVP funzionante nel minor tempo possibile, con struttura pulita e senza duplicazioni.

## Regole anti-deriva (sempre attive)

- Lavorare solo su feature che sbloccano il DoD MVP.
- Ogni task termina con una verifica concreta (test/smoke check).
- Niente refactor estetici prima del DoD.
- OpenAI e `daily-missing-check` non sono bloccanti MVP.
- Se un task supera il tempo previsto del 50%, si riduce scope e si passa oltre.

## Definition of Done MVP

- `POST /things` salva mood con validazione corretta.
- `POST /actions/weekly-report` legge ultimi 7 giorni, genera report deterministico, invia email.
- `runs` e `messages` vengono scritte correttamente su Supabase.
- Funziona anche senza `OPENAI_API_KEY`.
- Deploy su Render + trigger cron-job.org attivo.

## Sequenza bloccante (ordine obbligatorio)

## 1) Bootstrap progetto (2h)

- [ ] Creare struttura cartelle `app/`, `app/actions/`, `app/services/`, `app/prompts/`, `app/templates/`.
- [ ] Creare `requirements.txt` minimo.
- [ ] Creare `app/main.py` con FastAPI e `GET /health`.
- [ ] Creare `app/settings.py` con validazione ENV via `pydantic-settings`.
- [ ] Creare `Dockerfile` minimo per Render.

Exit criteria:
- [ ] Avvio locale (`uvicorn app.main:app`) senza errori.
- [ ] `GET /health` risponde `{ "ok": true }`.

## 2) Schema e repository Supabase (2h)

- [ ] Applicare SQL schema del DoC su Supabase.
- [ ] Implementare `app/services/supabase_repo.py` con metodi:
  - [ ] `insert_thing`
  - [ ] `list_things`
  - [ ] `create_run`
  - [ ] `finish_run`
  - [ ] `insert_message`

Exit criteria:
- [ ] Script/check manuale conferma insert/select su `things`.
- [ ] Nessuna query Supabase fuori da `supabase_repo.py`.

## 3) API Things (2h)

- [ ] Creare `app/models.py` con request/response models Pydantic.
- [ ] Implementare `app/things_api.py`.
- [ ] `POST /things` con regola: se `type="mood"`, `value_num` intero 1..5.
- [ ] `GET /things` con filtri `type`, `from`, `to`.
- [ ] Registrare router in `main.py`.

Exit criteria:
- [ ] Test smoke: insert mood valido -> 200.
- [ ] Test smoke: mood fuori range -> 422.
- [ ] Test smoke: GET con filtri restituisce dati attesi.

## 4) Core Actions + auth trigger (3h)

- [ ] Creare `app/auth.py` per validare header `X-Trigger-Token`.
- [ ] Creare `app/services/mailer_brevo_smtp.py` (plain text, STARTTLS 587).
- [ ] Creare `app/actions_api.py` con endpoint protetti.
- [ ] Implementare wrapper run lifecycle (inizio run, try/except, finish run).

Exit criteria:
- [ ] Endpoint action senza token -> 401.
- [ ] Con token valido passa al workflow.
- [ ] In caso errore action, `runs.status = fail` + `error` valorizzato.

## 5) Weekly report deterministic (3h)

- [ ] Implementare `app/actions/weekly_report.py`:
  - [ ] lettura mood ultimi 7 giorni in timezone `Europe/Zurich`
  - [ ] metriche: `count`, `avg`, `min`, `max`, trend (ultimi 3 vs primi 3)
  - [ ] render testo da `app/templates/weekly_report_deterministic.txt`
- [ ] Invio email + log `messages`.
- [ ] Endpoint `POST /actions/weekly-report` completo.

Exit criteria:
- [ ] Trigger manuale invia email reale.
- [ ] `runs` e `messages` contengono record coerenti con `run_id`.

## 6) Deploy e scheduler (2h)

- [ ] Deploy su Render con ENV configurate.
- [ ] Configurare cron-job.org (POST domenica 07:00 Europe/Zurich).
- [ ] Eseguire uno smoke run manuale post-deploy.

Exit criteria:
- [ ] Endpoint pubblico risponde su `/health`.
- [ ] Action remota completa con email ricevuta.

## 7) Hardening minimo non bloccante (1h)

- [ ] Retry SMTP/Supabase con `tenacity` nei punti I/O.
- [ ] Logging strutturato con `run_id`.
- [ ] README operativo essenziale (setup + deploy + cron).

Exit criteria:
- [ ] README permette setup senza conoscenza implicita.

## Scope post-MVP (non fare ora)

- [ ] `POST /actions/daily-missing-check`
- [ ] OpenAI per sezione "segnale + micro-azione"
- [ ] Ingestione `data_snapshots`
- [ ] Test suite estesa e CI

## Backlog Architettura Multi-User (priorita alta)

- [ ] Isolamento dati per utente (owner esplicito in `things`, `runs`, `messages`).
- [ ] Tutte le query di lettura/scrittura filtrate per owner, niente accesso cross-user.
- [x] Tracker configurabili per utente:
  - [ ] opzione A: template globale + override utente
  - [x] opzione B: configurazione interamente user-specific
- [ ] Regole intelligenti user-centric:
  - [ ] baseline personale
  - [ ] obiettivi/soglie personali
  - [ ] interpretazione trend sulla storia del singolo utente
- [ ] Scheduler: un solo cron globale con dispatcher per utenti attivi (no cron per utente).
- [ ] Dispatcher con regole per utente (timezone, opt-in, frequenza, policy invio).
- [ ] Reporting e alert generati separatamente per ogni utente.
- [ ] Migrazione dati:
  - [ ] strategia per record legacy senza owner
  - [ ] piano di backfill owner dove possibile

## Piano esecuzione rapido (oggi)

- [ ] Blocco 1 completato
- [ ] Blocco 2 completato
- [ ] Blocco 3 completato
- [ ] Blocco 4 completato
- [ ] Blocco 5 completato
- [ ] Blocco 6 completato

Quando questi 6 blocchi sono chiusi, l'MVP e' consegnabile.

## Stato esecuzione (2026-03-01)

- [x] Blocco 1 implementato in codice
- [ ] Blocco 2 completato end-to-end (schema su Supabase da applicare con credenziali)
- [x] Blocco 3 implementato in codice
- [x] Blocco 4 implementato in codice
- [x] Blocco 5 implementato in codice
- [ ] Blocco 6 (deploy Render + cron-job.org) da eseguire con accessi
- [x] Blocco 7 implementato (retry + README)
