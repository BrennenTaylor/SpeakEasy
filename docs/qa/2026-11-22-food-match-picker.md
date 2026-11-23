# Food Match Picker QA Steps

Date: 2026-11-22

## Scope

These steps validate the cumulative food-match-picker feature: AI interpretation returns one **group** per interpreted food, each group holds ranked, source-backed **matches**, the user selects one match per group, and nothing is saved until **Add selected foods** and then **Confirm**.

Design spec: `docs/superpowers/specs/2026-11-22-food-match-picker-design.md`. The earlier flow is covered by `docs/qa/2026-11-20-ai-meal-interpretation.md`; note that the interpret response now returns `groups` (with `matches`), not `candidates`.

Run every command from the repository root. Tests mock all providers; the manual steps below use live services, so exact wording and values can vary between model runs. Reference values below come from the linked source pages — spot-check against the page, not against this document.

## Setup

### 1. Accounts and keys

1. You need an OpenAI API key (from <https://platform.openai.com/api-keys>, not ChatGPT Plus) and a free USDA FoodData Central key (<https://fdc.nal.usda.gov/api-key-signup/>). `DEMO_KEY` works for USDA but is limited to 30 requests/hour and commonly returns HTTP 429 during QA.
2. Copy the example file and fill in the keys:

   ```bash
   cp backend/.env.example backend/.env
   ```

   Uncomment and set:

   ```dotenv
   APP_OPENAI_API_KEY=your-openai-api-key
   APP_USDA_API_KEY=your-usda-api-key
   ```

   Never commit `backend/.env`. Keys stay server-side; the browser never sees them.

### 2. Start the app

```bash
nvm use
make setup
make migrate
make dev-backend    # terminal 1, http://127.0.0.1:8000
make dev-frontend   # terminal 2, http://localhost:5173
```

Open <http://localhost:5173> in a 390 px-wide viewport. Verify the backend with `curl -s http://localhost:8000/api/meals`; it should return `[]` or an existing list, not a 500.

### 3. What the picker shows, and what "incomplete" means

- Each group has a heading (the AI's food label) and a `Qty` value. Matches render as radio-style cards, best first.
- Each card shows: a source badge (`USDA · high confidence`, `USDA · low confidence`, or `Web · low confidence`), the source record's name and brand, serving label and grams, all seven macros (calories, protein, carbs, fat, fiber, sugar, sodium), a `Rank N: …` line with reasons such as `brand match`, `name match`, `complete macros`, `USDA source` / `web source`, and a **View source** link when a source URL exists.
- A match is **incomplete** when at least one of the seven macros is missing, or when it is the URL-less draft (missing `source_url` too). Missing values display as `—`, the card lists `Missing: <fields>`, and the match **cannot be added directly**. The only path is **Complete with a label**, which opens the pre-filled create-food form; the saved food then becomes `source: "user_label"`, `confidence: "low"`, and keeps the match's `source_url` (or `null` for the URL-less draft).
- Each group initially shows at most **3** matches. When a group has more, a **Show more (N)** button reveals the rest. This is a display limit only, not a cap on matches.
- **Add selected foods** appears only when **every** group's selected match is complete. If any selection is incomplete, the button is hidden — there is no way to save a partial meal.
- Interpretation writes nothing, and selecting or reviewing matches saves nothing. **Add selected foods** creates `Food` rows; only **Confirm** creates a `Meal`. (The manual label form also creates foods, but only on explicit submit.) Use this count check whenever a step says "no writes":

  ```bash
  backend/.venv/bin/python -c "import sqlite3; c=sqlite3.connect('backend/data/app.db'); print('foods, meals =', c.execute('select (select count(*) from foods), (select count(*) from meals)').fetchone())"
  ```

## 1. Interpret the Chick-fil-A meal

1. Record the `foods, meals` counts with the command above.
2. In **Describe your meal**, type `chick fil a 12 count nuggets and mac and cheese`.
3. Click **Find foods**. No cards may appear before the click, and there is no call on every keystroke.
4. Expected states, in order: `Finding foods…`, then match groups. Warnings (if any) render as amber text above the groups.
5. Prove interpretation itself writes nothing. Call the endpoint directly:

   ```bash
   curl -s -X POST http://localhost:8000/api/meals/interpret \
     -H 'content-type: application/json' \
     -d '{"description":"chick fil a 12 count nuggets and mac and cheese"}'
   ```

   Expected: a JSON object with `groups` and `warnings` (no `candidates` field). Re-run the count command: **exactly the same** `foods, meals` pair.

## 2. Verify separate groups for nuggets and mac

1. After step 1, expected: **two** groups under **Suggested foods** — one for the nuggets, one for the mac and cheese — each with its own heading and `Qty` value.
2. Each group has its own radio selection; selecting a match in one group must not change the other group's selection.
3. Forbidden: one merged group, one food silently standing in for both, or a group for a food you did not describe.

## 3. Verify ranked matches with full provenance

The Chick-fil-A groups usually contain only the web match (see step 4), so use a common food to see several ranked matches:

1. In **Describe your meal**, type `apple` (or `banana`) and click **Find foods**.
2. Expected: a group with several `USDA` matches plus a `Web · low confidence` match, ordered by rank. Verify on every visible card:
   - A source badge as described in Setup §3.
   - Name and brand from the **source record** (for USDA, the FDC description and brand owner), not just the AI's wording.
   - Serving label and grams, e.g. `1 medium (182 g)`.
   - All seven macro rows; missing ones show `—`, never `0`.
   - A `Rank N: …` line with at least one reason (`complete macros`, `USDA source`, `web source`, and `brand match` / `name match` where applicable). Ranks are 1-based and increase down the group.
   - A **View source** link: USDA cards link to `https://fdc.nal.usda.gov/fdc-app.html#/food-details/<id>/nutrients`; the web card links to the page the model cited. Open one of each and spot-check that the displayed serving and macros match the linked page.
3. If any card shows `Missing: …`, verify it is flagged incomplete and offers **Complete with a label** when selected (step 7 covers the full completion flow). If no card in this run is incomplete, that is fine — step 7 exercises it deliberately.
4. Forbidden: a card with model-supplied numbers and no source URL presented as addable, zero-filled missing nutrients, or a match without rank/provenance information.

## 4. Select the correct Chick-fil-A matches over wrong USDA identities

This case prevents FDC `170303` (**Chick-fil-A Chick-n-Strips**, `4 pieces` / `201 g`) and FDC `1894006` (**Blount Seafood MAC & CHEESE**, `0.5 cup` / `113 g`) from being chosen for the wrong foods.

1. Re-enter `chick fil a 12 count nuggets and mac and cheese` and click **Find foods**.
2. Expected: the nuggets group contains the Chick-fil-A **web** match — reference values `12 nuggets` / `170 g` and `380` calories — and the mac group contains the Chick-fil-A web mac and cheese — reference values `Medium` / `227 g` and `450` calories. (Live values follow the linked Chick-fil-A page and can vary between runs.)
3. What is pre-selected depends on the model run:
   - When the AI fills the `brand` field, the identity gate drops the brand word from the food tokens, so "nuggets" has no overlap with Chick-n-Strips and the record is rejected; both groups then show a `No USDA match found` warning and the web match is rank 1 and pre-selected. Blount is rejected either way: with an empty brand, a **Branded** record is admitted only when the food name shares a word with its `brandOwner`/`brandName`, and "mac and cheese" shares none with "Blount Seafood".
   - When the AI leaves `brand` empty, the shared "Chick-fil-A" word can let the Chick-n-Strips record through the gate. It may then appear as a USDA card and even be pre-selected (source is a ranking tiebreaker). This is exactly what the picker is for: **click the radio on the Chick-fil-A web match in the nuggets group** so the wrong identity is not what gets saved.
4. In every run, finish this step with the Chick-fil-A web match selected in **both** groups. Verify each selected card's **View source** link points to a Chick-fil-A nutrition page, and that the serving grams and macros match that page.
5. Forbidden: saving a meal whose selected match shows `Chick-n-Strips`, `4 pieces`, `201 g`, Blount Seafood, `0.5 cup`, or `113 g` for this meal. The user's explicit selection must win over any ranking.

## 5. Use Show more

1. Return to the multi-match group from step 3 (re-interpret `apple` if needed). Any group with more than 3 matches shows at most 3 cards plus a **Show more (N)** button, where N is the number of hidden matches.
2. Click **Show more (N)**. Expected: all remaining matches appear in rank order, the button disappears, and the current selection is unchanged.
3. Select one of the newly revealed matches. Expected: the radio selection moves to it, and it is the match that **Add selected foods** will save.
4. Groups with 3 or fewer matches (typically the Chick-fil-A groups) correctly show no **Show more** button.
5. Forbidden: matches beyond the initial 3 being dropped from the response, or the display limit changing what the API returned (`groups[].matches` in the curl output of step 1 contains every match).

## 6. Add selected foods, Confirm, and verify saved provenance

1. With the two Chick-fil-A web matches selected (step 4), record the `foods, meals` counts.
2. Click **Add selected foods**. Expected: both foods enter **Meal review** with their groups' quantities, and the preview totals appear. The browser does not compute totals; the preview comes from backend `Decimal` arithmetic.
3. Re-run the count check. Expected: `foods` increased by 2, `meals` **unchanged**. No meal exists yet.
4. Inspect the saved foods:

   ```bash
   curl -s http://localhost:8000/api/foods
   ```

   Expected: the two new foods keep the selected matches' `name`, `brand`, `serving_label`, `serving_grams`, `source: "web_search"`, `source_url` (the Chick-fil-A page), `confidence: "low"`, and all seven macro values.
5. Optionally change a quantity in **Meal review** (e.g. `1` → `2`); the preview doubles that food's contribution.
6. Click **Confirm**. Expected: the draft clears, **Recent meals** gains the entry, and `meals` increases by exactly 1.
7. Verify the meal snapshot:

   ```bash
   curl -s http://localhost:8000/api/meals
   ```

   Expected: the new meal has `raw_input` `chick fil a 12 count nuggets and mac and cheese`, and **each** item's snapshot retains the selected source, `source_url`, `confidence`, serving, and macro values from the saved food.
8. Forbidden: a meal saved before **Confirm**, a partial meal with only one of the two foods, or a snapshot that lost `source_url`/`confidence` or substituted different values.

## 7. Incomplete matches and the URL-less draft

### 7a. An incomplete match with a source URL

1. In **Describe your meal**, type `chick fil a sandwich` and click **Find foods**.
2. Expected: a USDA match for FDC `170790` (`1 sandwich` / `187 g`). FDC typically omits sugar for this item, so the card shows `Missing: sugar_g`, a `USDA · low confidence` badge, and `—` for sugar. (If your run returns all seven values, use any other card that shows `Missing:` — the flow is identical.)
3. Select that incomplete match. Expected: **Add selected foods** is **hidden** (not merely disabled), and the selected card offers **Complete with a label**. If another group in the same run has a complete selection, the button stays hidden while any selection is incomplete — a partial meal can never be saved.
4. Click **Complete with a label**. Expected: the **Create a food from a label** form opens pre-filled with the match's name, brand, serving, and known macros; **Confidence** is set to `Low`; the match's `source_url` is carried along (hidden field). Missing fields are empty, not zero.
5. Enter the missing value(s) from the linked menu/label (for `170790`, the sugar grams from the Chick-fil-A page), then click **Create food**. Expected: the food enters **Meal review**.
6. Verify via `curl -s http://localhost:8000/api/foods`: the new food has `source: "user_label"`, `confidence: "low"`, and **retains** the match's `source_url` (the FDC page for `170790`).
7. Forbidden: an incomplete match being added directly, missing values saved as `0`, or the saved food keeping `usda_fdc`/`web_search` source after label completion.

### 7b. The URL-less draft

When the AI returns no valid `http(s)` URL and USDA finds no usable match, the group keeps exactly one incomplete, URL-less web draft for manual completion.

1. Describe something with no published nutrition, for example `homemade mystery casserole from a family recipe`, and click **Find foods**. Model output varies; if the group instead shows a web card **with** a URL, try another obscure description until you get the draft.
2. Expected draft card: `Web · low confidence`, **no View source link**, every macro `—`, and `Missing: source_url, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg`. Warnings include `Web result has no valid source_url` plus a USDA warning such as `No USDA match found` (or a lookup failure such as `USDA lookup returned 429` when rate-limited).
3. Select the draft. Expected: **Add selected foods** stays hidden; **Complete with a label** appears. The draft's numbers are never authoritative — there is nothing to add directly.
4. Click **Complete with a label**, fill in all seven values from your own label or recipe, and click **Create food**.
5. Verify via `curl -s http://localhost:8000/api/foods`: the saved food has `source: "user_label"`, `confidence: "low"`, and `source_url: null`.
6. Forbidden: the draft being addable without a label, model-invented numbers being saved as sourced data, or a fabricated `source_url` appearing on the saved food.

## 8. Manual logging still works without an AI key

1. Remove or comment out `APP_OPENAI_API_KEY` in `backend/.env`, and `unset APP_OPENAI_API_KEY` in the shell if it was exported. Restart `make dev-backend`.
2. Click **Find foods** with any description. Expected: a red alert containing `Server responded with 503`, and no writes (count check unchanged).
3. Verify the backend's exact message:

   ```bash
   curl -s -X POST http://localhost:8000/api/meals/interpret \
     -H 'content-type: application/json' -d '{"description":"lunch"}'
   ```

   Expected: `{"detail":"AI interpretation is not configured"}`. (With a key present but OpenAI failing, the body is `{"detail":"AI interpretation is unavailable"}`.)
4. Keep the backend running with no key and log a meal manually:
   - Use **Search foods** (e.g. `nuggets` — foods saved in earlier steps appear), click **Add** on a result, adjust its quantity in **Meal review**, and click **Confirm**. Alternatively use **Create a food from a label**.
   - Expected: search, preview, and confirmation all work, **Recent meals** updates, and `curl -s http://localhost:8000/api/meals` shows the new meal with its snapshot.
5. Restore the key in `backend/.env` and restart the backend when finished.

## Automated gate

```bash
nvm use
make check
```

Expected: backend lint/format/mypy/pytest (55+ tests), frontend lint/format/typecheck/vitest (62+ tests), migration round trip, and production build all pass.
