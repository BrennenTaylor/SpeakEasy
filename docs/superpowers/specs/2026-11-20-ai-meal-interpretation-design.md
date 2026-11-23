# AI Meal Interpretation — Design

## Intent and why

The user wants to type a normal sentence — "chick fil a sandwich and a coke" — and have the app go find the nutrition data instead of making them search and type labels first. Milestone 2 built the save/confirm/snapshot machinery and deliberately deferred AI interpretation. This change adds that interpretation step on top of the existing `Food` and `Meal` tables, plus a real data lookup so the numbers are sourced rather than guessed.

Success looks like: describe a meal, see candidate foods with their source and confidence, adjust a quantity, Confirm, and find the meal in Recent Meals with all seven macros and a source attached to every item. Typing a description still works with no AI key, and **no meal** is written until Confirm. Saving a candidate as a `Food` when the user adds it is allowed and mirrors the existing manual flow, where creating a food from a label also writes before the meal is confirmed.

## Goals

1. Turn a free-text meal description into a short list of candidate foods.
2. Get nutrition values from a real source: USDA FoodData Central first, web search as a fallback.
3. Preserve source, source URL, units, and confidence on the candidate, the saved food, and the meal snapshot.
4. Let the user review and adjust candidates, then Confirm before any meal is committed.
5. Keep today's manual search-and-label flow working with no AI service or keys.
6. Stay inside the approved budget (user approved paid OpenAI API usage, capped at roughly $5–10/month; expected spend is under $1/month).

## Non-goals

- Recipe description or recipe/PDF upload. That is a later change using the same lookup layer.
- Photo upload, nutrition insights, user accounts, or insulin-dosing guidance.
- Letting the model compute or output meal totals.
- Treating model-remembered numbers as authoritative without a source URL.
- Fabricating a zero for a nutrient the source did not report.

## Anti-goals (what would make this a failure)

- A logged meal whose calories came from the model's memory with no cited source.
- A meal written to the database before the user pressed Confirm. (`Food` rows may be written earlier, exactly as the manual label flow does today.)
- The manual path breaking when the AI provider is down or unconfigured.
- An API key or provider URL reachable from the browser.

## Constraints

- All rules in `AGENTS.md`, especially: never invent nutritional data; never let the LLM perform authoritative calorie arithmetic; preserve source, units, and confidence; store snapshots with meals; keep logging functional without AI; require confirmation; use `Decimal`; never expose API keys to the browser; never silently change schemas; no insulin recommendations.
- Existing stack: FastAPI + Pydantic, SQLAlchemy + Alembic, SQLite, React + TypeScript. Use what is there.
- `httpx` is already installed as a dev dependency. Move it to runtime dependencies rather than adding a new package. Use plain HTTP calls; no OpenAI SDK.
- Provider calls happen only on the server. Keys live in the backend environment with the existing `APP_` prefix.
- `source` is `String(50)` and `confidence` is `String(20)`. Compact provider tags fit; full URLs do not.

## Approaches considered

### A. AI supplies nutrition numbers directly

Ask the model for macros with web search and write its answer. Fewest moving parts, but the numbers would come from scraped pages with no reliable provenance, and the model could quietly do the arithmetic. This breaks the project's rules and was rejected.

### B. Interpret, then look up, with web-search fallback (chosen)

The model returns structured candidates only. For each candidate, the backend tries USDA FoodData Central first; if that yields no usable record, it falls back to the numbers the model found on the web, which must carry an `http(s)` source URL. The backend scales values to the requested quantity and sums totals with `Decimal`. Wide coverage, authoritative data where it exists, and explicit low confidence where it does not. This is what the user picked.

### C. Free model plus USDA, no web search

No API key or cost, but weaker interpretation and extra local setup. The user approved paid usage and wants web search coverage, so this was dropped.

## How it will be built

### Configuration and dependencies

- Add `APP_OPENAI_API_KEY: str | None = None`, `APP_AI_MODEL: str = "gpt-6-luna"`, `APP_AI_TIMEOUT_SECONDS: float = 15.0`, and `APP_USDA_API_KEY: str = "DEMO_KEY"` to `Settings` in `backend/app/core/config.py`.
- Move `httpx` from the dev extra into main dependencies in `backend/pyproject.toml`.
- Add commented placeholders to `backend/.env.example`. Never commit a real key.
- Missing OpenAI key is a supported state, not a startup error.

### AI provider adapter

- Add `backend/app/ai/__init__.py`, `backend/app/ai/provider.py` (a small `MealInterpreter` protocol with one `interpret(description: str) -> list[RawCandidate]` method), and `backend/app/ai/openai_provider.py`.
- The adapter POSTs to the OpenAI Responses API with structured outputs and the web-search tool enabled. The prompt asks for food candidates with name, brand hint, serving label and grams, seven per-serving macro values, quantity in servings, and a source URL. It explicitly forbids meal totals and estimated values without a URL.
- One request per interpretation, at most four candidates, one retry **only** on connection or timeout errors (never on HTTP errors), and a provider timeout of 10 seconds. No streaming, no conversation state.
- Interpretation stays synchronous: one POST, no background job or polling. The frontend passes a dedicated 30-second timeout to `requestJson` for this call, above the client's 8-second default, so the provider and USDA lookups can finish.
- Tests mock HTTP; no test calls a live provider.

### Nutrition lookup adapter

- Add `backend/app/services/nutrition_lookup.py` with `find_source(raw: RawCandidate) -> ResolvedCandidate`.
- Query `GET https://api.nal.usda.gov/fdc/v1/foods/search` and then `/food/{fdcId}` using the configured key. Prefer `Branded` and `SR Legacy` results whose name matches the candidate name. Read nutrient amounts by nutrient id/name and unit; FDC values are per 100 g, so scale by the gram weight of **the USDA record's own portion** with `Decimal` to get per-serving values. The model's serving label and grams are only matching hints, never the scaling basis. Store the USDA portion as `serving_label` and `serving_grams`, so the saved food, its snapshot, and its provenance all describe the same serving.
- A USDA record is usable only when all seven macros are present. If so, set `source = "usda_fdc"`, `source_url` to the FDC food page, and `confidence = "high"`.
- Otherwise, if the model supplied all seven macros and a valid `http(s)` source URL of at most 500 characters, use those values with `source = "web_search"`, the given URL, and `confidence = "low"`.
- If neither source supplies all seven values, return the candidate with `incomplete = True`, `missing_fields` listing the gaps, and `null` for the missing values. No zero-filling.
- When the user fills the gaps from a label, the saved `Food` gets `source = "user_label"` and `confidence = "low"`, and keeps `source_url` as a record of where the partial lookup came from. A partially user-entered food must never claim a pure provider source.

### Interpretation service and endpoint

- Add `backend/app/services/interpretation.py`. It calls the provider, resolves each candidate, and returns an `InterpretResult`. It performs no database writes. All arithmetic uses `Decimal` from `app.domain.nutrition`; it scales per-serving values by the proposed quantity and never accepts a model-provided total.
- Validate model output with Pydantic: non-negative macros with sane upper bounds (for example 5,000 kcal and 50,000 mg sodium per serving), `0 < quantity <= 20`, source URL scheme and length, and name/brand length limits that fit the existing columns. Reject invalid candidates rather than repairing them.
- Add `POST /api/meals/interpret` in `backend/app/api/routes/meals.py`: body `{ description: str }` with a 1–500 character limit, response `{ candidates: [...], warnings: [...] }`.
  - No OpenAI key configured, provider timeout, or provider error → HTTP 503 with a plain message and no writes. The frontend shows the error and keeps manual search available.
  - USDA failure is a warning, not an error: fall back to the web result when it is valid.

### Schema change (explicit, reviewed)

- Add `source_url: String(500) | None` to `Food` and `MealItem` so provenance survives into the snapshot. `source` and `confidence` keep their existing compact tags.
- Add `source_url` as an optional field to `FoodCreate`, `MealItemRead`, and the new interpretation schemas.
- Widen `source` from `Literal["user_label"]` to the closed union `Literal["user_label", "usda_fdc", "web_search"]` in `FoodCreate` and `FoodUpdate`. Keep it closed — arbitrary strings are not accepted. Update the frontend `Food`/`FoodCreate` types and the `isFood` type guard to accept exactly those three tags, so AI-sourced foods do not fail validation or disappear from the manual food list.
- Create and review Alembic migration `0003_source_url.py` by hand, upgrading and downgrading cleanly on a temporary database. This is a deliberate schema change, not a silent one.

### Frontend

- Add `frontend/src/api/interpretation.ts` with the response types, a runtime type guard, and `interpretMeal(description, signal)`.
- Add `frontend/src/components/MealCandidates.tsx` below the description textarea and above `FoodSearch`. An explicit "Find foods" button triggers the call, so typing does not spend money. Show loading, error, empty, and incomplete states.
- Each candidate card shows name, brand, serving, a `USDA` or `Web · low confidence` badge, a quantity field, and an Add button. An incomplete candidate lists its missing fields and offers the existing create-food form pre-filled; it cannot be added until those values are entered.
- On Add, call the existing `POST /api/foods` to save the food (including `source_url`), then add it to `MealReview` with the proposed quantity and run the existing preview. Confirm still creates the meal through `POST /api/meals`.
- Delete or change nothing in the manual `FoodSearch` path. If interpretation fails, the description field and manual search remain usable.

### Tests

- Backend: mocked adapter tests for OpenAI request shape and structured output; lookup tests for USDA precedence, web fallback, missing nutrients, invalid URLs, and out-of-range values; service tests proving no database writes; endpoint tests for 503 without a key and successful interpretation with a stubbed provider; snapshot test proving `source_url` survives into `MealItem`.
- Frontend: API client tests for the response guard; component tests for loading, error, empty, incomplete, Add, and the unchanged manual path.
- Run the full `make check` gate before declaring completion.

### QA documentation

- Add `docs/qa/2026-11-20-ai-meal-interpretation.md` with checkout-agnostic, user-runnable steps: set the backend keys, describe a Chick-fil-A meal, verify the candidate's source badge and macros, change a quantity, Confirm, and check the saved meal; verify that interpretation creates nothing on its own; verify low-confidence fallback with a rare food; stop the backend or unset the key and verify manual logging still works. Link this file from the change summary and PR description.

## Calls made during review

These were settled from the existing code and the rules above, not left open:

1. Saving a `Food` when the user adds a candidate is allowed; only meals wait for Confirm. Manual label entry already works this way.
2. `source` becomes a closed three-value union: `user_label`, `usda_fdc`, `web_search`.
3. USDA's own portion (label and grams) is authoritative for per-serving values and is what gets stored; the model's serving is a matching hint only.
4. A food with user-filled gaps is `user_label` / `low` confidence and retains `source_url`.
5. Interpretation stays synchronous with a 10-second provider timeout, one connection-only retry, at most four candidates, and a 30-second client timeout for that request.

## Left to the builder

- Exact prompt wording and model parameters, tuned against a few real descriptions.
- Retry/backoff details within the one-retry limit.
- Visual polish for the candidate cards on a 390 px screen.
- Whether to cache repeated lookups; not needed for the first pass.
