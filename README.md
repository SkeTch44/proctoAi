# ProctoAI

AI-powered online exam proctoring platform with cheat detection, AI question generation, live interviews, and a coding room with auto-grading + AI rubric review.

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Flask + Flask-SocketIO (gevent), Alembic |
| Database | PostgreSQL 18 (SQLite supported for dev) |
| Cache / Broker | Redis (via Docker) |
| Worker | Celery (proctoring frame analysis, async jobs) |
| Frontend | React (CRA), Tailwind, Monaco Editor |
| AI | MiniMax (primary), Ollama (fallback), DeepFace, sentence-transformers |

---

## Prerequisites

Install these once:

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend + Celery worker |
| Node.js | 18+ | Frontend dev server |
| PostgreSQL | 14+ (18 tested) | Application database |
| Docker Desktop | latest | Runs Redis container |
| Git | any | Cloning |

Optional for the coding sandbox to support more languages:
- `gcc`, `g++` for C / C++
- `node` (already installed for frontend) for JavaScript
- JDK (`javac` + `java`) for Java

---

## First-Time Setup

### 1. Clone and install dependencies

```powershell
git clone <repo-url> proctoAi
cd proctoAi

# Backend deps
pip install -r backend/requirements-backend.txt

# Frontend deps
cd frontend
npm install
cd ..
```

### 2. PostgreSQL — create the database

Open pgAdmin or psql and run:

```sql
CREATE DATABASE "ProctoAi";
```

### 3. Configure environment

Copy the example file and edit it:

```powershell
copy .env.example .env
```

Open `.env` and set at minimum:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/ProctoAi
JWT_SECRET_KEY=<random-64-char-hex>
SECRET_KEY=<random-64-char-hex>

# AI (optional but recommended)
MINIMAX_API_KEY=<your-key>
MINIMAX_MODEL=minimax-m2.5-free

# CORS
CORS_ORIGINS=http://localhost:3000

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

> If your PostgreSQL password contains `@`, URL-encode it as `%40`. Example: `Rohan@123` → `Rohan%40123`.

### 4. Apply database migrations

```powershell
$env:PYTHONPATH="$PWD"
$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/ProctoAi"
alembic -c backend/alembic.ini upgrade head
```

### 5. (Optional) Migrate data from SQLite

If upgrading from a SQLite-based install:

```powershell
python scripts/migrate_sqlite_to_pg.py `
  --sqlite backend/exam_platform.db `
  --postgres "postgresql://postgres:YOUR_PASSWORD@localhost:5432/ProctoAi"
```

### 6. (Optional) Seed sample coding problems

```powershell
python scripts/seed_coding_problems.py
```

This adds Two Sum, Reverse a String, and FizzBuzz with sample + hidden test cases.

---

## Running the Full Stack

You need **four** processes running at once. Open four terminals.

### Terminal 1 — Redis (via Docker)

Start Docker Desktop first, then:

```powershell
# First time only:
docker run -d --name proctoai-redis -p 6379:6379 redis:7-alpine

# Subsequent runs:
docker start proctoai-redis
```

Verify: `docker ps` should show `proctoai-redis ... Up`.

### Terminal 2 — Backend (Flask + SocketIO)

```powershell
python run.py
```

Wait ~25-35s for TensorFlow / sentence-transformers / DeepFace to load.

You should see:
```
Server initialized for gevent.
QuestionBankManager initialized (driver=postgres)
Starting server with GEVENT async mode...
```

Backend will be on http://localhost:5000.

### Terminal 3 — Celery worker

```powershell
celery -A backend.tasks worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on Windows. Wait for `celery@<host> ready.`

### Terminal 4 — Frontend (React)

```powershell
cd frontend
npm start
```

Browser opens to http://localhost:3000 automatically.

---

## Quick Health Check

```powershell
# Should return 401 (auth required) — confirms server is up:
curl http://localhost:5000/api/v1/coding/problems
```

| Service | Port | Check |
|---------|------|-------|
| Frontend | 3000 | http://localhost:3000 |
| Backend | 5000 | http://localhost:5000/apidocs/ |
| API docs (Swagger) | 5000 | http://localhost:5000/apidocs/ |
| Redis | 6379 | `docker ps` |
| PostgreSQL | 5432 | `psql -U postgres -d ProctoAi -c "\dt"` |

---

## Default Test Accounts

After running migrations, register accounts via the UI or insert directly:

| Role | Username | Password | How |
|------|----------|----------|-----|
| Admin | (your choice) | (your choice) | Register at http://localhost:3000 then promote in DB |

To promote a user to admin:
```sql
UPDATE users SET role='admin' WHERE username='your_username';
```

---

## Feature Tour

| Feature | Access |
|---------|--------|
| Create exam | Admin → "Test creation" |
| Generate questions with AI | Admin → "AI Question Generator" |
| Manage coding problems | Admin → "Coding Problems" |
| Review coding submissions | Admin → "Coding Submissions" |
| Live monitoring of exams | Admin → "Live monitoring" |
| Take an exam | Student → "Start Exam" |
| Solve coding problems | Student → "Coding Problems" |

---

## Common Issues

**Backend startup is slow (~30s)**
Normal — TensorFlow + sentence-transformers + DeepFace are imported eagerly. Subsequent requests are fast.

**`OSError: [WinError 10048] Only one usage of each socket address`**
A previous Python process is still bound to port 5000. Kill it:
```powershell
$pid = (Get-NetTCPConnection -LocalPort 5000 -State Listen).OwningProcess
Stop-Process -Id $pid -Force
```

**`Could not connect to Redis broker`**
Docker isn't running, or Redis container is stopped. Start it:
```powershell
docker start proctoai-redis
```

**`password authentication failed for user "postgres"`**
Wrong password in `DATABASE_URL`. If your password has special characters, URL-encode them (`@` → `%40`, `#` → `%23`, etc.).

**`Module not found: '@monaco-editor/react'`**
Run `npm install @monaco-editor/react` inside `frontend/`.

**Migration: `column "is_active" is of type boolean but default expression is of type integer`**
You're hitting an old migration version. Pull latest, then re-run `alembic upgrade head`.

**AI rubric shows `"ai_available": false`**
MiniMax/Ollama unreachable. Check `MINIMAX_API_KEY` in `.env` or start Ollama (`ollama serve`).

---

## Project Layout

```
proctoAi/
├── run.py                    # Main entry point (starts backend on :5000)
├── backend/
│   ├── app.py                # Flask app, SocketIO, all main routes
│   ├── celery_app.py         # Celery factory
│   ├── tasks.py              # Background tasks (proctoring frame analysis)
│   ├── config.py             # Settings (reads .env)
│   ├── coding/               # Coding-room blueprint (problems, run, submit, AI rubric)
│   ├── db/                   # DB engine + DatabaseManager
│   ├── migrations/           # Alembic migrations
│   ├── models/               # ML models (cheat detector, etc.)
│   ├── providers/            # Lazy-loaded providers (LLM, RAG, models)
│   ├── question_bank.py      # Question bank manager
│   └── services/             # Business services (question gen, proctoring, etc.)
├── frontend/                 # React app
│   └── src/pages/{StudentPages,AdminPages}/
├── scripts/
│   ├── migrate_sqlite_to_pg.py
│   └── seed_coding_problems.py
└── services/                 # Future microservices (coding-svc, exam-svc, etc.)
```

---

## Stopping Everything

```powershell
# Stop frontend / backend / celery: Ctrl+C in each terminal

# Stop Redis container:
docker stop proctoai-redis
```

---

## Troubleshooting Reset

If the database gets into a bad state:

```powershell
# Drop and recreate (destroys data!)
psql -U postgres -c 'DROP DATABASE "ProctoAi"'
psql -U postgres -c 'CREATE DATABASE "ProctoAi"'

# Re-apply schema
$env:PYTHONPATH="$PWD"
$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/ProctoAi"
alembic -c backend/alembic.ini upgrade head
python scripts/seed_coding_problems.py
```
