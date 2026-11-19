# Calorie Tracker

A phone-first calorie tracking PWA.

## Prerequisites

- Python 3.12 (`/usr/bin/python3.12`). System `python3` is 3.10 and will not work.
- Node 24 via nvm: `nvm use` (reads `.nvmrc`).
- `make`, `git`.

## Quick start

    make setup
    make dev-backend      # terminal 1, http://127.0.0.1:8000
    make dev-frontend     # terminal 2, http://localhost:5173

Open http://localhost:5173 in a phone-sized window (390 px wide).

## Commands

- `make setup` — Creates `backend/.venv`, installs backend dependencies, and runs `npm ci` for the frontend.
- `make dev-backend` — Starts the FastAPI backend with uvicorn on port 8000 with live reload.
- `make dev-frontend` — Starts the Vite frontend development server on port 5173.
- `make migrate` — Applies pending Alembic migrations to `head` against `backend/data/app.db`.
- `make migration m="..."` — Autogenerates a new Alembic migration revision with a message.
- `make test` — Runs backend unit tests (`pytest`) and frontend tests (`vitest`).
- `make lint` — Checks backend formatting and linting (`ruff`) and frontend style (`eslint`, `prettier`).
- `make typecheck` — Runs static type checking for backend (`mypy`) and frontend (`tsc`).
- `make build` — Compiles the frontend production bundle (`vite build`).
- `make check` — Runs the non-mutating pre-commit/CI gate (`lint`, `typecheck`, `test`, `check-migrations`, `build`).

## Database and migrations

The local development database is SQLite and lives at `backend/data/app.db` (git-ignored).

- Run `make migrate` to apply all migrations up to `head`.
- Run `make migration m="description"` to generate a new migration revision from SQLAlchemy model metadata changes.
- **Always review the generated migration file** in `backend/alembic/versions/` before committing. Autogenerate can miss schema nuances or misinterpret renames.
- The baseline migration (`0001_baseline`) is intentionally empty to establish Alembic tracking and prove migration wiring before domain models are introduced.
- Alembic runs with batch mode enabled (`render_as_batch=True`), which is required for SQLite table alterations (such as `ALTER TABLE` operations) in future migrations.
- `make check-migrations` verifies that migrations upgrade to head, downgrade to base, and re-upgrade to head cleanly on a temporary database without touching `backend/data/app.db`.

## Troubleshooting

- **Python version mismatch:** If `python3 --version` reports 3.10 or another unsupported version, `make setup` uses `python3.12` by default; override with `make setup PYTHON=/path/to/python3.12`.
- **Node version mismatch:** If `node --version` reports Node 12 or an older version, run `nvm use` in the repository root to switch to the supported version defined in `.nvmrc` (Node 24).
- **Port conflicts (8000 or 5173):** If port 8000 is in use, check for an existing uvicorn process (`lsof -i :8000` or `pgrep -f uvicorn`). If port 5173 is in use, check for an existing Vite process (`lsof -i :5173`).
- **Backend connection errors (502 or "Could not reach the server"):** With `make dev-frontend` running and the backend stopped, the card displays `Server responded with 502` because the Vite dev proxy answers when the backend port is closed. "Could not reach the server" appears when the request reaches no server at all (such as a built app served without the API in front of it). Both indicate the backend is not running, not a frontend bug. Recover by starting the backend with `make dev-backend` and clicking "Try again".

## Scope of this milestone

Milestone 1 is strictly foundation infrastructure:
- FastAPI backend skeleton with health endpoint (`GET /api/health`) and OpenAPI docs (`/docs`).
- React + TypeScript frontend shell with mobile layout (390 px) and health status card with retry.
- Database and migration foundation (SQLite + SQLAlchemy 2.0 + Alembic).
- Unified developer tooling, automated checks (`make check`), and CI workflow definition.

**Out of scope for Milestone 1:**
- No meal logging.
- No AI integration or LLM prompting.
- No external nutrition provider data or lookups.
- No user authentication or multi-tenant authorization.
- No service worker or offline caching.
- No production deployment configuration or hosting.

**CI Note:**
The GitHub Actions workflow in `.github/workflows/ci.yml` has **not been executed** because no git remote exists yet for this repository. It will become authoritative the first time it runs on a remote repository.

