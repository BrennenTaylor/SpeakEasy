# Milestone 2 QA Steps

## Scope

- PR: https://github.com/BrennenTaylor/SpeakEasy/pull/1
- Branch: `m2-meal-logging`
- These steps validate the Milestone 2 meal-logging flow. Re-run them after any change to food entry, preview totals, confirmation, recent meals, or food editing.
- Typing a meal sentence stores the text as `raw_input`; Milestone 2 does **not** parse it with AI. You still search for or create the foods and attach them manually.

## Automated gate

From the root of any checkout that contains these changes (the `m2-meal-logging` branch, or `main` after merge):

```bash
nvm use
make check
```

The commands are checkout-agnostic. If `npm run lint` falls back to `/usr/bin/eslint` and reports `Cannot find module 'mkdirp'`, that checkout's `frontend/node_modules` install is incomplete; run `npm ci` in `frontend/` there first.

Expected:

- lint/format/mypy/typecheck pass
- 28 backend tests pass
- 45 frontend tests pass
- migrations run `head -> base -> head`
- Vite production build succeeds

## Start the app

```bash
make setup
make dev-backend    # terminal 1
make dev-frontend   # terminal 2
```

Open http://localhost:5173 in a browser viewport set to **390 px wide**.

## Create a food from a label

1. Under **What did you eat?**, type: `two servings of test nuggets`.
2. Click **Create a food from a label**.
3. Fill in:

| Field | Value |
| --- | --- |
| Name | `Test Nuggets` |
| Brand | `Test Brand` |
| Serving label | `1 cup` |
| Serving grams | `100` |
| Calories | `250` |
| Protein | `10` |
| Carbs | `20` |
| Fat | `10` |
| Fiber | `1` |
| Sugar | `2` |
| Sodium | `300` |
| Confidence | `High` |
| Aliases | `nuggets, chicken nuggets` |

4. Click **Create food**.

Expected: the form closes, the food appears in **Meal review**, and the totals show seven rows: calories `250.0000`, protein `10.0000`, carbs `20.0000`, fat `10.0000`, fiber `1.0000`, sugar `2.0000`, and sodium `300.0000`.

## Search by alias and verify backend scaling

1. In **Search foods**, enter `chicken nuggets` and click **Search**. This text is an alias, not part of the name `Test Nuggets`, so a result proves alias matching works.
2. Expected: `Test Nuggets` appears with `250.0000 kcal`.
3. Click **Add** so there are two independent rows.
4. Expected totals with both rows at quantity `1`, in order calories/protein/carbs/fat/fiber/sugar/sodium:

   `500.0000 / 20.0000 / 40.0000 / 20.0000 / 2.0000 / 4.0000 / 600.0000`

5. Change the **first** row's quantity from `1` to `2`.
6. Expected totals:

   `750.0000 / 30.0000 / 60.0000 / 30.0000 / 3.0000 / 6.0000 / 900.0000`

This confirms the backend scales the stored label values; the browser does not compute totals.

## Verify confirm gating and no early writes

1. Before previewing, run `curl -s http://localhost:8000/api/meals`. Expect `[]`, or the list of meals already present from earlier runs.
2. Add foods and change quantities as above, but do not click **Confirm**.
3. Run `curl -s http://localhost:8000/api/meals` again. Expect exactly the same list as step 1. The browser alone cannot prove this because **Recent meals** is not refetched during preview.
4. Clear the description textarea.
5. Expected: **Confirm** becomes disabled. Clicking it saves nothing.
6. Re-enter the description.
7. Expected: totals reappear and **Confirm** becomes enabled.
8. Click **Confirm**.
9. Run `curl -s http://localhost:8000/api/meals` again. Expected: exactly one new meal, with `raw_input` matching the description and `totals.calories` equal to `750.0000`. **Recent meals** also gains the entry.

## Verify saved-food editing and snapshot immutability

1. Search for `nuggets` again.
2. Click **Edit** on `Test Nuggets`.
3. Change Calories from `250` to `999`.
4. Click **Save food**.
5. Click **Search** again to refresh the result row. Expected: `Test Nuggets` now shows `999.0000 kcal`.
6. In a second terminal, run `curl -s http://localhost:8000/api/meals`. Expected: the meal confirmed earlier still has `totals.calories` equal to `750.0000`, and its item still has `calories` equal to `250.0000`, even though the saved food now has `999.0000`.
7. Optional: add the edited food to a new draft, confirm it, and check that the new meal uses `999.0000` while the old meal remains `250.0000`.

This reads the server's stored snapshots, so it cannot pass on stale browser state.

Note: after saving an edit, the edited food is also added to the current draft. Remove it from **Meal review** if it gets in the way.

## Error-state check

1. Stop the backend process.
2. Click **Search** or **Try again**.
3. Expected: a red alert appears, such as `Server responded with 502` or `Could not reach the server`.
4. Restart the backend and search again.
5. Expected: results return and the alert clears.

## Mobile layout check

At a 390 px viewport, confirm:

- no horizontal scrolling
- Add, Edit, Remove, and Confirm buttons remain visible
- long food names and timestamps wrap or truncate without breaking the layout
