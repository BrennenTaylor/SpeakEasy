# Milestone 2 — Manual Meal Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a phone user type what they ate, attach saved foods with every macro, review backend-calculated totals, confirm the meal, and match the same food again later.

**Architecture:** A new Alembic revision adds foods, meals, and meal items. Each meal item copies the food's nutrition into a snapshot, so later food edits leave history alone. A domain module holds `Decimal` arithmetic. FastAPI exposes food create/search/update, meal preview/create/list, and the frontend calls those endpoints through a typed client. AI parsing and web lookup stay out of this milestone.

**Tech Stack:** FastAPI 0.165, Pydantic 2.14, SQLAlchemy 2.1, Alembic 1.20, SQLite, pytest 9; React 19, TypeScript 6, Vite 8, Tailwind 4, Vitest 5, React Testing Library.

**Spec:** `docs/superpowers/specs/2026-11-19-milestone-2-meal-logging-design.md`

## Global Constraints

- Python 3.12 only. Use `backend/.venv/bin/python`, `pytest`, `ruff`, and `mypy` from there.
- Node 24 via nvm. Frontend commands run in `frontend/` with Node 24 on PATH.
- No new dependencies. `Decimal`, SQLAlchemy `Numeric(12, 4)`, and Pydantic cover the work.
- All nutrition math uses `Decimal`. Quantize to `Decimal("0.0001")` with `ROUND_HALF_UP`.
- Serialize nutrition as JSON strings. The frontend parses strings for display only and never computes totals.
- All routes stay under `/api`.
- No AI calls, no provider keys, no photo upload, no auth, no insights, no service worker.
- Single-user local database. No `user_id` column.
- Every food and every meal item keeps `source`, units, and `confidence`.
- `make check` exits 0 with a clean `git status` at the end of each task.
- Work on a feature branch created by the execution skill.

## Review Focus

1. Fractional serving quantities and multi-item sums. Task 2 pins exact `Decimal` results.
2. A meal payload naming a food that does not exist. Task 4 proves no rows are written.
3. Food reuse by alias with different casing. Task 3 pins normalized search.
4. Editing a food after logging. Task 5 proves the meal item snapshot keeps its original values.
5. A backend that is down or returns a wrong shape during logging. Task 6 pins client errors; Task 8 pins the visible error state.

---

## File Structure

Created by this plan:

```text
backend/app/domain/__init__.py
backend/app/domain/nutrition.py
backend/app/models/nutrition.py
backend/app/models/food.py
backend/app/models/meal.py
backend/app/schemas/__init__.py
backend/app/schemas/common.py
backend/app/schemas/nutrition.py
backend/app/schemas/food.py
backend/app/schemas/meal.py
backend/app/services/__init__.py
backend/app/services/foods.py
backend/app/services/meals.py
backend/app/api/routes/foods.py
backend/app/api/routes/meals.py
backend/alembic/versions/0002_meal_logging.py
backend/tests/test_nutrition.py
backend/tests/test_foods_api.py
backend/tests/test_meals_api.py
frontend/src/api/client.ts
frontend/src/api/client.test.ts
frontend/src/api/foods.ts
frontend/src/api/meals.ts
frontend/src/api/foods.test.ts
frontend/src/api/meals.test.ts
frontend/src/components/FoodSearch.tsx
frontend/src/components/FoodSearch.test.tsx
frontend/src/components/MealReview.tsx
frontend/src/components/RecentMeals.tsx
frontend/src/components/MealLogger.tsx
frontend/src/components/MealLogger.test.tsx
```

Modified: `backend/app/api/router.py`, `backend/tests/conftest.py`, `backend/tests/test_migrations.py`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `README.md`.

---

### Task 1: Design baseline and nutrition arithmetic

**Files:**
- Commit: `docs/superpowers/specs/2026-11-19-milestone-2-meal-logging-design.md`, `docs/superpowers/plans/2026-11-19-milestone-2-meal-logging.md`
- Create: `backend/app/domain/__init__.py`, `backend/app/domain/nutrition.py`, `backend/tests/test_nutrition.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `MACRO_FIELDS: tuple[str, ...]` with `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg`
  - `NutritionValues` dataclass with those seven `Decimal` fields
  - `NutritionValues.scaled(quantity: Decimal) -> NutritionValues`
  - `NutritionValues.plus(other: NutritionValues) -> NutritionValues`
  - `NutritionValues.as_dict() -> dict[str, Decimal]`

- [ ] **Step 1: Commit the design baseline**

```bash
git add docs/superpowers/specs/2026-11-19-milestone-2-meal-logging-design.md docs/superpowers/plans/2026-11-19-milestone-2-meal-logging.md
git commit -m "docs: approve milestone 2 design and plan"
```

- [ ] **Step 2: Write the failing arithmetic tests**

`backend/tests/test_nutrition.py` defines a local helper that fills the seven fields with `Decimal("100")`, `Decimal("10")`, `Decimal("20")`, `Decimal("3")`, `Decimal("2")`, `Decimal("5")`, `Decimal("50")`, then overrides named fields. Write three tests:

```python
def test_scales_fractional_servings_exactly() -> None:
    scaled = make(calories=Decimal("140.0000"), protein_g=Decimal("13.0000")).scaled(
        Decimal("1.5")
    )
    assert scaled.calories == Decimal("210.0000")
    assert scaled.protein_g == Decimal("19.5000")

def test_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity must be positive"):
        make().scaled(Decimal("0"))

def test_adds_two_nutrition_sets() -> None:
    total = make(calories=Decimal("140")).plus(make(calories=Decimal("80")))
    assert total.calories == Decimal("220")
    assert total.sodium_mg == Decimal("100")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_nutrition.py -v`
Expected: collection error, module `app.domain.nutrition` missing.

- [ ] **Step 4: Implement the domain module**

Create `NutritionValues` as a frozen dataclass. `scaled` rejects `quantity <= 0`, multiplies each field, and quantizes the result to `0.0001`. `plus` adds matching fields and quantizes. `as_dict` returns the seven fields keyed by `MACRO_FIELDS`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_nutrition.py -v`
Expected: `3 passed`.

- [ ] **Step 6: Verify gates and commit**

Run: `make lint-backend && make typecheck-backend`
Expected: exit 0.

```bash
git add backend/app/domain backend/tests/test_nutrition.py
git commit -m "feat(nutrition): add Decimal macro arithmetic"
```

---

### Task 2: Domain models and reviewed migration

**Files:**
- Create: `backend/app/models/nutrition.py`, `backend/app/models/food.py`, `backend/app/models/meal.py`, `backend/alembic/versions/0002_meal_logging.py`
- Modify: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `app.models.base.Base`, `MACRO_FIELDS` from Task 1.
- Produces:
  - `app.models.food.Food` with `id`, `name`, `brand`, `serving_label`, `serving_grams`, the seven macro fields, `source`, `confidence`, `aliases`, `created_at`
  - `app.models.meal.Meal` with `id`, `raw_input`, `eaten_at`, `created_at`, `items`
  - `app.models.meal.MealItem` with `id`, `meal_id`, `food_id`, `quantity`, `unit`, `serving_label`, `serving_grams`, the seven macro fields, `source`, `confidence`, `created_at`
  - A `NutritionColumns` mixin in `app.models.nutrition` declaring the seven `Numeric(12, 4)` columns

- [ ] **Step 1: Write the failing migration test**

Add to `backend/tests/test_migrations.py`:

```python
def test_domain_tables_exist_after_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = build_engine(alembic_config.get_main_option("sqlalchemy.url"))
    try:
        with engine.connect() as connection:
            names = set(inspect(connection).get_table_names())
    finally:
        engine.dispose()
    assert {"foods", "meals", "meal_items"} <= names
```

Import `inspect` from `sqlalchemy`. The existing `test_schema_matches_models_after_upgrade` already asserts `compare_metadata(context, Base.metadata) == []`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_migrations.py -v`
Expected: the new table assertion fails.

- [ ] **Step 3: Implement the models**

`NutritionColumns` declares the seven macro columns as `Numeric(12, 4)`, `nullable=False`. `Food.aliases` uses SQLAlchemy `JSON` with `default=list`. `created_at` uses a UTC timestamp helper with a Python-side default. `Meal.items` uses a relationship with `cascade="all, delete-orphan"` and `back_populates`. `MealItem` carries `serving_label` and `serving_grams` copied from the food.

- [ ] **Step 4: Write revision `0002_meal_logging.py`**

Set `down_revision = "0001_baseline"`. `upgrade` creates `foods`, `meals`, then `meal_items` with foreign keys to `foods.id` and `meals.id`. Column names and types must match the models. `downgrade` drops `meal_items`, `meals`, then `foods`.

- [ ] **Step 5: Run migration tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_migrations.py -v`
Expected: `3 passed`, including `compare_metadata` returning `[]`.

- [ ] **Step 6: Verify gates and commit**

Run: `make check-migrations && make lint-backend && make typecheck-backend`
Expected: `migrations OK: head -> base -> head`, exit 0.

```bash
git add backend/app/models backend/alembic/versions/0002_meal_logging.py backend/tests/test_migrations.py
git commit -m "feat(db): add food, meal, and snapshot schema"
```

---

### Task 3: Food schemas, service, and API

**Files:**
- Create: `backend/app/schemas/__init__.py`, `backend/app/schemas/common.py`, `backend/app/schemas/nutrition.py`, `backend/app/schemas/food.py`, `backend/app/services/__init__.py`, `backend/app/services/foods.py`, `backend/app/api/routes/foods.py`, `backend/tests/test_foods_api.py`
- Modify: `backend/app/api/router.py`, `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `Food` from Task 2, `NutritionValues` from Task 1.
- Produces:
  - `DecimalText` in `app.schemas.common`, an `Annotated[Decimal, PlainSerializer(...)]` that emits a JSON string
  - `NutritionFields` and `NutritionTotals` in `app.schemas.nutrition`
  - `FoodCreate`, `FoodRead` in `app.schemas.food`
  - `normalize(text: str) -> str`
  - `create_food(session: Session, payload: FoodCreate) -> Food`
  - `search_foods(session: Session, query: str, limit: int = 20) -> list[Food]`
  - `food_values(food: Food) -> NutritionValues`
  - Fixtures `session(tmp_path)` and `client_with_db(session)` in `backend/tests/conftest.py`
  - Routes `POST /api/foods`, `GET /api/foods`

- [ ] **Step 1: Write the failing API tests**

`backend/tests/test_foods_api.py` covers four cases:

```python
def test_create_food_returns_string_decimals(client_with_db: TestClient) -> None:
    response = client_with_db.post("/api/foods", json={
        "name": "Costco nuggets", "brand": "Kirkland Signature",
        "serving_label": "4 pieces", "serving_grams": "88",
        "calories": "250.0000", "protein_g": "14.0000", "carbs_g": "16.0000",
        "fat_g": "14.0000", "fiber_g": "1.0000", "sugar_g": "2.0000",
        "sodium_mg": "400.0000", "confidence": "high",
        "aliases": ["those costco nuggets"],
    })
    assert response.status_code == 201
    assert response.json()["calories"] == "250.0000"

def test_search_finds_alias_with_different_casing(client_with_db: TestClient) -> None:
    # create the food above, then GET /api/foods?q=THOSE COSTCO NUGGETS
    assert [item["name"] for item in response.json()] == ["Costco nuggets"]

def test_search_returns_empty_for_unknown_query(client_with_db: TestClient) -> None:
    assert client_with_db.get("/api/foods?q=unrelated").json() == []

def test_create_food_rejects_negative_calories(client_with_db: TestClient) -> None:
    # copy the valid payload with calories "-1"
    assert response.status_code == 422
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_foods_api.py -v`
Expected: FAIL, fixtures or routes missing.

- [ ] **Step 3: Add the test fixtures**

In `backend/tests/conftest.py`, add `session(tmp_path)` that builds a file-backed SQLite engine at `tmp_path / "test.db"`, calls `Base.metadata.create_all`, yields one `Session`, then disposes the engine. Add `client_with_db(session)` that calls `create_app()`, sets `app.dependency_overrides[get_session] = lambda: session`, yields `TestClient`, then clears overrides.

- [ ] **Step 4: Implement schemas and service**

`NutritionFields` declares the seven fields with `DecimalText` and `ge=0` for macros. `FoodCreate(NutritionFields)` adds the food fields from the spec, with `source: Literal["user_label"]`, `confidence: Literal["high", "low"]`, and `aliases: list[str]`. `FoodRead` adds `id` and `created_at` and sets `from_attributes=True`.

`normalize` lowercases, strips, and collapses whitespace. `search_foods` loads foods with `select(Food)` and keeps those whose normalized `name`, `brand`, or any alias contains the normalized query. Sort by normalized name, then id, and apply `limit`. `food_values` builds `NutritionValues` from a `Food`.

- [ ] **Step 5: Implement the routes**

`POST /api/foods` returns 201. `GET /api/foods?q=...&limit=20` returns `list[FoodRead]`. Add the router to `app/api/router.py` with tag `foods`. Do not add a PATCH route here; Task 5 owns food editing.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_foods_api.py -v`
Expected: `4 passed`.

- [ ] **Step 7: Verify gates and commit**

Run: `make lint-backend && make typecheck-backend`
Expected: exit 0.

```bash
git add backend/app backend/tests
git commit -m "feat(api): create and search user-sourced foods"
```

---

### Task 4: Meal preview, creation, and listing

**Files:**
- Create: `backend/app/schemas/meal.py`, `backend/app/services/meals.py`, `backend/app/api/routes/meals.py`, `backend/tests/test_meals_api.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: `Food`, `Meal`, `MealItem` from Task 2, `FoodCreate` from Task 3, `NutritionValues` from Task 1, `food_values` from Task 3.
- Produces:
  - `MealItemCreate(food_id: int, quantity: DecimalText, unit: Literal["serving"])`
  - `MealCreate(raw_input: str, eaten_at: datetime, items: list[MealItemCreate])`
  - `MealItemRead` and `MealRead` with `totals: NutritionTotals`
  - `class UnknownFoodError(LookupError)`
  - `preview_totals(session: Session, payload: MealCreate) -> NutritionValues`
  - `create_meal(session: Session, payload: MealCreate) -> Meal`
  - `list_meals(session: Session, limit: int) -> list[Meal]`
  - `meal_to_read(meal: Meal) -> MealRead`
  - Routes `POST /api/meals/preview`, `POST /api/meals`, `GET /api/meals`

- [ ] **Step 1: Write the failing API tests**

`backend/tests/test_meals_api.py` covers six cases. Add a `food_ids(client_with_db)` fixture in `backend/tests/conftest.py` that posts two valid foods through `/api/foods` and returns their ids: the first has calories `"140.0000"` (eggs), the second `"250.0000"` (nuggets), with all other macro fields set to `"1.0000"`. Task 5 reuses this fixture.

```python
def test_preview_returns_totals_without_writing(client_with_db, food_ids) -> None:
    payload = {"raw_input": "two eggs and nuggets", "eaten_at": "2026-11-19T12:00:00",
               "items": [{"food_id": food_ids[0], "quantity": "1.5"}]}
    response = client_with_db.post("/api/meals/preview", json=payload)
    assert response.status_code == 200
    assert response.json()["calories"] == "210.0000"
    assert client_with_db.get("/api/meals").json() == []

def test_create_meal_stores_snapshots_and_totals(client_with_db, food_ids) -> None:
    # post two items with quantities "1" and "2", assert 201,
    # assert calories in totals, assert each item's snapshot matches its food

def test_unknown_food_writes_nothing(client_with_db, food_ids) -> None:
    # post one valid id and one id 999999, expect 422 and GET /api/meals == []

def test_empty_items_is_rejected(client_with_db) -> None:
    # items [], expect 422

def test_non_positive_quantity_is_rejected(client_with_db, food_ids) -> None:
    # quantity "0", expect 422

def test_list_meals_returns_recent_meals(client_with_db, food_ids) -> None:
    # create two meals, GET /api/meals?limit=1, assert one item and newest first
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_meals_api.py -v`
Expected: FAIL, modules missing.

- [ ] **Step 3: Implement meal schemas**

`MealItemCreate.quantity` uses `gt=0` and `unit` defaults to `"serving"` so the test payloads can omit it. `MealCreate.items` uses `min_length=1` and `raw_input` uses `min_length=1`. `MealItemRead` copies the snapshot fields from `MealItem` and sets `from_attributes=True`. `MealRead` lists items and adds `totals: NutritionTotals`.

- [ ] **Step 4: Implement the meal service**

`preview_totals` loads each food, raises `UnknownFoodError` for a missing id, scales `food_values(food)` by `quantity`, and adds the results. `create_meal` repeats that work, constructs `Meal` and `MealItem` rows, copies each food's macros, serving fields, `source`, and `confidence` onto the item, adds and commits, then returns the `Meal`. `list_meals` orders by `eaten_at` descending, then `id` descending, and applies `limit`. `meal_to_read` builds one `NutritionValues` from each item's snapshot fields, adds them with `plus`, and constructs `MealRead` from the meal, its items, and those totals.

- [ ] **Step 5: Implement the routes**

`POST /api/meals/preview` returns `NutritionTotals`. `POST /api/meals` returns 201 and maps `UnknownFoodError` to `HTTPException(422, detail="Unknown food id: <id>")`. `GET /api/meals?limit=20` returns `list[MealRead]`. Add the router to `app/api/router.py` with tag `meals`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_meals_api.py -v`
Expected: `6 passed`.

- [ ] **Step 7: Verify gates and commit**

Run: `make lint-backend && make typecheck-backend`
Expected: exit 0.

```bash
git add backend/app/api backend/app/schemas/meal.py backend/app/services backend/tests/conftest.py backend/tests/test_meals_api.py
git commit -m "feat(api): preview and log meals with nutrition snapshots"
```

---

### Task 5: Food update and snapshot immutability

**Files:**
- Modify: `backend/app/schemas/food.py`, `backend/app/services/foods.py`, `backend/app/api/routes/foods.py`, `backend/tests/test_foods_api.py`

**Interfaces:**
- Consumes: `FoodCreate`, `FoodRead`, `create_food`, `search_foods`, `client_with_db`, and `food_ids` from earlier tasks; meal routes from Task 4.
- Produces:
  - `FoodUpdate` in `app.schemas.food`
  - `update_food(session: Session, food_id: int, payload: FoodUpdate) -> Food | None`
  - Route `PATCH /api/foods/{food_id}`

- [ ] **Step 1: Write the failing immutability test**

Add to `backend/tests/test_foods_api.py`:

```python
def test_food_edit_leaves_logged_snapshot_unchanged(client_with_db, food_ids) -> None:
    # create a food with calories "250.0000", log a meal with one item,
    # PATCH /api/foods/{id} with calories "999.0000",
    # GET /api/meals and assert item calories still "250.0000"
```

Also add a test that `PATCH` with an unknown id returns 404.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest tests/test_foods_api.py -v`
Expected: two new tests fail.

- [ ] **Step 3: Implement `FoodUpdate` and the service function**

`FoodUpdate` has optional versions of every editable food field, including the seven macros. `update_food` applies only fields present in `model_fields_set`, commits, and returns `None` for an unknown id.

- [ ] **Step 4: Wire the existing PATCH route to the service**

Add `PATCH /api/foods/{food_id}` accepting `FoodUpdate` and calling `update_food`. Raise `HTTPException(404)` when `update_food` returns `None`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest tests/test_foods_api.py -v`
Expected: `6 passed`.

- [ ] **Step 6: Verify gates and commit**

Run: `make lint-backend && make typecheck-backend`
Expected: exit 0.

```bash
git add backend/app backend/tests/test_foods_api.py
git commit -m "feat(api): edit foods without rewriting logged meals"
```

---

### Task 6: Frontend API client

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`, `frontend/src/api/foods.ts`, `frontend/src/api/foods.test.ts`, `frontend/src/api/meals.ts`, `frontend/src/api/meals.test.ts`

**Interfaces:**
- Consumes: nothing from earlier frontend tasks.
- Produces:
  - `RequestError extends Error`
  - `requestJson<T>(path: string, init: RequestInit, validate: (value: unknown) => value is T, timeoutMs?: number) -> Promise<T>`
  - `Food`, `FoodCreate`, `fetchFoods(query: string, signal?: AbortSignal)`, `createFood`, `updateFood`
  - `MealItem`, `Meal`, `MealCreate`, `MacroStrings`, `fetchMeals(signal?: AbortSignal)`, `createMeal`, `previewMeal(payload: MealCreate, signal?: AbortSignal)`

- [ ] **Step 1: Write the failing client tests**

`client.test.ts` stubs `fetch` and covers a valid JSON body, a non-2xx status, a non-JSON body, a shape mismatch, and a timeout that throws `RequestError("Server did not respond")`. `foods.test.ts` covers `fetchFoods` with a query and `createFood` with a valid payload. `meals.test.ts` covers `previewMeal`, `createMeal`, and `fetchMeals`, asserting the request path and body.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- src/api`
Expected: FAIL, modules missing.

- [ ] **Step 3: Implement the shared request helper**

`requestJson` builds the URL from `VITE_API_BASE_URL`, sends `accept: application/json` and a JSON content type when a body exists, combines a passed `AbortSignal` with `AbortSignal.timeout(8000)`, maps errors to `RequestError` with the same messages as `health.ts`, parses JSON, and calls `validate`. Leave `health.ts` untouched.

- [ ] **Step 4: Implement the typed food and meal clients**

Define TypeScript types with string decimal fields. Validators check object shape at runtime. All functions use `requestJson`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npm run test -- src/api`
Expected: all API client suites pass.

- [ ] **Step 6: Verify gates and commit**

Run: `cd frontend && npm run lint && npm run format:check && npm run typecheck`
Expected: exit 0.

```bash
git add frontend/src/api
git commit -m "feat(web): typed clients for foods and meals"
```

---

### Task 7: Food search and quick-create UI

**Files:**
- Create: `frontend/src/components/FoodSearch.tsx`, `frontend/src/components/FoodSearch.test.tsx`

**Interfaces:**
- Consumes: `Food`, `FoodCreate`, `fetchFoods`, `createFood` from Task 6.
- Produces: `FoodSearch({ onAdd }: { onAdd: (food: Food) => void })`, a component with a query input, a search button, result rows with an Add button, and a form that creates a food from a label.

- [ ] **Step 1: Write the failing component tests**

Cover three cases with `fetch` stubbed:

```tsx
it("lists matching foods and calls onAdd", async () => { /* search, click Add */ });
it("creates a food from label values and calls onAdd", async () => { /* fill form, submit */ });
it("shows an error when search fails", async () => { /* 503 response, expect role alert */ });
```

The create form must include fields for name, brand, serving label, serving grams, calories, protein, carbs, fat, fiber, sugar, sodium, confidence, and aliases.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/FoodSearch.test.tsx`
Expected: FAIL, component missing.

- [ ] **Step 3: Implement the component**

Keep the search query in local state. Call `fetchFoods` on submit. Render each result with name, brand, serving label, calories, and an Add button. Toggle the create form with a button labelled "Create a food from a label". On success, call `onAdd` with the returned food. Show `role="alert"` with the error message on failure. Use Tailwind classes that stay inside a 390 px viewport.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npm run test -- src/components/FoodSearch.test.tsx`
Expected: `3 passed`.

- [ ] **Step 5: Verify gates and commit**

Run: `cd frontend && npm run lint && npm run format:check && npm run typecheck`
Expected: exit 0.

```bash
git add frontend/src/components/FoodSearch.tsx frontend/src/components/FoodSearch.test.tsx
git commit -m "feat(web): food search and label entry"
```

---

### Task 8: Meal logger, review, and recent meals

**Files:**
- Create: `frontend/src/components/MealReview.tsx`, `frontend/src/components/RecentMeals.tsx`, `frontend/src/components/MealLogger.tsx`, `frontend/src/components/MealLogger.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `FoodSearch` from Task 7, `previewMeal`, `createMeal`, `fetchMeals`, `Meal`, `MacroStrings` from Task 6.
- Produces:
  - `MealReview({ items, totals, submitting, onQuantityChange, onRemove, onConfirm })`
  - `RecentMeals({ meals: Meal[] })`
  - `MealLogger`, mounted in `App`

`items` is an array of `{ food: Food; quantity: string }`. `totals` is `MacroStrings | null`.

- [ ] **Step 1: Write the failing logger tests**

Stub `fetch` by URL: `/api/health` returns `{"status":"ok"}`, `/api/foods` returns one food, `/api/meals/preview` returns macro strings, `/api/meals` GET returns `[]` then POST returns the saved meal. Cover four cases:

```tsx
it("lets the user type a sentence, add a food, preview, and confirm", async () => {});
it("shows a backend error when confirm fails", async () => {});
it("keeps Confirm disabled until a food is added", async () => {});
it("shows recent meals after a successful confirm", async () => {});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/MealLogger.test.tsx`
Expected: FAIL, component missing.

- [ ] **Step 3: Implement the review and list components**

`MealReview` renders one row per item with a quantity input, a Remove button, and the seven macro totals from `totals`. It disables Confirm when `submitting` or `items` is empty. `RecentMeals` renders each meal's `raw_input`, `eaten_at`, and macro totals. Both keep text inside a 390 px container.

- [ ] **Step 4: Implement the logger orchestration**

`MealLogger` holds `rawInput`, `items`, `totals`, `meals`, `error`, and `submitting`. Adding a food appends it with quantity `"1"` and calls `previewMeal`. Changing a quantity calls `previewMeal` again. Confirm calls `createMeal`, clears the draft, then reloads `fetchMeals`. Use `AbortController` cleanup on unmount for preview and list requests.

- [ ] **Step 5: Mount the logger in the app**

Add a `<section aria-labelledby="logger-heading">` with `<h2 id="logger-heading">What did you eat?</h2>` and `<MealLogger />` below the server status section. Update `App.test.tsx` so its `fetch` stub handles both `/api/health` and `/api/meals`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd frontend && npm run test`
Expected: all suites pass, including the 390 px layout test.

- [ ] **Step 7: Verify gates and commit**

Run: `make lint && make typecheck && make build`
Expected: exit 0.

```bash
git add frontend/src
git commit -m "feat(web): log meals with macro review and confirmation"
```

---

### Task 9: Documentation and final gate

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: every task above.
- Produces: README that describes Milestone 2 scope and the next milestone.

- [ ] **Step 1: Update the scope section**

Replace the Milestone 1 scope and out-of-scope lists in `README.md` with the Milestone 2 scope: food records from labels, macro totals from the backend, confirmation before save, snapshot history, and alias search. State that AI interpretation, branded web lookup, photo upload, and insights come next. Keep the setup and troubleshooting sections unchanged.

- [ ] **Step 2: Run the full gate**

Run: `make check`
Expected: exit 0, including lint, type checks, tests, migrations, and build.

- [ ] **Step 3: Confirm a clean tree**

Run: `git status --short`
Expected: no output before the documentation commit.

- [ ] **Step 4: Commit and hand off**

```bash
git add README.md
git commit -m "docs: describe milestone 2 logging scope"
```

Run: `git status --short`
Expected: no output.

---

## Definition of Done

- A user can create a food from label values, find it again by alias, log it with a fractional serving, review all seven macros, and confirm the meal.
- Totals come from backend `Decimal` arithmetic and arrive as JSON strings.
- A logged meal keeps its snapshot after the food changes.
- An unknown food id or empty item list writes no meal.
- Meal logging works with no AI service configured.
- `make check` exits 0 with a clean tree.
- The README describes the shipped scope and the next milestone.
