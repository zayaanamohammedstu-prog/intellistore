# IntelliStore / ShopIntel

A full-stack Business Intelligence and sales-forecasting platform for retail businesses.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2

### 1. Clone and configure

```bash
git clone https://github.com/zayaanamohammedstu-prog/intellistore.git
cd intellistore/ops
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `JWT_SECRET` | Random secret for signing app JWTs (`openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | Database password |

### 2. Start all services

```bash
cd ops
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | <http://localhost:80> |
| API (Swagger docs) | <http://localhost:8000/docs> |
| ETL (Swagger docs) | <http://localhost:8001/docs> |
| PostgreSQL | `localhost:5432` |

### 3. (Optional) Add your trained model

Place your exported `.pkl` model at `services/api/models/forecast/model.pkl`.
See [services/api/models/forecast/README.md](services/api/models/forecast/README.md)
for export instructions.

---

## Repository structure

```
intellistore/
├── services/
│   ├── api/          # FastAPI backend (auth, uploads, forecasting)
│   └── etl/          # ETL worker (Pandas cleaning → Postgres load)
├── frontend/         # React/Vite SPA (dashboard + Google Sign-In)
├── warehouse/
│   └── schema/       # PostgreSQL DDL (applied automatically by docker-compose)
├── ops/
│   ├── docker-compose.yml
│   └── .env.example
└── docs/
    └── architecture.md
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for a detailed description of:

- Service boundaries and communication
- Google OAuth login flow
- Upload → ETL pipeline
- Colab model (.pkl) integration

## Development without Docker

### API

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://... GOOGLE_CLIENT_ID=... JWT_SECRET=...
uvicorn src.main:app --reload
```

### ETL

```bash
cd services/etl
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://...
uvicorn src.main:app --port 8001 --reload
```

### Frontend

```bash
cd frontend
npm install
cp ../ops/.env.example .env.local   # then edit VITE_* variables
npm run dev
```

## Production TODOs

- [ ] Replace local volume uploads with S3 / GCS object storage
- [ ] Replace synchronous ETL trigger with async queue (Celery / RQ / SQS)
- [ ] Add Alembic migrations (replace `create_all` on startup)
- [ ] Store JWT in httpOnly cookie instead of localStorage
- [ ] Add rate limiting and request validation middleware
- [ ] Deploy model artifacts from S3 (avoid large binary blobs in Docker image)
- [ ] Add CI/CD pipeline (GitHub Actions)

