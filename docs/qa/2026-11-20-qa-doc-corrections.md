# QA Steps Documentation Corrections

## Scope

- Companion QA for the documentation correction on the `m2-meal-logging` branch (PR #1).
- Verifies that the Milestone 2 runbook is followable in any checkout and that the PR's QA link resolves.

## 1. Verify the PR link resolves

1. Open https://github.com/BrennenTaylor/SpeakEasy/pull/1.
2. In the description, click **Milestone 2 QA Steps**.
3. Expected: the file opens at `https://github.com/BrennenTaylor/SpeakEasy/blob/m2-meal-logging/docs/qa/2026-11-20-milestone-2-meal-logging.md`, not a 404 under `/pull/docs/...`.

After the branch is merged, the same link should be updated to `blob/main/...`.

## 2. Verify the corrected runbook text

From the root of any checkout containing the change:

```bash
grep -F "chicken nuggets" docs/qa/2026-11-20-milestone-2-meal-logging.md
grep -F "curl -s http://localhost:8000/api/meals" docs/qa/2026-11-20-milestone-2-meal-logging.md
grep -F "999.0000 kcal" docs/qa/2026-11-20-milestone-2-meal-logging.md
! grep -F "/home/brtayl/.local/share/opencode/worktree" docs/qa/2026-11-20-milestone-2-meal-logging.md
```

Expected: all four commands exit 0. The last command proves the runbook contains no machine-specific path.

## 3. Follow the two corrected behavioral checks

Start the app as described in the Milestone 2 runbook, then confirm:

- Searching `chicken nuggets` returns `Test Nuggets`. That string is an alias, not part of the food name, so the check can fail if alias matching breaks.
- After editing the food to `999` and confirming a meal, `curl -s http://localhost:8000/api/meals` shows the old meal with `totals.calories` of `750.0000` and item `calories` of `250.0000`. This reads server state, so stale browser state cannot make it pass.

## 4. Verify the automated gate is portable

From the root of any checkout containing the change:

```bash
nvm use
make check
```

Expected: exit 0, with 28 backend tests, 45 frontend tests, clean lint/format/type checks, the migration round-trip, and a production build.

If `npm run lint` instead reports `/usr/share/nodejs/eslint` and `Cannot find module 'mkdirp'`, that checkout's local install is broken. Repair it with `npm ci` in `frontend/`, then rerun `make check`. This is an environment problem, not a reason to pin QA to one directory.
