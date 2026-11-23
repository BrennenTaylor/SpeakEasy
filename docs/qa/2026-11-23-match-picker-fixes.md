# Match Picker Hardening QA Steps

Date: 2026-11-23

## Scope

These steps verify two hardening fixes on top of the food match picker:

1. An overlong USDA serving label (or any single USDA record that cannot produce a schema-valid match) no longer fails the whole `POST /api/meals/interpret` request with a 500. The label is truncated to the schema cap; a genuinely unusable record degrades to one dropped card plus a `USDA record was unusable` warning while every other group still resolves.
2. Double-tapping **Add selected foods** no longer re-creates the same foods. After a fully successful batch the picker clears (no button left to tap). After a partial failure the per-item failures are reported, and a retry skips foods that were already saved, creating only the failed ones.

The companion fix to `docs/qa/2026-11-20-ai-meal-interpretation.md` (stale `candidates` field, per-card **Add** buttons, duplicate warnings, retired warning text) is documentation only; its steps now match the current UI and are covered by the automated gate below.

Run commands from the repository root.

## 1. Automated regression tests (primary evidence)

The overlong-label case needs a synthetic USDA record, so the regression tests are the primary verification:

```bash
cd backend && .venv/bin/pytest -q tests/test_nutrition_lookup.py
cd ../frontend && npx vitest run src/components/MealCandidates.test.tsx
```

Expected: all tests pass, including:

- `test_overlong_serving_label_is_truncated_to_schema_cap` — a 120-char portion modifier produces a 100-char serving label; the sibling USDA match and the web match still resolve.
- `test_unusable_usda_record_drops_while_sibling_matches_survive` — a record whose view fails schema validation drops with `USDA record was unusable` while the good sibling and web match survive.
- `test_long_name_and_brand_are_truncated_to_schema_cap` — 250-char description and brand owner truncate to the 200-char schema cap.
- `clears the picker after a successful add so a second Add creates nothing`
- `retries only the foods that failed and never re-creates saved ones`

## 2. Start the app

```bash
nvm use
make setup
make migrate
make dev-backend    # terminal 1, http://127.0.0.1:8000
make dev-frontend   # terminal 2, http://localhost:5173
```

## 3. Live check: overlong labels cannot 500 the request

USDA rarely serves a 120-char serving label, so live QA proves the request path is healthy rather than the extreme case itself:

1. In **Describe your meal**, type `apple` and click **Find foods**.
2. Expected: groups render with their ranked match cards, no red 500 alert, and every visible card's serving label fits on the card.
3. Stop the backend (`Ctrl-C` in terminal 1), click **Find foods** again, and confirm the red alert is the connection error, not a 500. Restart the backend.

## 4. Live check: a successful Add clears the picker

1. Record the food count:

   ```bash
   backend/.venv/bin/python -c "import sqlite3; c=sqlite3.connect('backend/data/app.db'); print('foods, meals =', c.execute('select (select count(*) from foods), (select count(*) from meals)').fetchone())"
   ```

2. Interpret `apple` (or any meal), select complete matches, and click **Add selected foods**.
3. Expected: the foods enter **Meal review**, and the **Suggested foods** section clears: no match cards and no **Add selected foods** button remain, so a second tap cannot re-create anything. **Find foods** still works for a fresh search.
4. Re-run the count command. Expected: `foods` increased by exactly the number of added foods, `meals` unchanged. **Confirm** saves the meal as usual.

## 5. Live check: failed Add keeps the picker and reports the failure

1. Interpret a meal with at least one group and let the matches render.
2. Stop the backend, then click **Add selected foods**.
3. Expected: a red alert reports the failure per food and says retrying adds only the failed foods; the match cards and the **Add selected foods** button remain.
4. Restart the backend and click **Add selected foods** again. Expected: the foods are created and enter **Meal review**, the alert clears, and the picker clears. The food count from step 1 increases by exactly the number of foods in the draft (no duplicates from the failed attempt).

A mid-batch failure (one food saved, one failed) is timing-dependent and not reliably reproducible by hand; the automated test `retries only the foods that failed and never re-creates saved ones` covers that path.

## Automated gate

```bash
nvm use
make check
```

Expected: backend lint/format/mypy/pytest (68+ tests), frontend lint/format/typecheck/vitest (70+ tests), migration round trip, and production build all pass.
