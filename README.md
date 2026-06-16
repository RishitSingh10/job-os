# Job OS

A **local-first, single-user AI Job OS** — discover jobs, score and tailor resumes
with local LLMs, generate cover letters, track applications through a Kanban
pipeline, and (with explicit human approval) automate browser-based submissions.

Everything runs on your own machine. No cloud, no Kubernetes, no managed services,
no microservices — a single modular-monolith application backed by SQLite, ChromaDB,
and [Ollama](https://ollama.com).

> **Status:** Phase 1 complete — project structure + runnable backend skeleton.
> Built incrementally across 12 phases (see [Roadmap](#roadmap)).

---

## Architecture

A **modular monolith**: one FastAPI process composed of clean, decoupled modules.

```text
job-os/
├── backend/            FastAPI app (HTTP layer, app factory, routers)
│   ├── main.py         create_app() factory + ASGI entrypoint
│   └── api/            routers (system/health now; features per phase)
├── core/               cross-cutting domain + infrastructure
│   ├── config.py       strongly-typed settings (pydantic-settings)
│   ├── logging.py      structlog → console + JSONL audit trail
│   ├── paths.py        storage path management
│   ├── database/       SQLModel engine + models           (Phase 2)
│   ├── embeddings/     ChromaDB vector store               (Phase 5)
│   ├── llm/            Ollama client + prompts             (Phase 6)
│   ├── documents/      PDF/DOCX parse + render             (Phase 6/7)
│   ├── jobs/           discovery / dedup / indexing        (Phase 5)
│   ├── applications/   lifecycle + approval                (Phase 8)
│   └── automation/     browser orchestration               (Phase 9)
├── agents/             specialised in-process AI agents
│   ├── discovery/  ats/  tailoring/  cover_letter/
│   └── browser/    tracking/  analytics/
├── frontend/           Next.js 15 + Tailwind + shadcn/ui    (Phase 4)
├── storage/            local artifacts (resumes, exports, logs, traces, chroma)
├── scripts/            dev/test helper scripts
└── tests/              pytest suite
```

### Tech stack

| Layer        | Choice                                                        |
| ------------ | ------------------------------------------------------------- |
| Frontend     | Next.js 15, TypeScript, TailwindCSS, shadcn/ui, React Query, Zustand, Recharts |
| Backend      | FastAPI, Python 3.12, SQLModel, asyncio                       |
| Database     | SQLite (`jobos.db`) via async `aiosqlite`                     |
| Vector store | ChromaDB (embedded, persistent)                               |
| LLMs         | Ollama — `qwen3`, `qwen2.5-coder`, `llama3.3`, `mistral-small`|
| Embeddings   | `nomic-embed-text`                                            |
| Browser      | browser-use + Playwright                                      |
| Background   | asyncio + FastAPI BackgroundTasks + APScheduler               |
| Tooling      | uv (Python), npm (frontend), pytest / Vitest / Playwright     |

---

## Prerequisites

- **Python 3.12** and [**uv**](https://docs.astral.sh/uv/) — backend.
- **Ollama** running locally (`ollama serve`) with the models pulled — AI features.
- **Node.js 20+** and **npm** — frontend (needed from Phase 4 onward).

Pull the local models once:

```powershell
ollama pull qwen3
ollama pull qwen2.5-coder
ollama pull mistral-small
ollama pull nomic-embed-text
```

---

## Quickstart (backend)

```powershell
# 1. Install dependencies into a local virtualenv
uv sync

# 2. (optional) create your own config
Copy-Item .env.example .env

# 3. Run the API with autoreload
./scripts/dev.ps1
#   → http://127.0.0.1:8000
#   → http://127.0.0.1:8000/docs       (interactive API docs)
#   → http://127.0.0.1:8000/api/health (liveness)
#   → http://127.0.0.1:8000/api/ready  (readiness; probes Ollama)
```

### Run the tests

```powershell
./scripts/test.ps1            # plain
./scripts/test.ps1 -Cov       # with coverage
# or directly:
uv run pytest
```

---

## API

REST endpoints are mounted under `/api` (interactive docs at `/docs`). Layering:
**routers** (HTTP) → **services** (`core/<domain>/service.py`, business logic) →
generic **`CRUDService`** base → DB. The core layer never imports `backend`; domain
errors (`core/exceptions.py`) are mapped to HTTP in `backend/api/errors.py`.

| Resource       | Endpoints |
| -------------- | --------- |
| System         | `GET /api/health`, `GET /api/ready` |
| Jobs           | `POST/GET /api/jobs`, `GET/PATCH/DELETE /api/jobs/{id}` (filter: source, company, easy_apply, search; dedup on create) |
| Resumes        | `POST/GET /api/resumes`, `GET/PATCH/DELETE /api/resumes/{id}` |
| Applications   | `POST/GET /api/applications`, `GET/PATCH/DELETE /api/applications/{id}`, `PUT /api/applications/{id}/status`, `GET /api/applications/counts` |

List endpoints return a paginated envelope `{ items, total, offset, limit }`
(`offset`/`limit` query params, `limit` capped at 200).

## Job discovery

The **Discovery Agent** ([agents/discovery/](agents/discovery)) fetches postings
from a source adapter, deduplicates them, and indexes new ones:

1. **Fetch** — `JobSourceAdapter` implementations normalise each source into a
   `JobPosting`. Available now: **Exa** (semantic web search, needs
   `JOBOS_EXA_API_KEY`) and **manual** (client-supplied import). LinkedIn/Indeed/
   Glassdoor live scraping is wired in Phase 9 (browser automation).
2. **Dedup** — cheapest signal first: exact fingerprint (`dedup_hash`) →
   embedding cosine similarity → fuzzy title match within the same company.
3. **Index** — new jobs are embedded (`nomic-embed-text` via Ollama) and stored in
   **ChromaDB** for semantic dedup/search.

Embeddings are **best-effort**: if Ollama is down or the `embeddings` extra isn't
installed, discovery still runs with fingerprint + fuzzy dedup. Enable the vector
store with `uv sync --extra embeddings`.

```http
POST /api/discovery/run
{ "source": "manual", "postings": [ { "title": "...", "company": "...", "url": "..." } ] }
{ "source": "exa", "query": "remote AI engineer roles at GenAI startups", "limit": 25 }
```

## Frontend

A **Next.js 16** app (App Router, React 19, TypeScript, Tailwind v4, shadcn/ui on
Base UI) in [`frontend/`](frontend). State/data via **React Query** + **Zustand**;
charts via **Recharts**; dark mode via **next-themes**.

```powershell
cd frontend
npm install          # first time
npm run dev          # http://localhost:3000  (backend must run on :8000)
npm run build        # production build
npm run lint         # eslint
```

The browser talks to the backend at `NEXT_PUBLIC_API_BASE_URL` (default
`http://127.0.0.1:8000/api`; see `frontend/.env.example`). Layout: a sidebar shell
with Dashboard (stat cards + pipeline chart), **Jobs** (search/filter, add, track,
delete), **Applications** (inline status transitions, filter), and **Resumes**
(library + add). A typed API client lives in `src/lib/api.ts`; React Query hooks in
`src/hooks/`.

> Run the backend first (`./scripts/dev.ps1`) so the UI has data to show.

## Database & migrations

The data layer uses **SQLModel** over **async SQLite** (`aiosqlite`). A single
`Database` instance (engine + session factory) is created per app instance and
stored on `app.state.db`; request handlers get a transactional session via the
`get_session` dependency.

Domain models live in [core/database/models.py](core/database/models.py):
`Resume`, `Job`, `ATSScore`, `TailoredResume`, `CoverLetter`, `Application`,
`ApprovalWorkflow`, `AutomationRun`, `LLMUsage`. On startup the app creates any
missing tables; **Alembic** provides versioned migrations:

```powershell
uv run alembic upgrade head                      # apply migrations
uv run alembic revision --autogenerate -m "..."  # generate a migration from model changes
uv run alembic check                             # fail if models drift from migrations
uv run alembic downgrade -1                       # roll back one revision
```

## Configuration

All settings are environment-driven with safe defaults (see `.env.example`).
Variables use the `JOBOS_` prefix and are validated into a typed `Settings` object
(`core/config.py`). An empty or absent `.env` works out of the box.

## Logging & audit trail

Structured logs (`structlog`) are written to:

- the **console** (pretty in dev, JSON if `JOBOS_LOG_JSON=true`), and
- **`storage/logs/jobos.jsonl`** — a rotating JSON Lines audit trail (local only,
  no external monitoring).

---

## Roadmap

| Phase | Scope                       | Status |
| ----- | --------------------------- | ------ |
| 1     | Project structure           | ✅ done |
| 2     | Database models             | ✅ done |
| 3     | API layer                   | ✅ done |
| 4     | Frontend                    | ✅ done |
| 5     | Job discovery               | ✅ done |
| 6     | ATS engine                  | ⏳      |
| 7     | Resume tailoring            | ⏳      |
| 8     | Application tracker         | ⏳      |
| 9     | Browser automation          | ⏳      |
| 10    | Analytics                   | ⏳      |
| 11    | Testing                     | ⏳      |
| 12    | Dockerization               | ⏳      |

---

## Principles

Single-user · local-first · strongly typed · modular · SOLID · incremental ·
production-quality (no placeholders). **The browser agent never submits an
application without explicit human approval.**
