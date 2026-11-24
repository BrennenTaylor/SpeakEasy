# QA: stale preview guard (2026-11-23)

## What changed

Changing the meal description, item list, or quantity now clears the visible totals and disables Confirm immediately. A preview result is applied only if it belongs to the draft currently on screen. A late success from an older quantity cannot re-enable Confirm, and a late failure from an older draft cannot show an error for the current draft.

## Automated checks

From the repository root:

```bash
cd frontend && npm run test -- src/components/MealLogger.test.tsx
make check
```

The focused suite includes regression coverage for:

- Confirm staying disabled with no totals while a preview for the edited quantity is pending.
- A stale preview failure leaving the current totals and Confirm state intact.
- Add and remove mutations dropping stale preview responses.

## Manual steps

Use the running app with the backend and frontend up.

1. Create or choose a saved food with known nutrition (for example, the existing Costco nuggets fixture) and add it to a meal.
2. Wait for the preview totals to appear and confirm that Confirm becomes enabled.
3. Change the quantity from `1` to `2` while throttling or delaying the preview response (browser DevTools network throttling works).
4. Confirm that the old totals disappear and Confirm is disabled as soon as the quantity changes.
5. Tap Confirm before the new preview resolves. No meal should appear in Recent meals, and the draft should stay editable.
6. Let the fresh preview finish. Confirm that recalculated totals appear and Confirm becomes enabled.
7. Tap Confirm. The saved meal should show quantity `2` and totals matching two servings.

## Failure and recovery

1. Start a preview, then stop the backend before it responds.
2. Confirm that the error banner appears, totals stay cleared, and Confirm is disabled.
3. Restart the backend, edit the quantity again, and confirm that a fresh preview restores totals and enables Confirm.

## Limitations

This change does not address serving-basis conversion (backlog task 2) or idempotent saves/retry deduplication (backlog task 6).
