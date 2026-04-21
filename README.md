# Couply API

FastAPI backend for Couply — a shared finance app for couples. Tracks shared and personal expenses, calculates real-time balance between partners, and supports flexible split modes (equal, custom, or proportional to income).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| HTTP Framework | FastAPI 0.115.0 |
| ASGI Server | Uvicorn 0.30.6 |
| ORM | SQLAlchemy 2.0 async |
| DB Driver | asyncpg 0.30.0 |
| Database | PostgreSQL 15+ |
| Migrations | Alembic 1.13.3 |
| Validation | Pydantic v2 (2.9.2) |
| Auth | Firebase Admin SDK 6.5.0 (JWT verification) |
| Config | pydantic-settings + python-dotenv |
| Deployment | Docker → GCP Cloud Run |
| Testing | pytest 8.3.3 + pytest-asyncio + httpx |

---

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- A Firebase project with a service account JSON key
- Docker (optional, for containerized local development)

---

## Local Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/your-org/couply.git
cd couply/couply-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables) below).

### 4. Create the database

```bash
createdb couply  # or use psql / pgAdmin
```

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Async PostgreSQL DSN: `postgresql+asyncpg://user:pass@host:5432/couply` |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID (e.g. `my-app-12345`) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Yes | Full service account JSON as a single-line string |
| `ENVIRONMENT` | No (default: `dev`) | `dev` enables SQL echo and the `/dev/*` router |

> In production, secrets are stored in **GCP Secret Manager** and injected at deploy time.

---

## Running Tests

```bash
pytest
```

Tests use mocked `AsyncSession` (no real DB required). Coverage includes all services and Pydantic schemas.

```bash
pytest -v                  # verbose output
pytest tests/test_balance_service.py  # single file
```

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Create a new migration after changing models
alembic revision --autogenerate -m "describe your change"

# Show current migration status
alembic current
```

Migration history:
1. `21b26210721d` — initial schema (users, couples, expenses)
2. `739a75aa8416` — add `visible_to` JSON column to expenses
3. `37f969dd0def` — rename `date` → `expense_date`
4. `a1b2c3d4e5f6` — rename `sueldo` → `salary`

---

## API Endpoints

All protected endpoints require `Authorization: Bearer <firebase_id_token>`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check → `{"status": "ok"}` |
| POST | `/auth/register` | Bearer | Register user from Firebase token (idempotent — 409 if already exists) |
| GET | `/auth/me` | Bearer | Current user profile |
| PATCH | `/auth/me` | Bearer | Update profile (`name`, `salary`) — salary is never returned in any response |
| POST | `/couple` | Bearer | Create couple (generates `invite_code`) |
| POST | `/couple/join` | Bearer | Join existing couple via `invite_code` |
| GET | `/couple` | Bearer | Get current user's couple data |
| PUT | `/couple/split` | Bearer | Update split mode and/or custom percentages |
| POST | `/expenses` | Bearer | Create expense |
| GET | `/expenses` | Bearer | List expenses — filters: `?type=shared\|personal`, `?month=YYYY-MM` |
| PUT | `/expenses/{id}` | Bearer | Update expense (creator only — 403 otherwise) |
| DELETE | `/expenses/{id}` | Bearer | Delete expense (creator only — 403 otherwise) |
| GET | `/balance` | Bearer | Calculate current balance between partners |
| GET | `/dev/custom-token` | No | **Dev only** — get a Firebase custom token by UID |

---

## Project Structure

```
couply-api/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic Settings — reads env vars
│   │   ├── firebase.py          # Firebase Admin SDK init + token verification
│   │   └── dependencies.py      # FastAPI deps: get_current_user, get_db
│   ├── database/
│   │   └── session.py           # Async engine, session factory, get_db
│   ├── models/
│   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   ├── user.py              # User ORM model
│   │   ├── couple.py            # Couple ORM model + SplitMode enum
│   │   └── expense.py           # Expense ORM model + ExpenseType enum
│   ├── schemas/
│   │   ├── user.py              # UserCreate, UserUpdate, UserResponse
│   │   ├── couple.py            # JoinCoupleRequest, UpdateSplitRequest, CoupleResponse
│   │   └── expense.py           # ExpenseCreate, ExpenseUpdate, ExpenseResponse
│   ├── routers/
│   │   ├── auth.py              # POST /auth/register, GET /auth/me, PATCH /auth/me
│   │   ├── couple.py            # Couple CRUD + invite code
│   │   ├── expenses.py          # Expenses CRUD
│   │   ├── balance.py           # GET /balance
│   │   └── dev.py               # GET /dev/custom-token (dev only)
│   └── services/
│       ├── auth_service.py      # create_user, get_user_by_firebase_uid, update_user
│       ├── couple_service.py    # create_couple, join_couple, update_split
│       ├── expense_service.py   # CRUD + visibility filtering
│       └── balance_service.py   # calculate_balance + split percentage resolution
├── alembic/
│   ├── env.py                   # Async Alembic config
│   └── versions/                # Migration files
├── tests/
│   ├── conftest.py              # Fixtures: mock_db, user1, user2, couple, expenses
│   ├── test_auth_service.py
│   ├── test_balance_service.py
│   ├── test_couple_service.py
│   ├── test_expense_service.py
│   └── test_schemas.py
├── Dockerfile
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Business Rules

### Authentication
1. Client signs in via Firebase SDK and obtains a Firebase ID token.
2. Client sends `Authorization: Bearer <id_token>` on every protected request.
3. `HTTPBearer` extracts the token; `verify_firebase_token()` validates it with Firebase Admin SDK.
4. Firebase UID is used to look up the `User` row in the DB.
5. `POST /auth/register` creates the user row; returns 409 if already registered (client should call `GET /auth/me` on 409).

### Couple lifecycle
- A user can belong to only one couple at a time.
- Creator becomes `user1`; `user2_id` is null until a partner joins.
- A couple is "complete" only when `user2_id` is set — expenses and balance require a complete couple.
- A user cannot join their own couple; a complete couple cannot be joined again.

### Split modes
- **`equal`** — always 50/50.
- **`custom`** — `percentage_user1 + percentage_user2` must equal 100 (0.01 tolerance). Set via `PUT /couple/split`.
- **`auto`** — computed proportionally from each user's `salary` at balance-calculation time. Requires both salaries to be set; raises HTTP 422 otherwise.

### Per-expense split override
- `split_override_user1` and `split_override_user2` can override the couple's global split for a single expense.
- Both fields must be set together and must sum to 100.
- Used by the "Settle up" feature in the mobile app (0/100 split to fully cancel a debt).

### Expense visibility
- `shared` expenses: `visible_to = [user1_id, user2_id]` — both partners see them.
- `personal` expenses: `visible_to = [created_by]` — only the creator sees them.
- `GET /expenses` filters by `str(current_user.id) in expense.visible_to`.

### Balance calculation
- Computed at query time from all shared expenses — never stored.
- For each expense: the payer gets credited their partner's share.
- Result: `{ balance, debtor, creditor }` — balance < 0.01 is treated as settled (debtor/creditor = null).
- Personal expenses are fully excluded.
- `salary` is never included in any API response.

---

## Deployment (GCP Cloud Run)

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

No CI/CD pipeline exists yet — deployment is manual.
