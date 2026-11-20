# QA Steps Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make user-runnable QA steps a durable, file-backed part of every change, and add the QA runbook for Milestone 2.

**Architecture:** This is a documentation-only change. It adds one standing rule to `AGENTS.md`, creates a dated QA runbook under `docs/qa/`, and links that runbook from the open PR description. No application code changes.

**Tech Stack:** Markdown, Git, GitHub CLI (`gh`).

**Spec:** `docs/superpowers/specs/2026-11-20-qa-steps-documentation-design.md`

## Global Constraints

- No application code changes.
- No new dependencies.
- Keep one QA file per change, named `YYYY-MM-DD-<topic>.md`.
- Preserve the existing `AGENTS.md` structure.
- Do not change the Milestone 2 implementation or its automated tests.
- `make check` must remain green.
- PR #1 description must link the QA runbook.

## Review Focus

- A future change could omit QA steps entirely — pinned by the `AGENTS.md` rule check in Step 4.
- A QA file could be created in the wrong place or with the wrong naming pattern — pinned by the path check in Step 4.
- The Milestone 2 runbook could omit the snapshot-immutability check — pinned by the content check in Step 4.
- The PR description could lose its existing summary or lack the QA link — pinned by the append-then-verify flow in Steps 7 and 8.
- A docs-only change could still leave the repo gate red — pinned by `make check` in Step 5.

---

### Task 1: Add QA documentation rule and Milestone 2 runbook

**Files:**
- Modify: `AGENTS.md:41-46`
- Create: `docs/qa/2026-11-20-milestone-2-meal-logging.md`

**Interfaces:**
- Consumes: QA walkthrough already provided for Milestone 2 and PR #1 URL `https://github.com/BrennenTaylor/SpeakEasy/pull/1`.
- Produces: `docs/qa/2026-11-20-milestone-2-meal-logging.md` and an `AGENTS.md` rule that future changes can follow.

- [ ] **Step 1: Add the standing QA rule to `AGENTS.md`**

Under `## Quality`, add exactly one bullet:

```markdown
- Every change must include user-runnable QA steps in a Markdown file under `docs/qa/` named `YYYY-MM-DD-<topic>.md`; link that file from the change summary or PR description.
```

- [ ] **Step 2: Create `docs/qa/2026-11-20-milestone-2-meal-logging.md`**

Write a self-contained runbook with these sections, in this order:

1. `# Milestone 2 QA Steps`
2. `## Scope` — PR #1 link, branch `m2-meal-logging`, and note that typing a meal sentence is stored as text but not AI-parsed in M2.
3. `## Automated gate` — commands:

```bash
cd /home/brtayl/.local/share/opencode/worktree/8e66d7/m2-meal-logging
nvm use
make check
```

Expected: lint/format/mypy/typecheck pass; 28 backend tests, 45 frontend tests; migrations `head -> base -> head`; Vite build succeeds.

4. `## Start the app` — `make setup`, `make dev-backend`, `make dev-frontend`, open `http://localhost:5173` at 390 px wide.
5. `## Create a food from a label` — exact values: `Test Nuggets`, `Test Brand`, `1 cup`, `100`, calories `250`, protein `10`, carbs `20`, fat `10`, fiber `1`, sugar `2`, sodium `300`, confidence `High`, aliases `nuggets, chicken nuggets`.
6. `## Search by alias and verify backend scaling` — search `nuggets`; after two rows at qty 1 expect `500/20/40/20/2/4/600`; after changing first qty to `2` expect `750/30/60/30/3/6/900` for calories/protein/carbs/fat/fiber/sugar/sodium.
7. `## Verify confirm gating and no early writes` — Recent meals unchanged before Confirm; clearing description disables Confirm; retyping restores totals; Confirm clears draft and adds one recent meal.
8. `## Verify saved-food editing and snapshot immutability` — edit calories to `999`; search shows `999`; already logged meal still shows `750` and original macros.
9. `## Error-state check` — stop backend, expect red alert; restart and search succeeds.
10. `## Mobile layout check` — no horizontal scroll; Add/Edit/Remove/Confirm visible at 390 px.

- [ ] **Step 3: Commit the documentation files**

```bash
git add AGENTS.md docs/qa/2026-11-20-milestone-2-meal-logging.md docs/superpowers/specs/2026-11-20-qa-steps-documentation-design.md docs/superpowers/plans/2026-11-20-qa-steps-documentation.md
git commit -m "docs: require QA steps for every change"
```

- [ ] **Step 4: Verify the committed files**

Run:

```bash
test -f docs/qa/2026-11-20-milestone-2-meal-logging.md
grep -F "docs/qa/" AGENTS.md
grep -F "snapshot immutability" docs/qa/2026-11-20-milestone-2-meal-logging.md
git status --short
```

Expected: all checks succeed; `git status --short` is empty.

- [ ] **Step 5: Run the full gate**

Run: `make check`

Expected: exit 0 with 28 backend tests, 45 frontend tests, clean lint/format/type checks, migration round-trip, and production build.

- [ ] **Step 6: Push the documentation commit**

Run: `git push origin m2-meal-logging`

Expected: push succeeds to PR #1 branch.

- [ ] **Step 7: Append the QA link to PR #1 without losing the existing body**

Run:

```bash
gh pr view 1 --json body --jq .body > /tmp/opencode/m2-pr-body-current.md
printf '\n\nSee [Milestone 2 QA Steps](docs/qa/2026-11-20-milestone-2-meal-logging.md) for user-runnable validation steps.\n' >> /tmp/opencode/m2-pr-body-current.md
gh pr edit 1 --body-file /tmp/opencode/m2-pr-body-current.md
```

Expected: commands exit 0; the existing PR summary remains.

- [ ] **Step 8: Verify the PR link**

Run: `gh pr view 1 --json body`

Expected: body contains `docs/qa/2026-11-20-milestone-2-meal-logging.md`.

- [ ] **Step 9: Self-review**

Read `git show --stat HEAD` and the QA file once. Confirm only documentation files changed, all required QA sections are present, and no app code was modified.
