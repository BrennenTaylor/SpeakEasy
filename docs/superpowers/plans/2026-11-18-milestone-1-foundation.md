# Milestone 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, fully gated skeleton — React shell talking to a typed FastAPI health endpoint over Vite's dev proxy, with Alembic migrations and one command that lints, type-checks, tests, and builds everything.

**Architecture:** Two top-level projects (`frontend/`, `backend/`) that keep their native tooling and lockfiles, with a thin root `Makefile` as the only command surface. All API routes live under `/api`; Vite proxies `/api` to `127.0.0.1:8000` in development, so no CORS configuration exists. Alembic ships from day one with an empty baseline revision — migration wiring is proven, domain schema is deferred to Milestone 2.

**Tech Stack:** React 19 + TypeScript 7 + Vite 8 + Tailwind 4 (via `@tailwindcss/vite`), FastAPI 0.165 + Pydantic 2.14 + pydantic-settings, SQLAlchemy 2.1 + Alembic 1.20 on SQLite, pytest 9, Vitest 5 + Testing Library, Ruff + mypy, ESLint + Prettier.

**Spec:** `docs/superpowers/specs/2026-11-18-milestone-1-foundation-design.md`

## Global Constraints

- **Interpreter:** `/usr/bin/python3.12` (3.12.16). System `python3` is 3.10.12 and must not be used. `PYTHON ?= python3.12` in the Makefile; CI passes `PYTHON=python`.
- **Node:** 24.22.3 via nvm only (`.nvmrc` = `24`). No system Node 12. Every frontend command runs after `nvm use`.
- **No new dependencies** beyond the lists in Tasks 2 and 5. Adding one requires a stated reason in the commit message.
- **No domain schema, no auth, no user table, no service worker, no AI, no nutrition arithmetic** in this milestone.
- **No secrets in the bundle.** Only `VITE_*` values reach the browser; credentials are `APP_*` env vars, server-side only.
- **Tests never touch the developer database.** Always in-memory SQLite or a temp file under the OS temp dir.
- **`make check` is non-mutating:** `--check` lint modes, disposable migration DB removed afterward, `git status` clean when it exits 0.
- **All routes under `/api`.**
- Nutrition values will be `Decimal` when they arrive; introduce no floats that would later need converting.

## Review Focus

1. **Backend unreachable from the browser** — fetch rejects; the card must show a readable error and a working retry, never a blank page or an endless spinner. Tested in Task 6.
2. **200 response with the wrong shape** (proxy returns HTML, field renamed, `"status":"degraded"`) — must be treated as an error, never displayed as OK. Tested in Task 6.
3. **Retry pressed while a request is in flight** — exactly one request in flight; the button is disabled, no state race. Tested in Task 6.
4. **Migration downgrade followed by re-upgrade** — a half-migrated database must never result; base → head → base → head all succeed. Tested in Task 3.
5. **Health endpoint with no database file present** — liveness must not depend on a database, so a fresh clone reaching `/api/health` before any migration still returns 200. Tested in Task 2.

---

## File Structure

Created by this plan (end state):

```text
app-calorie/
├── Makefile
├── README.md
├── .github/workflows/ci.yml          # written, not pushed (see Decision note)
├── backend/
│   ├── pyproject.toml
│   ├── .python-version               # 3.12
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_baseline.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # create_app(), app
│   │   ├── api/__init__.py
│   │   ├── api/router.py             # api_router, prefix /api
│   │   ├── api/routes/__init__.py
│   │   ├── api/routes/health.py      # HealthResponse, router
│   │   ├── core/__init__.py
│   │   ├── core/config.py            # Settings, get_settings()
│   │   ├── core/db.py                # build_engine, build_session_factory, get_session
│   │   └── models/__init__.py
│   │   └── models/base.py            # Base
│   ├── data/.gitkeep
│   ├── scripts/check_migrations.py
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_db.py
│       └── test_migrations.py
└── frontend/
    ├── package.json  package-lock.json
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json                 # single config (simpler than project references)
    ├── eslint.config.js
    ├── .prettierrc.json  .prettierignore
    ├── .env.example
    ├── public/manifest.webmanifest
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── api/health.ts
        ├── components/HealthCheck.tsx
        ├── test/setup.ts
        ├── App.test.tsx
        └── components/HealthCheck.test.tsx
```

**Deliberate deviations from the spec's tree, both for less drift:** one `tsconfig.json` instead of `tsconfig.app.json`/`tsconfig.node.json` (M1 has no multi-target build), and migration verification as `backend/scripts/check_migrations.py` rather than shell logic inline in the Makefile (so it can be run and reasoned about directly).

**Decision note (from design review):** `git init` and the first commit are deliverables here — acceptance criterion 8 is unverifiable otherwise, and `package-lock.json` must be committed. `.github/workflows/ci.yml` is written and committed but **not executed and not pushed**; no remote is created in this milestone, so the workflow is an unverified artifact until one exists. Task 7 records that limitation in the README.

---

### Task 1: Repository baseline

**Files:**
- Create: `README.md`
- Modify: `docs/superpowers/specs/2026-11-18-milestone-1-foundation-design.md:3` (status line)

**Interfaces:**
- Consumes: nothing.
- Produces: a git repository with one commit; `README.md` prerequisite section that later tasks append to.

- [ ] **Step 1: Initialize the repository**

Run: `cd /home/brtayl/app-calorie && git init -b main`
Expected: `Initialized empty Git repository in /home/brtayl/app-calorie/.git/`

- [ ] **Step 2: Write the README prerequisites section**

`README.md` begins with: project name, one-sentence purpose, then:

```markdown
## Prerequisites

- Python 3.12 (`/usr/bin/python3.12`). System `python3` is 3.10 and will not work.
- Node 24 via nvm: `nvm use` (reads `.nvmrc`).
- `make`, `git`.

## Quick start

    make setup
    make dev-backend      # terminal 1, http://127.0.0.1:8000
    make dev-frontend     # terminal 2, http://localhost:5173

Open http://localhost:5173 in a phone-sized window (390 px wide).
```

Leave `## Commands`, `## Database and migrations`, `## Troubleshooting`, and `## Scope of this milestone` as empty headings for Task 7.

- [ ] **Step 3: Mark the spec approved**

Change line 3 of the spec from `**Status:** Proposed for approval` to `**Status:** Approved`.

- [ ] **Step 4: Commit the baseline**

```bash
git add -A
git commit -m "chore: initialize repository with engineering rules and M1 design"
```

Verify: `git status --short` prints nothing.

---

### Task 2: Backend skeleton and typed health endpoint

**Files:**
- Create: `backend/pyproject.toml`, `backend/.python-version`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/app/api/__init__.py`, `backend/app/api/router.py`, `backend/app/api/routes/__init__.py`, `backend/app/api/routes/health.py`, `backend/tests/conftest.py`, `backend/tests/test_health.py`
- Modify: `Makefile` (create), `README.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `app.main.create_app() -> FastAPI` and module-level `app: FastAPI`
  - `app.main.api_router` imported from `app.api.router`, variable `api_router: APIRouter` with `prefix="/api"`
  - `app.api.routes.health.HealthResponse` — `status: Literal["ok"]`
  - `GET /api/health` → `200 {"status": "ok"}`
  - Make targets `setup`, `setup-backend`, `dev-backend`, `test-backend`, `lint-backend`, `typecheck-backend`

- [ ] **Step 1: Write `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "app-calorie-backend"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.165,<0.166",
  "uvicorn[standard]>=0.54,<0.55",
  "pydantic>=2.14,<3",
  "pydantic-settings>=2.16,<3",
  "sqlalchemy>=2.1,<2.2",
  "alembic>=1.20,<1.21",
]

[project.optional-dependencies]
dev = ["pytest>=9.2,<10", "httpx>=0.28,<0.29", "ruff>=0.17,<0.18", "mypy>=2.4,<3"]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
files = ["app"]
strict = true
```

Also write `backend/.python-version` containing `3.12`, and `backend/.env.example`:

```dotenv
# Copy to .env for local overrides. Never commit .env.
APP_ENVIRONMENT=development
APP_DATABASE_URL=sqlite:///./data/app.db
```

- [ ] **Step 2: Write the failing tests**

`backend/tests/conftest.py`:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
```

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_documented_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/health" in schema["paths"]
    assert schema["paths"]["/api/health"]["get"]["responses"]["200"]["content"]


def test_health_does_not_require_a_database(tmp_path, monkeypatch) -> None:
    """Liveness must work before any migration has run."""
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'absent.db'}")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
    assert not (tmp_path / "absent.db").exists()
    get_settings.cache_clear()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest tests/test_health.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 4: Implement the app**

`backend/app/core/config.py` (needed by `main.py` only for `app_name`; database fields land in Task 3):

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "Calorie Tracker API"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/api/routes/health.py`:

```python
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(status="ok")
```

`backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
```

`backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(api_router)
    return application


app = create_app()
```

Create empty `__init__.py` files in `app/`, `app/api/`, `app/api/routes/`, `app/core/`, `app/models/`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_health.py -v`
Expected: `3 passed`.

- [ ] **Step 6: Write the Makefile**

```make
PYTHON ?= $(shell command -v python3.12 >/dev/null 2>&1 && echo python3.12 || echo python3)
NPM ?= npm
BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/bin
API := $(PY)/python
ALEMBIC := $(PY)/alembic

.PHONY: help setup setup-backend setup-frontend dev-backend dev-frontend \
        migrate migration test test-backend test-frontend lint lint-backend \
        lint-frontend typecheck typecheck-backend typecheck-frontend build \
        check-migrations check

help:
	@grep -E '^[a-z-]+:' $(MAKEFILE_LIST) | sed 's/:.*//' | sort | column -c 100

setup: setup-backend setup-frontend

$(BACKEND)/.venv/.installed: $(BACKEND)/pyproject.toml
	$(PYTHON) -m venv $(BACKEND)/.venv
	$(PY)/pip install --upgrade pip
	$(PY)/pip install -e '$(BACKEND)[dev]'
	@touch $@

setup-backend: $(BACKEND)/.venv/.installed

dev-backend:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

test-backend:
	cd $(BACKEND) && .venv/bin/pytest -q

lint-backend:
	cd $(BACKEND) && .venv/bin/ruff check . && .venv/bin/ruff format --check .

typecheck-backend:
	cd $(BACKEND) && .venv/bin/mypy app
```

`setup-frontend`, `dev-frontend`, `test-frontend`, `lint-frontend`, `typecheck-frontend`, `build`, `migrate`, `migration`, `check-migrations`, and `check` are added in Tasks 5, 3, and 7. Until then `make setup` fails on the missing `setup-frontend` target — that is expected, and Task 5 completes it.

- [ ] **Step 7: Verify lint and types**

Run: `make lint-backend && make typecheck-backend`
Expected: both exit 0 with no findings.

- [ ] **Step 8: Commit**

```bash
git add backend Makefile README.md
git commit -m "feat(api): typed /api/health endpoint with app factory and backend tooling"
```

---

### Task 3: Settings, database layer, and Alembic baseline

**Files:**
- Create: `backend/app/core/db.py`, `backend/app/models/base.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_baseline.py`, `backend/scripts/check_migrations.py`, `backend/data/.gitkeep`, `backend/tests/test_db.py`, `backend/tests/test_migrations.py`
- Modify: `backend/app/core/config.py`, `backend/tests/conftest.py`, `Makefile`

**Interfaces:**
- Consumes: `app.core.config.Settings`, `get_settings()` from Task 2.
- Produces:
  - `Settings.database_url: str` (default `"sqlite:///./data/app.db"`), `Settings.sql_echo: bool` (default `False`)
  - `app.core.db.build_engine(url: str) -> Engine`
  - `app.core.db.build_session_factory(engine: Engine) -> sessionmaker[Session]`
  - `app.core.db.get_session() -> Iterator[Session]` (FastAPI dependency; no route consumes it yet — it is the session boundary Milestone 2 uses, so keep it and keep it tested)
  - `app.models.base.Base` (DeclarativeBase)
  - Make targets `migrate`, `migration`, `check-migrations`
  - `tests/conftest.py` fixture `alembic_config(tmp_path) -> Config`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_db.py`:

```python
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import build_engine, build_session_factory, get_session


def test_session_executes_sql(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unit.db'}")
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_in_memory_engine_works_with_a_single_session() -> None:
    """In-memory SQLite lives per connection; one session is the supported pattern."""
    engine = build_engine("sqlite://")
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        session.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY)"))
        session.commit()
        assert session.execute(text("SELECT count(*) FROM probe")).scalar_one() == 0


def test_get_session_yields_a_working_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'dependency.db'}")
    get_settings.cache_clear()
    session = next(get_session())
    try:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        session.close()
        get_settings.cache_clear()
```

`backend/tests/test_migrations.py`:

```python
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from app.core.db import build_engine
from app.models.base import Base


def test_upgrade_then_downgrade_then_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")  # review focus #4


def test_schema_matches_models_after_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = build_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
```

Add to `backend/tests/conftest.py`:

```python
from pathlib import Path

from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_config(tmp_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migrate.db'}")
    return config
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_db.py tests/test_migrations.py -v`
Expected: `ModuleNotFoundError: No module named 'app.core.db'`.

- [ ] **Step 3: Implement the config, engine, and Base**

Extend `backend/app/core/config.py` — add to `Settings`:

```python
    database_url: str = "sqlite:///./data/app.db"
    sql_echo: bool = False
```

`backend/app/core/db.py`:

```python
from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(url: str) -> Engine:
    connect_args: dict[str, Any] = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=get_settings().sql_echo, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session_factory = build_session_factory(build_engine(get_settings().database_url))
    with session_factory() as session:
        yield session
```

`backend/app/models/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Note: `sqlite://` (in-memory) needs `StaticPool` only when a second connection is expected. Tests use a single session, so the default pool is correct here; do not add `StaticPool` speculatively.

- [ ] **Step 4: Write the Alembic configuration**

`backend/alembic.ini` — minimal, with the URL deliberately empty so the environment drives it:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic
```

(Include the standard `[handlers]`, `[formatters]`, and `[logger_*]` sections from `alembic init`; they are boilerplate.)

`backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app.core.config import get_settings
from app.core.db import build_engine
from app.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = build_engine(_database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite cannot ALTER most columns
            poolclass=pool.NullPool,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Write the empty baseline revision**

`backend/alembic/versions/0001_baseline.py`:

```python
"""baseline: no schema yet, proves migration wiring

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Intentionally empty. Domain schema begins in Milestone 2."""


def downgrade() -> None:
    """Intentionally empty."""
```

- [ ] **Step 6: Run the migration tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_db.py tests/test_migrations.py -v`
Expected: `5 passed`.

- [ ] **Step 7: Write the migration check script**

`backend/scripts/check_migrations.py` — upgrades a temp database to head, asserts a revision exists, downgrades to base, asserts `alembic_version` is gone, upgrades again, then removes the file. Uses `tempfile.TemporaryDirectory()`; never `backend/data/`. Prints `migrations OK: head -> base -> head` and exits 0; any mismatch exits 1 with the failing step named.

Make it runnable from the repo root: the script resolves `backend/alembic.ini` via `Path(__file__).resolve().parents[1]` and inserts that directory at `sys.path[0]` so `app` imports resolve.

`backend/data/.gitkeep` — empty file, so the directory exists for the default SQLite URL.

- [ ] **Step 8: Add migration targets to the Makefile**

```make
migrate:
	cd $(BACKEND) && .venv/bin/alembic upgrade head

migration:
	@test -n "$(m)" || (echo 'usage: make migration m="description"' && exit 1)
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

check-migrations:
	cd $(BACKEND) && .venv/bin/python scripts/check_migrations.py
```

Add `migrate migration check-migrations` to `.PHONY`.

- [ ] **Step 9: Verify migrations end to end by hand**

Run: `make check-migrations`
Expected: `migrations OK: head -> base -> head`

Run: `rm -f backend/data/app.db && make migrate && make migrate && ls backend/data/app.db`
Expected: file exists; second run prints no migration steps (no-op).

- [ ] **Step 10: Verify lint and types, then commit**

Run: `make lint-backend && make typecheck-backend`
Expected: exit 0. If mypy flags the Alembic `env.py` module-level `config`, exclude `alembic/` with `[tool.mypy] exclude = ["^alembic/"]` — the migration environment is a script, not application code.

```bash
git add backend Makefile
git commit -m "feat(db): settings-driven SQLAlchemy session layer with empty Alembic baseline"
```

---

### Task 4: Frontend scaffold and mobile shell

**Files:**
- Create: `frontend/package.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`, `frontend/.env.example`, `frontend/public/manifest.webmanifest`, `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.tsx`, `frontend/src/test/setup.ts`, `frontend/src/App.test.tsx`
- Modify: `Makefile`, `README.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `App` (default export, `src/App.tsx`) rendering the shell
  - `setupFiles` wired to `src/test/setup.ts`
  - Make targets `setup-frontend`, `dev-frontend`, `test-frontend`, `lint-frontend`, `typecheck-frontend`, `build`

- [ ] **Step 1: Write `frontend/package.json`**

Versions verified available on the registry as of 2026-11-18:

```json
{
  "name": "app-calorie-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": { "node": ">=24" },
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint .",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^19.3.1",
    "react-dom": "^19.3.1"
  },
  "devDependencies": {
    "@eslint/js": "^10.0.1",
    "@tailwindcss/vite": "^4.3.5",
    "@testing-library/jest-dom": "^8.0.0",
    "@testing-library/react": "^16.3.3",
    "@testing-library/user-event": "^14.6.13",
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "@vitejs/plugin-react": "^6.3.0",
    "eslint": "^10.15.0",
    "eslint-plugin-react-hooks": "^7.1.1",
    "eslint-plugin-react-refresh": "^0.5.8",
    "globals": "^17.14.0",
    "jsdom": "^31.0.1",
    "prettier": "^3.10.1",
    "tailwindcss": "^4.3.5",
    "typescript": "^7.0.2",
    "typescript-eslint": "^8.73.0",
    "vite": "^8.3.8",
    "vitest": "^5.1.1"
  }
}
```

Run `npm install` in `frontend/` once so `package-lock.json` is generated, then commit it in Step 9.

- [ ] **Step 2: Write the failing shell test**

`frontend/src/App.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the app title inside a phone-width container", () => {
    const { container } = render(<App />);
    expect(screen.getByRole("heading", { name: /calorie tracker/i })).toBeInTheDocument();
    expect(container.querySelector(".max-w-md")).not.toBeNull();
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — cannot resolve `./App`.

- [ ] **Step 4: Write the Vite, TypeScript, Tailwind, and test configuration**

`frontend/vite.config.ts`:

```ts
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});
```

`frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});
```

`frontend/tsconfig.json` — one config, DOM + bundler resolution, `noUncheckedIndexedAccess` on:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "types": ["vite/client"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/eslint.config.js`:

```js
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "coverage", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser } },
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: { ...reactHooks.configs.recommended.rules, "react-refresh/only-export-components": "warn" },
  },
);
```

`frontend/.prettierrc.json`: `{ "printWidth": 100, "trailingComma": "all", "semi": true }`
`frontend/.prettierignore`: `dist`, `coverage`, `node_modules`, `package-lock.json`
`frontend/.env.example`: `# Empty = same-origin, routed through the Vite proxy / same host in production.`\n`VITE_API_BASE_URL=`

- [ ] **Step 5: Write the shell**

`frontend/index.html` — `lang="en"`, `<meta name="viewport" content="width=device-width, initial-scale=1">`, `<meta name="theme-color" content="#16a34a">`, `<link rel="manifest" href="/manifest.webmanifest">`, `<div id="root"></div>`, `<script type="module" src="/src/main.tsx">`.

`frontend/public/manifest.webmanifest`:

```json
{
  "name": "Calorie Tracker",
  "short_name": "Calories",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#16a34a"
}
```

No icons and no service worker in this milestone — the manifest intentionally does not claim installability.

`frontend/src/index.css`:

```css
@import "tailwindcss";
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./index.css";

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("Root element #root not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`frontend/src/App.tsx`:

```tsx
export default function App() {
  return (
    <main className="mx-auto min-h-dvh max-w-md px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Calorie Tracker</h1>
        <p className="mt-1 text-sm text-gray-600">Log a meal in plain language.</p>
      </header>
    </main>
  );
}
```

`HealthCheck` is mounted in Task 6.

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: `1 passed`.

- [ ] **Step 7: Verify typecheck, lint, format, and build**

Run: `cd frontend && npx tsc --noEmit && npx eslint . && npx prettier --check . && npx vite build`
Expected: all exit 0; `dist/` created and git-ignored. If TypeScript 7 rejects a compiler option above, fix the option, not the gate — and record the change in the commit message.

- [ ] **Step 8: Add frontend targets to the Makefile**

```make
setup-frontend:
	cd $(FRONTEND) && $(NPM) ci

dev-frontend:
	cd $(FRONTEND) && $(NPM) run dev

test-frontend:
	cd $(FRONTEND) && $(NPM) run test

lint-frontend:
	cd $(FRONTEND) && $(NPM) run lint && $(NPM) run format:check

typecheck-frontend:
	cd $(FRONTEND) && $(NPM) run typecheck

build:
	cd $(FRONTEND) && $(NPM) run build
```

Note: `setup-frontend` uses `npm ci` because the lockfile is committed by Step 9; running `make setup` before the lockfile exists fails with a clear npm error.

- [ ] **Step 9: Commit**

```bash
git add frontend Makefile README.md
git commit -m "feat(web): Vite/React/Tailwind shell with Vitest, ESLint, and Prettier"
```

---

### Task 5: Typed API client

**Files:**
- Create: `frontend/src/api/health.ts`, `frontend/src/api/health.test.ts`

**Interfaces:**
- Consumes: nothing from earlier tasks (uses `import.meta.env.VITE_API_BASE_URL`).
- Produces:
  - `type HealthResponse = { status: "ok" }`
  - `class ApiError extends Error`
  - `async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse>` — throws `ApiError` on network failure, non-2xx, invalid JSON, or shape mismatch.

- [ ] **Step 1: Write the failing tests**

`frontend/src/api/health.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, fetchHealth } from "./health";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchHealth", () => {
  it("returns the parsed body for a valid response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    await expect(fetchHealth()).resolves.toEqual({ status: "ok" });
  });

  it("rejects a 200 with the wrong shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "degraded" })));
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects a non-JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>proxy error</html>", { status: 200 })),
    );
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });

  it("reports the status code for a non-2xx response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "boom" }, 503)));
    await expect(fetchHealth()).rejects.toThrow(/503/);
  });

  it("wraps a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/api/health.test.ts`
Expected: FAIL — cannot resolve `./health`.

- [ ] **Step 3: Implement the client**

`frontend/src/api/health.ts`:

```ts
export type HealthResponse = { status: "ok" };

export class ApiError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "ApiError";
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    (value as { status: unknown }).status === "ok"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/health`, { signal, headers: { accept: "application/json" } });
  } catch (cause) {
    throw new ApiError("Could not reach the server", { cause });
  }
  if (!response.ok) {
    throw new ApiError(`Server responded with ${response.status}`);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (cause) {
    throw new ApiError("Server returned a response that was not JSON", { cause });
  }
  if (!isHealthResponse(body)) {
    throw new ApiError("Server returned an unexpected response");
  }
  return body;
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/api/health.test.ts`
Expected: `5 passed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api
git commit -m "feat(web): validated health API client that fails loudly on bad responses"
```

---

### Task 6: Health check slice

**Files:**
- Create: `frontend/src/components/HealthCheck.tsx`, `frontend/src/components/HealthCheck.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `fetchHealth`, `ApiError` from Task 5.
- Produces: `HealthCheck` (named export) rendering a status card with `role="status"` while loading and when OK, `role="alert"` on error, and a `Try again` button rendered in **every** state, disabled while a request is in flight.

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/HealthCheck.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HealthCheck } from "./HealthCheck";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("HealthCheck", () => {
  it("shows loading and then OK", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    render(<HealthCheck />);
    expect(screen.getByRole("status")).toHaveTextContent(/checking/i);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/connected/i));
  });

  it("shows an error and recovers on retry", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthCheck />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not reach the server/i);

    await user.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/connected/i));
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("treats an unexpected payload as an error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "degraded" })));
    render(<HealthCheck />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/unexpected response/i);
  });

  it("keeps the retry button disabled while a request is in flight", async () => {
    const user = userEvent.setup();
    let resolve: (value: Response) => void = () => {};
    const pending = new Promise<Response>((r) => {
      resolve = r;
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }))
      .mockReturnValueOnce(pending);
    vi.stubGlobal("fetch", fetchMock);

    render(<HealthCheck />);
    await screen.findByText(/connected/i);

    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(screen.getByRole("button", { name: /try again/i })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    resolve(jsonResponse({ status: "ok" }));
    await waitFor(() => expect(screen.getByRole("button", { name: /try again/i })).toBeEnabled());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/HealthCheck.test.tsx`
Expected: FAIL — cannot resolve `./HealthCheck`.

- [ ] **Step 3: Implement the component**

`frontend/src/components/HealthCheck.tsx` — `useState` holding a discriminated union `{ kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string }`, one `useEffect` that runs the initial check on mount, and a `runCheck` callback used by both the effect and the retry button. Track the in-flight state by deriving it from `kind === "loading"` (so the button is disabled), and guard the effect against setting state after unmount with a local `cancelled` flag. Error messages come from `ApiError.message`; anything else becomes `"Something went wrong"`. The card uses `text-sm`, `p-3 rounded-lg border`, and `break-words` so a long message wraps instead of scrolling the page sideways at 390 px.

No `setState` in render, no `useEffect` dependency on the whole state object — the effect depends on `[]` and calls `runCheck`.

- [ ] **Step 4: Mount it in `App.tsx` and update the shell test**

Wrap in a `<section aria-labelledby="status-heading">` with an `<h2 id="status-heading">Server status</h2>` above `<HealthCheck />`.

Replace `frontend/src/App.test.tsx` with both tests, since the mount now performs a fetch on render:

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders the app title inside a phone-width container", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    const { container } = render(<App />);
    expect(screen.getByRole("heading", { name: /calorie tracker/i })).toBeInTheDocument();
    expect(container.querySelector(".max-w-md")).not.toBeNull();
  });

  it("renders the server status section", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));
    render(<App />);
    expect(screen.getByRole("heading", { name: /server status/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Run the frontend tests to verify they pass**

Run: `cd frontend && npx vitest run`
Expected: all suites pass, including the 5 client tests and 4 component tests.

- [ ] **Step 6: Verify the slice against a real backend**

Run: `make dev-backend` in one terminal and `make dev-frontend` in another; open `http://localhost:5173` at 390 px width.
Expected: "Checking…" then "Connected". DevTools network shows the request going to `localhost:5173/api/health` and returning 200.

Stop the backend, press "Try again".
Expected: alert reading "Could not reach the server". No blank page, no console error that crashes the app.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(web): health check card with loading, error, and retry states"
```

---

### Task 7: Aggregate gate, CI artifact, and documentation

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `Makefile`, `README.md`

**Interfaces:**
- Consumes: every target from Tasks 2–6.
- Produces: `make check` as the single gate; README sections `## Commands`, `## Database and migrations`, `## Troubleshooting`, `## Scope of this milestone`.

- [ ] **Step 1: Add the aggregate gate**

```make
check: lint typecheck test check-migrations build
```

Confirm `check-migrations` is not `check-migrations: migrate` — it must never touch `backend/data/app.db`.

- [ ] **Step 2: Run the gate**

Run: `make check`
Expected: every phase exits 0. Then `git status --short` prints nothing (no stray `.db`, `dist`, or cache files).

If a step fails, fix that step's cause — do not add `|| true`, do not reorder to hide a failure.

- [ ] **Step 3: Write the CI workflow**

`.github/workflows/ci.yml` — on `push` and `pull_request`, `ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5` with `python-version: "3.12"`, `actions/setup-node@v4` with `node-version: "24"` and `cache: npm` / `cache-dependency-path: frontend/package-lock.json`, then:

```yaml
      - run: make setup PYTHON=python
      - run: make check PYTHON=python
```

`PYTHON=python` because setup-python exposes the interpreter as `python`, not `python3.12`.

- [ ] **Step 4: Finish the README**

Fill in:
- `## Commands` — the nine `make` targets with one line each.
- `## Database and migrations` — SQLite lives at `backend/data/app.db` (ignored); `make migrate`; `make migration m="..."` then **review the generated file** before committing; the baseline is intentionally empty; batch mode is on for future SQLite `ALTER`s.
- `## Troubleshooting` — wrong Python (`python3 --version` showing 3.10 → use `make setup` which prefers `python3.12`); wrong Node (`node --version` showing 12 → `nvm use`); port 8000/5173 in use; "could not reach the server" means the backend is not running, not a frontend bug.
- `## Scope of this milestone` — no meal logging, no AI, no nutrition data, no auth, no service worker, no deploy. State plainly that `.github/workflows/ci.yml` has **not been executed** because no remote exists yet; it becomes authoritative the first time it runs.

- [ ] **Step 5: Walk the acceptance criteria**

Run each and confirm:

| # | Command | Expected |
| --- | --- | --- |
| 1 | `rm -rf backend/.venv frontend/node_modules && make setup` | exit 0 |
| 2 | `make check` | exit 0 |
| 3 | `make dev-backend` then `curl -i localhost:8000/api/health` | `200`, `{"status":"ok"}`; `/docs` renders |
| 4 | `make check-migrations` | `head -> base -> head` |
| 5 | `make dev-frontend`, 390 px window | no horizontal scroll, heading inside `max-w-md` |
| 6 | stop backend, press retry | alert + working retry |
| 7 | DevTools network on `:5173` | `/api/health` → 200, no CORS error |
| 8 | `git status --short` after `make check` | empty |
| 9 | `make lint-backend && make typecheck-backend` | exit 0 |
| 10 | `make lint-frontend && make typecheck-frontend` | exit 0 |
| 11 | follow README from scratch | no unanswered questions |

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: aggregate make check gate, CI workflow, and contributor docs"
```

---

## Definition of Done

- `make setup` on a clean clone with Python 3.12 + Node 24 exits 0.
- `make check` exits 0 and leaves the tree clean.
- `curl localhost:8000/api/health` returns `{"status":"ok"}`; `/docs` lists the route.
- Alembic upgrades, downgrades, and re-upgrades a temp database; the baseline is empty and matches `Base.metadata`.
- The browser shows loading → connected with the backend up, and a readable error with a working retry with it down.
- No secrets, databases, `node_modules`, or `dist` committed.
- Commits are one per task, each independently reviewable.
