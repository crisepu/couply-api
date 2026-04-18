# Couply API

FastAPI backend for Couply — a finance management app for couples with proportional expense splitting.

## Tech Stack

- **Python 3.12** + **FastAPI**
- **PostgreSQL** via **SQLAlchemy async** (asyncpg)
- **Firebase Auth** — JWT validation with firebase-admin SDK
- **Alembic** — database migrations
- **GCP Cloud Run** — deployment target

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- A Firebase project with a service account

## Local Setup

```bash
# 1. Clone and create virtualenv
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your database URL and Firebase credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start the development server
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | Async PostgreSQL DSN | `postgresql+asyncpg://user:pass@localhost:5432/couply` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `my-firebase-project` |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full service account JSON as a string | `{"type":"service_account",...}` |
| `ENVIRONMENT` | `dev` or `prod` | `dev` |

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| POST | `/auth/register` | Bearer token | Register user (after Firebase sign-in) |
| GET | `/auth/me` | Bearer token | Get current user |
| POST | `/couple` | Bearer token | Create couple, get invite_code |
| POST | `/couple/join` | Bearer token | Join couple via invite_code |
| GET | `/couple` | Bearer token | Get couple data |
| PUT | `/couple/split` | Bearer token | Update split mode and percentages |

## Firebase Auth Flow

1. Client signs in via Firebase SDK and gets an ID token
2. Client sends `Authorization: Bearer <id_token>` header
3. Backend verifies token with Firebase Admin SDK
4. Backend resolves the `User` row linked to that Firebase UID

## Database Migrations

```bash
# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

## Business Rules

- **Split modes**: `equal` (50/50) · `auto` (proportional to each user's `sueldo`) · `custom` (manual percentages)
- **Per-expense override**: each expense can override the couple's global split via `split_override_user1/2`
- **Sueldo privacy**: `sueldo` is never exposed in any API response — only used internally for `auto` split calculation
- **Balance**: calculated at query time from shared expenses (not stored)
- **Personal expenses**: visible only to the creator, excluded from balance

## Deployment (Cloud Run)

```bash
# Build and push image
docker build -t gcr.io/<PROJECT>/couply-api .
docker push gcr.io/<PROJECT>/couply-api

# Deploy
gcloud run deploy couply-api \
  --image gcr.io/<PROJECT>/couply-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars ENVIRONMENT=prod \
  --set-secrets DATABASE_URL=couply-db-url:latest \
  --set-secrets FIREBASE_SERVICE_ACCOUNT_JSON=couply-firebase-sa:latest \
  --set-secrets FIREBASE_PROJECT_ID=couply-firebase-project:latest
```

## Project Structure

```
app/
├── main.py              # FastAPI app + lifespan
├── core/
│   ├── config.py        # Settings from .env
│   ├── firebase.py      # Firebase Admin SDK
│   └── dependencies.py  # get_db, get_current_user
├── database/
│   └── session.py       # Async engine + session
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── routers/             # Route handlers
└── services/            # Business logic
alembic/                 # DB migrations
```
