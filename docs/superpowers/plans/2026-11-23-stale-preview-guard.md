# Stale Preview Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a delayed or failed preview response from letting the user confirm a meal quantity they did not review.

**Architecture:** Keep the existing abort controller, then add a preview version counter and a reviewed-version ref in `MealLogger`. Every draft mutation invalidates totals and bumps the version. A preview applies only when its captured version still matches. Confirm requires the reviewed version to match the current version.

**Tech Stack:** React 19, TypeScript, Vitest, React Testing Library, Tailwind. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-23-stale-preview-guard-design.md`

## Global Constraints

- Python 3.12 and Node 24, as documented in `README.md`.
- Implement only backlog task 1. Later tasks stay unchecked.
- Do not change the backend, database schema, nutrition arithmetic, or `MealReview`.
- Do not add dependencies.
- Keep the existing 250 ms preview debounce and 8 s client timeout.
- Every behavior change needs a dated QA file under `docs/qa/` and a link from the change summary.
- Mark backlog task 1 `[x]` only after its acceptance criteria pass.

## Review Focus

- A late success from an obsolete quantity must not show stale calories or enable Confirm. Test: `ignores a late preview response from an obsolete quantity`.
- A late failure from an obsolete draft must not show an error for the current draft. Test: `ignores a late preview failure from an obsolete draft`.
- Removing an item while a preview is pending must drop the stale result. Test: `invalidates totals when an item is removed during a pending preview`.
- A failed preview for the current draft must leave Confirm disabled and save nothing. Test: existing `clears totals and blocks Confirm when a preview fails`.
- Clearing the description must disable Confirm and remove totals. Test: existing `keeps Confirm disabled and does not save after the description is cleared`.

---

### Task 1: Guard preview results by draft version

**Files:**
- Modify: `frontend/src/components/MealLogger.tsx`
- Modify: `frontend/src/components/MealLogger.test.tsx`
- Create: `docs/qa/2026-11-23-stale-preview-guard.md`
- Modify: `docs/opencode-meal-logging-backlog.md` (task 1 checkbox only)

**Interfaces:**
- Consumes: `previewMeal(payload, signal)` from `../api/meals`; `MealReview` props `totals`, `canConfirm`, and `submitting`.
- Produces: no new exported API. Internal refs `previewVersionRef` and `reviewedVersionRef` govern state writes and confirmation.

- [ ] **Step 1: Add deterministic fetch helpers to `MealLogger.test.tsx`**

Add a deferred-promise helper and let `StubOptions` queue preview responses in order:

```ts
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
```

Add `previewResponses?: Promise<Response>[]` to `StubOptions`. In the `/api/meals/preview` branch, return `options.previewResponses?.shift()` when present; otherwise keep the existing resolved response. Add a `previewCalls(stub)` helper that filters mock calls for `POST /api/meals/preview`.

- [ ] **Step 2: Write the failing regression tests**

Add three tests to `MealLogger.test.tsx`:

```ts
it("ignores a late preview response from an obsolete quantity", async () => {
  // Queue two held responses: the one-serving preview and the two-serving preview.
  // Add nuggets, edit quantity to 2, assert both calls happened and Confirm is
  // disabled. Click Confirm and assert no POST /api/meals. Resolve the stale
  // response with calories "111.0000"; assert that value never appears and
  // Confirm stays disabled. Resolve the fresh response with previewTotals;
  // assert "250.0000" appears, Confirm becomes enabled, and the saved payload
  // contains quantity "2".
});

it("ignores a late preview failure from an obsolete draft", async () => {
  // Hold the first preview, edit quantity to 2, let the second preview resolve
  // with previewTotals, then reject the first response. Assert no alert appears,
  // "250.0000" remains, Confirm stays enabled, and no POST /api/meals happened
  // before the deliberate confirm.
});

it("invalidates totals when an item is removed during a pending preview", async () => {
  // Hold the first preview, add a second food, hold the resulting preview, then
  // remove the first food. Resolve the stale response with a distinct calorie
  // value. Assert the stale value never appears and Confirm stays disabled
  // until the fresh response resolves.
});
```

Use `await user.clear(quantity)`, `await user.type(quantity, "2")`, and `await waitFor(...)` exactly as the surrounding tests do. Use `jsonResponse({ ...previewTotals, calories: "111.0000" })` for stale success bodies.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/MealLogger.test.tsx`
Expected: the three new tests fail. The current code leaves stale totals visible, re-enables Confirm from stale responses, or shows a stale error.

- [ ] **Step 4: Implement the version guard in `MealLogger.tsx`**

Add `previewVersionRef = useRef(0)` and `reviewedVersionRef = useRef<number | null>(null)` beside the existing refs.

Add a stable `invalidatePreview()` callback that aborts and clears `previewControllerRef`, increments `previewVersionRef`, sets `reviewedVersionRef.current = null`, and clears `totals` and `error`.

Call `invalidatePreview()` at the start of the description effect, `handleAdd`, `handleQuantityChange`, and `handleRemove`. Keep their existing state and preview calls after that.

In `runPreview`, capture `const version = previewVersionRef.current;` before the request. In the success handler, return when `version !== previewVersionRef.current || controller.signal.aborted`; otherwise call `setTotals(result)` and set `reviewedVersionRef.current = version`. In the failure handler, return on the same stale check; otherwise clear totals, clear the reviewed version, and set the error.

In `handleConfirm`, keep the existing guard and add `reviewedVersionRef.current !== previewVersionRef.current` as a reason to return before `createMeal`.

- [ ] **Step 5: Run the focused tests to verify they pass**

Run: `cd frontend && npm run test -- src/components/MealLogger.test.tsx`
Expected: all tests pass, including the existing preview failure and cleared-description tests.

- [ ] **Step 6: Add the QA runbook**

Create `docs/qa/2026-11-23-stale-preview-guard.md`. Include:

- What changed: stale preview results no longer control Confirm.
- Automated checks with the exact focused command from Step 5 and `make check`.
- Manual steps with the backend and frontend running: add a saved food, wait for totals, set the quantity to 2, tap Confirm while a throttled preview is pending, verify no meal appears; then let the fresh preview finish, confirm, and verify the saved meal shows quantity 2 and doubled totals.
- A failure case: stop the backend during a preview, verify the error and no save, restart, edit the quantity, and verify recovery.
- A limitation note: this task does not address serving-basis conversion or idempotent saves (backlog tasks 2 and 6).

- [ ] **Step 7: Mark the backlog item complete**

Change `- [ ] 1. Confirm only the quantity the user reviewed` to `- [x] 1. Confirm only the quantity the user reviewed` in `docs/opencode-meal-logging-backlog.md`. Leave tasks 2 through 44 unchecked.

- [ ] **Step 8: Run the full gate**

Run: `make check`
Expected: lint, format, mypy, TypeScript, backend pytest, frontend vitest, migration round trip, and production build all pass.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/MealLogger.tsx \
        frontend/src/components/MealLogger.test.tsx \
        docs/qa/2026-11-23-stale-preview-guard.md \
        docs/opencode-meal-logging-backlog.md
git commit -m "fix: bind meal confirmation to the reviewed preview"
```
