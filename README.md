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
| 3     | API layer                   | ⏳      |
| 4     | Frontend                    | ⏳      |
| 5     | Job discovery               | ⏳      |
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
