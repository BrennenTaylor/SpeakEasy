# QA: missing model values no longer cause 503 (2026-11-23)

## What changed

OpenAI sometimes returns empty strings for numeric fields when a value is missing, for example `serving_grams: ""`, `fiber_g: ""`. The strict candidate schema rejected the whole response, and the interpretation endpoint returned `503 AI interpretation is unavailable`.

Blank numeric values and blank source URLs are now treated as missing. Candidates stay in the picker, the affected fields are listed under **Missing**, and no zero or guessed value is substituted.

## Automated checks

```bash
make check
```

Expected: backend pytest 71 passed, frontend vitest 73 passed, lint, format, mypy, typecheck, migration round trip, and production build all pass.

Focused regression tests:

```bash
cd backend && .venv/bin/pytest -q tests/test_interpretation_schemas.py tests/test_nutrition_lookup.py
cd frontend && npm run test -- src/api/interpretation.test.ts src/components/MealCandidates.test.tsx src/components/MealLogger.test.tsx
```

- `test_blank_model_values_become_missing` failed before the fix with four `ValidationError`s and now passes.
- `test_web_card_marks_missing_serving_grams_and_macros` failed before the fix because `None` was rejected and now passes.
- The client test rejects a `null` `serving_grams` before the fix and accepts it now.
- The picker test failed before the fix with the rendered text `5 pieces ( g)` and now shows `5 pieces` with the missing fields listed.

## Live checks (requires OpenAI and USDA keys)

1. Start or restart both servers and confirm the keys are configured:

   ```bash
   make dev-backend
   make dev-frontend
   ```

2. In the browser, enter `sushi platter with miso soup` and click **Find foods**.

   - Expected: status `200` and at least one food group. No 503 error banner.
   - The response body has `groups` and `warnings`; there is no `candidates` field.

3. Look at a match card whose source data was incomplete.

   - Expected: the serving line shows the serving label without an empty `( g)` suffix.
   - Expected: missing values appear as `—` in the macro grid and are named under **Missing**, for example `serving_grams, fiber_g, sugar_g`.
   - Forbidden: `0`, `0.0000`, or any invented number in a field listed as missing.

4. Verify **Add selected foods** is hidden while any selection is incomplete. Click **Complete with a label** on that card.

   - Expected: the create-food form opens with the known fields pre-filled and missing numeric fields blank.
   - Enter the missing serving grams and any missing macros, save the food, then add the other complete selections and click **Confirm**.
   - Expected: the meal saves with the user-supplied values marked `user_label` / low confidence, and its source URL is retained if the match had one.

5. Repeat step 2 with `chick fil a sandwich` and confirm complete cards still add normally.

6. Confirm the no-key path from the earlier runbook is unchanged: without `APP_OPENAI_API_KEY`, **Find foods** reports `AI interpretation is not configured` and manual food logging still works.

## If a 503 still appears

Open the browser Network tab and inspect `POST /api/meals/interpret`:

- `AI interpretation is unavailable` with an `AIServiceError` cause mentioning `ReadTimeout` means the provider exceeded the 20-second budget from the previous fix.
- A `ValidationError` naming a candidate field means another model value shape reached the schema. Record the full field name and value from the backend terminal and report it; do not add an ad-hoc default for it.

Manual food search and logging remain available in either case.

## Limitations

- `quantity` remains required because a meal group needs an amount; a blank quantity from the model still fails interpretation. No sample response has produced this, but it is not yet handled.
- Provider latency and web results vary, so the exact missing fields in step 3 depend on the live response.
- No API keys are committed or exposed to the browser.
