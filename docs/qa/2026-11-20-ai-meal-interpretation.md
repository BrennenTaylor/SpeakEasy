# AI Meal Interpretation QA Steps

## Scope

These steps validate the AI-assisted meal entry flow: a description is interpreted, foods are looked up from real sources, the user reviews candidates, and a meal is saved only after **Confirm**.

Run every command from the repository root. The paths are relative and work on `main` or any branch that contains these changes. Tests mock all providers; the manual steps below use live services.

## 1. Accounts and keys

1. Create a **separate OpenAI API account** at <https://platform.openai.com/api-keys>. ChatGPT Plus does not provide backend API access. Set a monthly billing limit of about $5–10; the default model is `gpt-6-luna`, and the built-in web search bills to this same account.
2. Create a free USDA FoodData Central key at <https://fdc.nal.usda.gov/api-key-signup/>. `DEMO_KEY` works but is limited to 30 requests/hour and commonly returns HTTP 429 during QA.
3. Copy the example file and add the keys:

   ```bash
   cp backend/.env.example backend/.env
   ```

   Uncomment and fill in:

   ```dotenv
   APP_OPENAI_API_KEY=your-openai-api-key
   APP_USDA_API_KEY=your-usda-api-key
   ```

   Never commit `backend/.env`.

## 2. Start the app

```bash
nvm use
make setup
make migrate
make dev-backend    # terminal 1, http://127.0.0.1:8000
make dev-frontend   # terminal 2, http://localhost:5173
```

Open <http://localhost:5173> in a 390 px-wide viewport. Verify the backend with `curl -s http://localhost:8000/api/meals`; it should return `[]` or an existing list, not a 500.

## 3. Interpret a real meal

1. In **Describe your meal**, type `chick fil a sandwich`.
2. Click **Find foods**. Do not expect a call on every keystroke.
3. Expected states, in order: `Finding foods…`, then one or more candidate cards. No card should appear before the button is clicked.
4. On the Chick-fil-A candidate, verify:
   - A source badge: `USDA · high confidence` when FDC supplied all seven values, `USDA · low confidence` for an incomplete FDC record, or `Web · low confidence` when the web fallback was used.
   - A serving of `1 sandwich` / `187 g` for FDC food `170790`.
   - All seven macro values are present, not `—`: calories, protein, carbs, fat, fiber, sugar, sodium.
   - A `source_url` link on the card or in the saved food when inspected via `curl -s http://localhost:8000/api/foods`.

   For FDC `170790`, the per-100 g values `249 kcal`, `16.28 g protein`, `20.89 g carbs`, `11.19 g fat`, `1.4 g fiber`, and `753 mg sodium` scale by `1.87` to approximately `465.63`, `30.44`, `39.06`, `20.93`, `2.62`, and `1408.11`. FDC does not provide sugar for this item. If neither source supplies sugar, the card shows `Missing: sugar_g`, has no **Add** button, and offers **Complete with a label**. Enter the sugar value from the menu/label to continue; the saved food then has `source: "user_label"`, `confidence: "low"`, and retains its `source_url`.

5. Change the candidate's quantity from `1.0000` to `2`. Expected: the **Meal review** preview doubles every macro value. The browser does not compute totals; the preview comes from backend `Decimal` arithmetic.
6. Click **Confirm**. Expected: the draft clears, **Recent meals** gains the entry, and a new meal appears in `curl -s http://localhost:8000/api/meals` with `raw_input` `chick fil a sandwich`. Its item keeps the serving, `source`, `source_url`, `confidence`, and macro snapshot from the candidate.

## 3b. Reject USDA matches for the wrong food or brand

This case prevents FDC `170303` (**Chick-fil-A Chick-n-Strips**, `4 pieces` / `201 g`) and FDC `1894006` (**Blount Seafood MAC & CHEESE**, `0.5 cup` / `113 g`) from overwriting a correct branded web result.

1. In **Describe your meal**, type `chick fil a 12 count nuggets and mac and cheese`.
2. Click **Find foods**.
3. Expected: two `Web · low confidence` cards and two warnings reading `No USDA match found`.
4. The nugget card should show `12 nuggets` / `170 g` and `380` calories. It must **not** show `4 pieces`, `201 g`, or `Chick-n-Strips` values.
5. The mac and cheese card should show `Medium` / `227 g` and `450` calories. It must **not** show `0.5 cup` or `113 g`. This expectation does not depend on the model populating the card's `brand` field: with an empty brand, a USDA **Branded** record is accepted only when the food name shares at least one word with the record's `brandOwner`/`brandName`, so the Blount entry is rejected either way.
6. Spot-check that each card's `source_url` points to the Chick-fil-A nutrition page. Exact label wording can vary between model runs; the serving grams and macros should match the linked page.

## 4. Prove interpretation itself writes nothing

Before clicking **Add** or **Confirm**, capture the counts:

```bash
backend/.venv/bin/python -c "import sqlite3; c=sqlite3.connect('backend/data/app.db'); print('foods, meals =', c.execute('select (select count(*) from foods), (select count(*) from meals)').fetchone())"
```

Call the endpoint directly:

```bash
curl -s -X POST http://localhost:8000/api/meals/interpret \
  -H 'content-type: application/json' \
  -d '{"description":"chick fil a sandwich"}'
```

Expected: a JSON object with `candidates` and `warnings`. Run the same Python count command. Expected: **exactly the same** `foods, meals` pair. Interpretation is read-only; only **Add** saves a `Food` and only **Confirm** saves a `Meal`.

## 5. Exercise web-search fallback

1. Describe a real but uncommon item, for example `McDonald's McLobster sandwich`, and click **Find foods**.
2. Expected: a warning such as `USDA lookup unavailable`, `No USDA match found`, or `USDA record was incomplete; used web source`.
3. Expected: a `Web · low confidence` card with a source URL. If all seven values are present, it can be added; if not, it shows its `missing_fields` and the label form.
4. Record the URL and spot-check that the displayed values match the linked page. Do not accept a card with no source URL and model-supplied numbers.

## 6. No-key and outage behavior

1. Remove or comment out `APP_OPENAI_API_KEY` in `backend/.env` (and `unset APP_OPENAI_API_KEY` in the shell if it was exported). Restart `make dev-backend`.
2. Click **Find foods** again. Expected: a red alert containing `Server responded with 503`.
3. Verify the backend's exact message:

   ```bash
   curl -s -X POST http://localhost:8000/api/meals/interpret \
     -H 'content-type: application/json' -d '{"description":"lunch"}'
   ```

   Expected: `{"detail":"AI interpretation is not configured"}`. If a key is present but OpenAI fails or times out, the expected body is `{"detail":"AI interpretation is unavailable"}`. Both produce no writes.

4. Keep the backend running with no key and log a meal manually:
   - Use **Create a food from a label** or **Search foods**, add a food, change its quantity, and click **Confirm**.
   - Expected: preview and confirmation still work, **Recent meals** updates, and `curl -s http://localhost:8000/api/meals` shows the new meal.
5. Restore the key in `backend/.env` and restart the backend when finished.

## 7. Automated gate

```bash
nvm use
make check
```

Expected: backend lint/format/mypy/pytest, frontend lint/format/typecheck/vitest, migration round trip, and production build all pass.
