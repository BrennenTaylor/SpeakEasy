# Milestone 1 — Repository Scaffolding and Project Foundation

**Status:** Approved 2026-11-18
**Date:** 2026-11-18
**Scope owner:** Lead architect

## Intent

Milestone 1 exists to make every later milestone cheap to start and hard to get
wrong. It delivers a runnable, testable skeleton:

- a React/TypeScript/Tailwind frontend that renders a mobile-first shell,
- a FastAPI backend with typed request/response boundaries,
- a SQLAlchemy/Alembic/SQLite persistence layer that can migrate from empty,
- one thin vertical slice (browser → HTTP → backend) proving the wiring,
- one command that lints, type-checks, tests, and builds everything.

No meal logging, nutrition lookup, AI, or insights work happens here.

**Success looks like:** a developer clones the repo, runs `make setup` and
`make check`, then `make dev-backend` + `make dev-frontend`, and sees a health
indicator go from loading to OK in a phone-sized browser window. Stopping the
backend and retrying shows a clear error state, not a blank page.

## Goals

1. Predictable two-project layout with no workspace tooling.
2. Reproducible setup on Python 3.12 and Node 24.
3. Backend liveness endpoint with a Pydantic response model.
4. Alembic baseline that upgrades and downgrades cleanly on an empty SQLite file.
5. Frontend API client with runtime response validation and loading/error states.
6. Lint, format, type-check, test, and build commands that fail loudly.
7. README that a new contributor can follow without asking questions.

## Non-goals

- Domain schema (`meals`, `foods`, nutrition snapshots) — Milestone 2.
- Nutrition provider adapters and AI provider abstraction.
- Authentication, accounts, multi-user, or sync.
- Service worker, offline caching, installable PWA assets/icons.
- Deployment, containers, TLS, production CORS, observability.
- Charts, weekly/monthly insights, photo upload.
- State-management or data-fetching libraries (React Router, TanStack Query, Redux).

## Anti-goals

- A schema designed before the meal-logging requirements are understood.
- Abstractions with one caller (provider registries, generic repositories).
- Client-side secrets or AI calls from the browser.
- A "temporary" database bootstrap that silently drifts from Alembic.
- CI that tests a different runtime than local development.

## Constraints

- Stack is fixed by `AGENTS.md`: React + TypeScript + Vite + Tailwind,
  FastAPI + Pydantic, SQLAlchemy + Alembic, SQLite.
- Node 24 via nvm (`.nvmrc`); system Node is 12 — commands must not rely on it.
- Python 3.12 (`/usr/bin/python3.12`); system `python3` is 3.10 — commands must
  name the interpreter.
- Local-first, single-user assumption. No auth in Milestone 1.
- Nutrition arithmetic uses `Decimal` when it arrives; no float money/nutrition
  values are introduced now.
- Do not modify `AGENTS.md` rules; do not reset or delete user data.

## Approaches considered

### A. Two top-level projects + root Makefile (chosen)

`frontend/` and `backend/` each keep their native tooling and lockfiles; a thin
root `Makefile` is the command surface. No workspace protocol, no shared build
graph. Cost: no shared TypeScript/Python types (there are none worth sharing
yet). Benefit: the smallest thing that a React developer and a Python developer
both recognize immediately.

### B. npm workspace monorepo (`apps/web`, `apps/api`)

Buys shared TypeScript packages and one `npm install`. But the backend is
Python, so the workspace only covers half the repo; shared API types would need
codegen (OpenAPI → TS) to have value. That is real complexity with no Milestone 1
consumer. Deferred until a second frontend consumer or generated client exists.

### C. FastAPI serves the built SPA

One process, one origin, simple deployment. But it slows frontend feedback
(every change needs a rebuild), couples release cycles, and makes Vite's dev
server features unavailable. Revisit at the deployment milestone; keep the API
same-origin-friendly so this stays possible.

### D. Docker Compose for local development

Reproducible across machines, but adds image builds, bind mounts, and a second
way to run tests. Not needed for a two-process local app. Deferred to the
deployment milestone.

## Decisions

| Area | Decision | Why |
| --- | --- | --- |
| Layout | `frontend/`, `backend/`, `docs/`, root `Makefile` | Native tooling per ecosystem, no workspace overhead |
| Package manager | npm with committed `package-lock.json` | Ships with Node; one fewer tool to install |
| Python env | `backend/.venv` via `python3.12 -m venv`, deps in `pyproject.toml` | Standard, inspectable, no extra tooling |
| App factory | `create_app() -> FastAPI` in `backend/app/main.py` | Testable without import-time side effects |
| API prefix | All routes under `/api` | Clean dev proxy and future same-origin deploy |
| Dev wiring | Vite proxy `/api` → `http://127.0.0.1:8000` | No CORS configuration in development |
| DB access | Synchronous SQLAlchemy 2.0 + `sessionmaker` | SQLite is local and single-user; async adds no value yet |
| Migrations | Alembic from day one, empty baseline revision | Proves wiring without inventing schema |
| Migrations mode | `render_as_batch=True` | SQLite cannot `ALTER` many columns; batch mode keeps future migrations viable |
| Health contract | `GET /api/health` → `{"status":"ok"}`, Pydantic `Literal["ok"]` | Small, typed, extendable |
| Frontend styling | Tailwind v4 via `@tailwindcss/vite`, CSS-first config | No `tailwind.config.js` to maintain |
| Frontend tests | Vitest + React Testing Library + jsdom | Native Vite integration, fast |
| Backend tests | pytest + `fastapi.testclient` (httpx) | Standard, sync, no server process needed |
| Backend lint/format | Ruff (lint + format), mypy | One fast tool for both; type-check requirement |
| Frontend lint/format | ESLint (Vite template) + Prettier | ESLint for correctness, Prettier for diff stability |
| PWA | Viewport, theme color, minimal web manifest; no service worker | Phone-first layout now, installability later |
| Runtime config | `APP_*` env vars (backend), `VITE_API_BASE_URL` (frontend) | 12-factor, no secrets in the bundle |

## Directory structure

```text
app-calorie/
├── AGENTS.md                  # existing engineering rules (unchanged)
├── Makefile                   # single command surface
├── README.md                  # setup, commands, troubleshooting
├── .editorconfig .gitignore .nvmrc
├── .github/workflows/ci.yml
├── docs/
│   └── superpowers/
│       ├── specs/2026-11-18-milestone-1-foundation-design.md
│       └── plans/2026-11-18-milestone-1-foundation.md
├── backend/
│   ├── pyproject.toml         # deps, pytest, ruff, mypy config
│   ├── .python-version        # 3.12
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py             # settings-driven URL, Base.metadata
│   │   ├── script.py.mako
│   │   └── versions/<rev>_baseline.py
│   ├── app/
│   │   ├── main.py            # create_app()
│   │   ├── api/router.py      # /api router composition
│   │   ├── api/routes/health.py
│   │   ├── core/config.py     # Settings, get_settings()
│   │   ├── core/db.py         # engine, session factory
│   │   └── models/base.py     # Base(DeclarativeBase)
│   ├── data/.gitkeep          # local SQLite lives here (ignored)
│   └── tests/
│       ├── test_config.py
│       ├── test_health.py
│       └── test_db.py
└── frontend/
    ├── package.json package-lock.json
    ├── index.html
    ├── vite.config.ts         # react, tailwind, vitest, /api proxy
    ├── tsconfig*.json
    ├── eslint.config.js
    ├── .prettierrc.json
    ├── .env.example
    ├── public/manifest.webmanifest
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css          # @import "tailwindcss";
        ├── components/HealthCheck.tsx
        ├── api/health.ts
        ├── test/setup.ts
        └── App.test.tsx
```

## Responsibilities

| Concern | Frontend | Backend |
| --- | --- | --- |
| Rendering | Mobile-first shell, states, accessibility | None (no templates) |
| Validation | Parse and shape-check API responses before display | Authoritative Pydantic request/response models |
| Business rules | Presentation only; no calorie math | Future home of deterministic nutrition logic |
| Persistence | Never touches SQL or files | SQLAlchemy sessions, Alembic migrations |
| Secrets | Only `VITE_*` public config | All credentials in `APP_*` env vars, server-side only |
| AI | Never calls providers directly | Future provider adapters, server-side only |
| Errors | User-visible loading/error/retry states | Typed HTTP errors; no stack traces to clients |

The frontend is a client, not a second source of truth. If a number matters
(calories, macros), the backend computes and returns it; the frontend formats it.

## Dependencies

**Backend runtime:** `fastapi`, `uvicorn[standard]`, `pydantic`,
`pydantic-settings`, `sqlalchemy`, `alembic`.
**Backend dev:** `pytest`, `httpx`, `ruff`, `mypy`.

**Frontend runtime:** `react`, `react-dom`.
**Frontend dev:** `vite`, `@vitejs/plugin-react`, `typescript`, `tailwindcss`,
`@tailwindcss/vite`, `vitest`, `jsdom`, `@testing-library/react`,
`@testing-library/jest-dom`, `@testing-library/user-event`, `eslint` (+ Vite
template plugins), `prettier`, `@types/react`, `@types/react-dom`.

No other dependency is added in Milestone 1. Rationale for each addition is
either the mandated stack or a direct test/quality requirement from `AGENTS.md`.
Exact resolved versions are captured in `package-lock.json`; Python uses
compatible-release bounds in `pyproject.toml` (no unpinned `latest`).

## Commands

| Command | Effect |
| --- | --- |
| `make setup` | Create `backend/.venv`, install backend deps, `npm ci` frontend |
| `make dev-backend` | `uvicorn app.main:app --reload --port 8000` |
| `make dev-frontend` | `vite` on port 5173 |
| `make migrate` | `alembic upgrade head` against `APP_DATABASE_URL` |
| `make migration m="..."` | Autogenerate a revision (review before committing) |
| `make test` | `pytest` + `vitest run` |
| `make lint` | `ruff check`, `ruff format --check`, `eslint`, `prettier --check` |
| `make typecheck` | `mypy app` + `tsc --noEmit` |
| `make build` | `vite build` |
| `make check` | lint + typecheck + test + migrations check + build |

`make check` must not require a running server and must not mutate a developer's
database: migration verification uses a disposable file under `backend/data/`
that is removed afterward.

## Test and lint infrastructure

- **Backend tests** run against an in-memory SQLite engine (`sqlite://`), never
  the developer database. `TestClient(create_app())` exercises the ASGI app; no
  port binding, no network.
- **Frontend tests** run in jsdom with `fetch` stubbed per test; no MSW yet
  (one endpoint does not justify it).
- **Lint/format gates** are non-mutating in `make check` (`--check` modes) so CI
  and local runs agree.
- **CI** runs the same `make setup && make check` on Ubuntu with Python 3.12 and
  Node 24. No separate CI-only commands.
- **Migration check** upgrades an empty temp database to head, asserts the
  revision is `base`'s child (baseline), then downgrades to base.

## Acceptance criteria

| # | Criterion | Verification |
| --- | --- | --- |
| 1 | Fresh clone sets up with one command | `make setup` exits 0 on Python 3.12 + Node 24 |
| 2 | All quality gates pass | `make check` exits 0 |
| 3 | Health endpoint is live and typed | `curl -i localhost:8000/api/health` → 200 `{"status":"ok"}`; `/docs` renders |
| 4 | Migrations work from empty | `make migrate` on missing DB creates `alembic_version` at head; rerun is a no-op; downgrade to base succeeds |
| 5 | Frontend renders a mobile shell | App shows heading inside `max-w-md` container; no horizontal scroll at 390 px |
| 6 | Health slice shows all states | Loading, then OK with backend up; clear error + retry with backend down |
| 7 | Proxy works without CORS | Browser requests `/api/health` on :5173 and receives 200 from :8000 |
| 8 | No secrets or artifacts committed | `git status` clean after `make check`; `.env`, `.venv`, `*.db`, `dist` ignored |
| 9 | Backend type/lint clean | `mypy app`, `ruff check`, `ruff format --check` exit 0 |
| 10 | Frontend type/lint clean | `tsc --noEmit`, `eslint .`, `prettier --check .` exit 0 |
| 11 | Docs are sufficient | A new contributor can follow README to run backend, frontend, tests |

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Wrong Python on PATH (3.10) | Setup fails cryptically | `backend/.python-version`, Makefile uses `PYTHON ?= python3.12`, README states it |
| Wrong Node on PATH (12) | Vite/Tailwind fail oddly | README starts with `nvm use`; CI pins Node 24; `engines` field in `package.json` |
| Empty baseline migration confuses contributors | Someone edits history or autogenerates blindly | Comment in revision + README migration section; schema work starts M2 |
| SQLAlchemy + mypy friction | False positives block work | Start mypy on `app/` only; add `sqlalchemy[mypy]` plugin when models arrive |
| Dev proxy masks production origin issues | CORS/same-origin surprise at deploy | Single `VITE_API_BASE_URL` switch, documented; deployment milestone revisits |
| SQLite write contention | Future concurrent writes fail | Single-user local assumption documented; Postgres path not designed away |
| Dependency drift | Reproducibility breaks | Commit `package-lock.json`; compatible-release bounds in `pyproject.toml`; CI installs from lock |
| Half-finished PWA | Users expect offline/install | Manifest ships without service worker; README states PWA install is out of scope |
| No auth model yet | Multi-user retrofit is expensive | Explicitly out of scope; user identity decided before any user-scoped table |
| Health slice grows into real features | Milestone creep | Acceptance criteria cap M1 at one endpoint and one UI card |

## Open questions (resolve before Milestone 2, not now)

1. Single-user local app, or accounts from the start? This determines every
   table's ownership column and the auth boundary.
2. Is the first persistence unit a `meal` with nutrition snapshots, or separate
   `food` and `meal_item` records?
3. Local-only SQLite for the foreseeable future, or hosted Postgres at launch?
4. Does the first AI flow require background jobs, or is a synchronous request
   with a confirmation step sufficient?
