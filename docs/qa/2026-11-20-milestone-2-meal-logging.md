# Milestone 2 QA Steps

## Scope

- PR: https://github.com/BrennenTaylor/SpeakEasy/pull/1
- Branch: `m2-meal-logging`
- These steps validate the Milestone 2 meal-logging flow. Re-run them after any change to food entry, preview totals, confirmation, recent meals, or food editing.
- Typing a meal sentence stores the text as `raw_input`; Milestone 2 does **not** parse it with AI. You still search for or create the foods and attach them manually.

## Automated gate

From the repository root:

```bash
cd /home/brtayl/.local/share/opencode/worktree/8e66d7/m2-meal-logging
nvm use
make check
```

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

Expected: the form closes, the food appears in **Meal review**, and the totals show `250` calories plus the seven entered macro values.

## Search by alias and verify backend scaling

1. In **Search foods**, enter `nuggets` and click **Search**.
2. Expected: `Test Nuggets` appears with `250 kcal`.
3. Click **Add** so there are two independent rows.
4. Expected totals with both rows at quantity `1`, in order calories/protein/carbs/fat/fiber/sugar/sodium:

   `500 / 20 / 40 / 20 / 2 / 4 / 600`

5. Change the **first** row's quantity from `1` to `2`.
6. Expected totals:

   `750 / 30 / 60 / 30 / 3 / 6 / 900`

This confirms the backend scales the stored label values; the browser does not compute totals.

## Verify confirm gating and no early writes

1. Before clicking **Confirm**, check **Recent meals** — the count must not change from previewing.
2. Clear the description textarea.
3. Expected: **Confirm** becomes disabled. Clicking it saves nothing.
4. Re-enter the description.
5. Expected: totals reappear and **Confirm** becomes enabled.
6. Click **Confirm**.

Expected: the draft clears and **Recent meals** gains one entry with the description and `750` calories plus the matching macros.

## Verify saved-food editing and snapshot immutability

1. Search for `nuggets` again.
2. Click **Edit** on `Test Nuggets`.
3. Change Calories from `250` to `999`.
4. Click **Save food**.

Expected:

- Search results show `999 kcal` for the edited food.
- The already logged **Recent meal** still shows `750` calories and the original macro totals.
- No historical meal values change.

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
