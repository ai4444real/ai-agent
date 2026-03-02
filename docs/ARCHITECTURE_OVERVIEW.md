# Architecture Overview

```txt
                                   ┌──────────────────────────────┐
                                   │          Browser UI          │
                                   │ index / summary / my-rules   │
                                   └──────────────┬───────────────┘
                                                  │ HTTPS
                                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                               FastAPI Backend                                       │
│                                                                                      │
│  Auth                                                                                │
│  - /auth/google/verify  -> valida Google token                                      │
│  - owner_sub / owner_email da token                                                  │
│                                                                                      │
│  Data entry                                                                          │
│  - POST /things/choice-quick                                                         │
│  - POST /things/text-quick                                                           │
│  - DELETE /things-mine/{id}                                                          │
│                                                                                      │
│  User config                                                                         │
│  - GET/PUT /config/report-rules-mine                                                 │
│  - GET/PUT /config/tracker-config-mine                                               │
│                                                                                      │
│  Reporting                                                                           │
│  - POST /actions/weekly-report-mine          (flow classico)                         │
│  - POST /actions/weekly-report-smart-mine    (AI + tool-calling)                     │
│  - POST /actions/weekly-report-dispatch      (cron globale multiutente)              │
└───────────────────────────────┬───────────────────────────────┬──────────────────────┘
                                │                               │
                                │ SQL via Supabase client       │ SMTP
                                ▼                               ▼
                     ┌──────────────────────┐        ┌──────────────────────┐
                     │   Supabase (DB)      │        │   Brevo SMTP         │
                     │                      │        │                      │
                     │ things               │        │ invio email report   │
                     │ runs                 │        └──────────────────────┘
                     │ messages             │
                     │ user_report_rules    │
                     │ user_tracker_configs │
                     │ users                │
                     └──────────┬───────────┘
                                │
                                │ dati owner-scoped
                                │
                                ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ OpenAI (solo nel flow SMART)                              │
                     │                                                            │
                     │ Prompt base: weekly_report_smart_system.md                │
                     │ Prompt utente: weekly_report_smart_user.md + rules utente │
                     │                                                            │
                     │ Tools dichiarati dal backend:                             │
                     │ - get_window_coverage(days)                               │
                     │ - get_daily_counts(days, type)                            │
                     │                                                            │
                     │ LLM decide se/quando chiamarli                            │
                     └───────────────┬────────────────────────────────────────────┘
                                     │ function_call
                                     ▼
                     ┌────────────────────────────────────────────────────────────┐
                     │ Tool executor backend (in actions_api)                    │
                     │ - esegue query su Supabase                                │
                     │ - ritorna JSON al modello                                 │
                     └────────────────────────────────────────────────────────────┘
```

## Run Modes

- Classico: backend aggrega + prompt semplice -> report
- Smart: LLM sceglie tool -> backend risponde -> LLM scrive report finale

## Safety / Isolation

- Tutto owner-scoped via `owner_sub`
- Cron attuale resta su dispatch classico
- Smart e' una feature aggiuntiva, non sostitutiva
