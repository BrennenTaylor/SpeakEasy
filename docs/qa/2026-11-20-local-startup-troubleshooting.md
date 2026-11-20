# Local Startup and Branch Checkout QA

## Scope

- QA runs from the primary repository checkout; no linked worktree is required.
- Covers the two things that blocked manual QA on 2026-11-20: being on the wrong branch, and starting the app without migrating the local database.

## 1. Confirm you are on the m2 branch

From the repository root:

```bash
git status --short --branch
```

Expected: `## m2-meal-logging...origin/m2-meal-logging`.

If it says `main`, switch:

```bash
git checkout m2-meal-logging
```

If Git says the branch is already checked out in another directory, that directory is a linked worktree. After confirming it has no uncommitted work, remove it from the repository root:

```bash
git worktree list
git worktree remove <path-to-worktree>
git checkout m2-meal-logging
```

`git worktree list` should then show only your primary checkout.

If you were seeing the old app with no meal-entry fields, you were on `main`.

## 2. Migrate before starting the servers

From the repository root:

```bash
nvm use
make setup
make migrate
make dev-backend    # terminal 1
make dev-frontend   # terminal 2
```

`make migrate` creates the `foods`, `meals`, and `meal_items` tables. Skipping it produces `sqlite3.OperationalError: no such table: meals` and HTTP 500 from the API.

Expected migration output:

```text
Running upgrade  -> 0001_baseline
Running upgrade 0001_baseline -> 0002_meal_logging
```

## 3. Verify the services

```bash
curl -s http://localhost:8000/api/meals
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:5173/
```

Expected: `[]` (or your existing meals list) from the API, and `200` from the frontend. A 500 means migrations were not applied; a connection error means a dev server is not running.

## 4. If npm tools disappear

If `npm run lint` or `npm run dev` falls back to `/usr/bin/eslint` or a global Vite, repair the local install:

```bash
cd frontend
npm ci
```

Then rerun `make check`. This is an environment issue, not a reason to pin QA to a particular directory.
