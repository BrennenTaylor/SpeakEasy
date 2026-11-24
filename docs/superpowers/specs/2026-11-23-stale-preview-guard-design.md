# Design: keep Confirm tied to the reviewed preview (2026-11-23)

Backlog task 1, milestone 1. Intent: a phone user changes a quantity while a preview request is in flight. Confirm must never save a quantity whose total they have not reviewed.

## Goals

- Any change to the description, item list, or quantity clears the visible totals and disables Confirm at once.
- A preview result updates totals only when it belongs to the draft the user currently sees.
- A late success from an older preview cannot re-enable Confirm.
- A failed preview leaves the draft editable and unsaved.
- A component test holds the first preview open, changes the quantity, attempts Confirm, sees zero meal-creation requests, releases the stale response, then confirms and saves the new quantity.

## Non-goals

- Serving-basis conversion or source switching (task 2).
- Web nutrition verification (task 3).
- Quantity carried through label completion (task 4).
- Precision policy, idempotency keys, obsolete interpretation results, or retry deduplication (tasks 5-8).

## Constraints

`MealLogger.tsx` already aborts the previous preview request and keeps `itemsRef` in sync. It does not clear `totals` on quantity edits and does not check that a resolved preview still matches the draft. `MealReview.tsx` already disables Confirm when `totals` is null or `canConfirm` is false. No new dependencies. The QA runbook requirement in `AGENTS.md` applies.

## Approaches

1. **Request generation token (chosen).** Every draft change bumps a counter and clears totals. Each preview captures the counter. Its response writes state only when the counter still matches and the request was not aborted. Confirm also checks that the displayed totals came from the current counter.
2. **Draft hash.** Compare a serialized payload with the current draft before accepting a response. This duplicates the payload shape in two places and still needs explicit state clearing.
3. **Abort plus a boolean flag.** Abort alone cannot stop a response that resolved before the abort call, so a late success can still write stale totals.

The counter gives one rule for late successes, failures, and Confirm. It fits the existing abort logic instead of replacing it.

## Design

Add a preview version ref in `MealLogger`. Route description edits, `handleAdd`, `handleQuantityChange`, and `handleRemove` through one invalidation step: clear totals, bump the version, abort the pending request. `runPreview` captures the version and the payload it sent. On success, it writes totals and records that version as reviewed only when the version still matches and the request was not aborted. On failure, it clears totals and leaves the error visible. `handleConfirm` requires the reviewed version to match the current version before it posts.

`MealReview` needs no behavior change; it already renders the disabled state from the props.

Tests use a deferred preview response in `MealLogger.test.tsx` to hold the one-serving request open while the user edits to two servings. The test asserts no `POST /api/meals` during the hold or after the stale response resolves, then enables and uses Confirm after the fresh preview and checks the saved quantity.

## Repository housekeeping

The handoff documents from ChatGPT are untracked in `app-calorie`. Commit them with the broken link in `docs/2026-11-23-opencode-backlog.md` corrected from `../opencode-meal-logging-backlog.md` to `opencode-meal-logging-backlog.md`. Mark backlog task 1 complete only after its acceptance criteria pass.

## Verification

- Focused: `cd frontend && npm run test -- src/components/MealLogger.test.tsx`
- Full gate: `make check`
- Manual runbook: `docs/qa/2026-11-23-stale-preview-guard.md`
