# IntelliStore / ShopIntel – Architecture

## Overview

IntelliStore is a full-stack Business Intelligence and sales-forecasting
platform for retail businesses.  It is structured as a **monorepo with three
separate services** that communicate over HTTP and share a PostgreSQL database.

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker network                        │
│                                                              │
│  ┌──────────┐   upload    ┌─────────┐   /etl/run   ┌──────┐│
│  │Frontend  │────────────▶│  API    │─────────────▶│ ETL  ││
│  │(React)   │◀────────────│(FastAPI)│             │(Py)  ││
│  └──────────┘   JWT/data  └────┬────┘             └──┬───┘│
│                                │                      │    │
│                                └──────────┬───────────┘    │
│                                           ▼                │
│                                    ┌────────────┐          │
│                                    │ PostgreSQL  │          │
│                                    │  warehouse  │          │
│                                    └────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Services

### `services/api` – FastAPI Backend

| Path | Method | Description |
|------|--------|-------------|
| `/health` | GET | Liveness probe |
| `/auth/google` | POST | Verify Google ID token → issue app JWT |
| `/uploads/` | POST | Accept CSV/Excel → save → trigger ETL |
| `/uploads/{job_id}` | GET | Poll ETL job status |
| `/forecast/run` | POST | Run sales forecast with loaded .pkl model |

### `services/etl` – ETL Worker

| Path | Method | Description |
|------|--------|-------------|
| `/health` | GET | Liveness probe |
| `/etl/run` | POST | Execute pipeline for a given `job_id` |

### `frontend` – React / Vite SPA

- Google Sign-In button (Google Identity Services SDK)
- File upload form (CSV / Excel)
- Sales dashboard with Recharts line chart (mock data; TODO real API)

### `warehouse/schema` – SQL migrations

Run in order:

1. `001_init.sql` – `users`, `etl_jobs`, `staging_sales_raw`
2. `002_dim_fact.sql` – `dim_date`, `dim_product`, `dim_store`, `fact_sales`

---

## Authentication flow (Google OAuth)

```
Frontend                     API                       Google
   │                          │                           │
   │──── click Sign In ───────▶                           │
   │                          │──── OAuth consent ───────▶│
   │◀─── Google ID token ─────│◀──── id_token ────────────│
   │                          │                           │
   │──── POST /auth/google ──▶│                           │
   │      { id_token }        │── verify_oauth2_token() ──▶│
   │                          │◀── id_info (sub/email) ───│
   │                          │                           │
   │                          │── upsert user in DB ──────▶│
   │◀── { access_token } ─────│                           │
   │  (app JWT, HS256)        │                           │
```

**Security notes:**
- The ID token is verified server-side using `google-auth` library.
- The app issues its own short-lived JWT (HS256) signed with `JWT_SECRET`.
- `JWT_SECRET` must be set via environment variable – never hard-coded.

---

## Upload → ETL flow (Option A)

```
User                  API                       ETL               DB
 │                     │                         │                 │
 │── POST /uploads/ ──▶│                         │                 │
 │  (multipart form)   │                         │                 │
 │                     │── save file to volume ──▶                 │
 │                     │── INSERT etl_jobs ───────────────────────▶│
 │                     │── POST /etl/run ────────▶│               │
 │◀── 202 { job_id } ──│                         │               │
 │                     │                         │── read file ───▶│
 │                     │                         │── clean data    │
 │                     │                         │── INSERT staging│
 │                     │                         │── UPDATE status │
 │── GET /uploads/{id}─▶                         │               │
 │◀── { status: "completed" } ─────────────────────────────────── │
```

**Production TODOs:**
- Replace synchronous HTTP trigger with async queue (Celery / RQ / SQS).
- Store uploaded files in S3 / GCS instead of local volume.
- Add retry logic and dead-letter queue.

---

## Forecast model integration (Google Colab → .pkl)

### 1. Train in Colab

```python
# Train your model (Prophet, sklearn Pipeline, etc.)
model.fit(train_df)

# Export
import pickle
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)
```

### 2. Place in repo

```
services/api/models/forecast/model.pkl   ← not committed to git
```

See `services/api/models/forecast/README.md` for full instructions.

### 3. API loads it lazily

`services/api/src/forecast.py` loads the model on first call and caches it.
`POST /forecast/run` accepts `{ store_id, product_id, horizon_days }` and
returns a list of `{ ds, yhat }` predictions.

If no model file is present, mock predictions are returned so development can
proceed without a trained model.

**Production TODOs:**
- Version-stamp models with `metadata.json` (training date, features, RMSE).
- Store models in S3 and pull on startup (avoid baking large binaries into the
  Docker image).
- Add input validation against a feature schema.

---

## Local development with docker-compose

```bash
cd ops
cp .env.example .env
# Edit .env: set GOOGLE_CLIENT_ID, JWT_SECRET, POSTGRES_PASSWORD

docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:80 |
| API docs | http://localhost:8000/docs |
| ETL docs | http://localhost:8001/docs |
| Postgres | localhost:5432 |
