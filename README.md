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

## Optional AI interpretation

Meal logging works without any AI service. To enable **Find foods** on a typed description, copy `backend/.env.example` to `backend/.env` and set `APP_OPENAI_API_KEY` (separate from ChatGPT Plus) and optionally `APP_USDA_API_KEY`. The default model is `gpt-6-luna`; set a monthly API billing limit. USDA's `DEMO_KEY` works but is rate-limited to 30 requests/hour.

Interpretation is read-only until you click **Add** (saves a food) and **Confirm** (saves the meal). Without a key, the endpoint returns HTTP 503 with `AI interpretation is not configured`; manual search and label entry still work.

See [AI meal interpretation QA steps](docs/qa/2026-11-20-ai-meal-interpretation.md) for key setup, live provider checks, no-write verification, and outage testing.

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
- **Node version mismatch:** If `node --version` reports Node 12 or an older version, run `nvm use` in the repository root to switch to the supported version defined in `.nvmrc` (Node 24). `npm ci` is configured with `engine-strict=true`, so an unsupported runtime fails with an explicit `EBADENGINE` error.
- **Port conflicts (8000 or 5173):** If port 8000 is in use, check for an existing uvicorn process (`lsof -i :8000` or `pgrep -f uvicorn`). If port 5173 is in use, check for an existing Vite process (`lsof -i :5173`).
- **Backend connection errors (502 or "Could not reach the server"):** With `make dev-frontend` running and the backend stopped, the card displays `Server responded with 502` because the Vite dev proxy answers when the backend port is closed. "Could not reach the server" appears when the request reaches no server at all (such as a built app served without the API in front of it). Both indicate the backend is not running, not a frontend bug. Recover by starting the backend with `make dev-backend` and clicking "Try again".
- **"Server did not respond":** The health request timed out after 8 seconds. Check whether the backend process is paused or blocked, then click "Try again".
- **"Find foods" shows 503:** With no `APP_OPENAI_API_KEY`, the backend returns `AI interpretation is not configured`; add the key to `backend/.env` and restart the backend. If a key is present but OpenAI times out or fails, the message is `AI interpretation is unavailable`. Manual food search and logging remain available in both cases.
- **Frequent `USDA lookup unavailable` warnings:** The default `DEMO_KEY` allows 30 requests/hour. Set `APP_USDA_API_KEY` to a free FoodData Central key; web-sourced candidates are marked `Web · low confidence`.

## Scope of this milestone

Milestone 2 adds meal logging on top of the foundation:

- Create food records from nutrition label values, including serving size, brand, source, confidence, and optional aliases.
- Search foods by name or alias and edit existing records.
- Log a food with a fractional serving and review all seven macros (calories, protein, carbs, fat, fiber, sugar, sodium) in a preview before saving.
- Backend `Decimal` arithmetic produces meal totals, returned as JSON strings so precision survives the API boundary.
- Nothing is written until the user confirms the preview. A preview request, an unknown food id, or an empty item list creates no meal, and logging works with no AI service configured.
- Logged items keep an immutable nutrition snapshot, so meal history stays stable when the underlying food is edited later.
- Optional AI interpretation returns sourced candidates from USDA FoodData Central or a linked web page; missing values stay null until the user supplies them.
- Interpretation writes nothing on its own. Adding a candidate saves a food; the meal is saved only after the existing Confirm step.

**Coming next:**
- Recipe description and recipe text entry through the same lookup layer.
- Photo upload.
- Nutrition insights.

**CI:**
GitHub Actions ran on the push to `main` (run `44674002201`) and succeeded. `.github/workflows/ci.yml` uses the same `make check` gate as local development.

