# AI Meal Interpretation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user type a meal description and receive source-backed food candidates they can review, adjust, and confirm into a meal, with the existing manual flow untouched.

**Architecture:** A server-side OpenAI adapter returns structured candidate foods only; a lookup layer resolves each against USDA FoodData Central first and falls back to web-sourced values with a URL and low confidence; a read-only endpoint returns candidates. The frontend pre-fills the existing food-create and meal-review flow, and Confirm still creates the meal. `Decimal` is used for all scaling and totals.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, SQLite, `httpx`, React, TypeScript, Vitest, pytest

**Spec:** `docs/superpowers/specs/2026-11-20-ai-meal-interpretation-design.md`

## Global Constraints

- Never invent nutritional data; no zero-filling of missing nutrients.
- Never let the LLM perform authoritative calorie arithmetic; ignore model-provided totals.
- Preserve source, units, and confidence on foods and meal snapshots.
- Keep meal logging functional with no AI key and while AI services are unavailable.
- Require confirmation before committing any AI-interpreted meal.
- Use `Decimal` for all nutrition math.
- Never expose API keys to the browser; keys stay in `backend/.env`.
- Never silently change database schemas; migration `0003_source_url.py` must be reviewed.
- No insulin-dosing recommendations.
- Default model is `gpt-6-luna`; provider timeout 10 seconds; one retry on connection or timeout errors only; at most four candidates; client timeout 30 seconds for interpretation only.
- `source` is a closed union: `user_label`, `usda_fdc`, `web_search`.
- Every change includes user-runnable QA steps in `docs/qa/YYYY-MM-DD-<topic>.md`, linked from the change summary or PR description.
- Full gate before completion: `make check` (28 existing backend tests, 45 existing frontend tests, lint, format, mypy, typecheck, migrations, build).

## Review Focus

These are the failure modes the spec implies that no task's main happy path covers. Each is pinned to a test in the owning task.

1. Source omits one of the seven macros → candidate is `incomplete` with named gaps, no zero. Test: `test_missing_sugar_is_flagged_not_zeroed` (Task 5).
2. Model supplies numbers without a valid `http(s)` source URL → not accepted as authoritative. Test: `test_web_candidate_without_valid_url_is_incomplete` (Task 5).
3. No API key or provider outage → endpoint returns 503, manual logging still works. Test: `test_interpret_returns_503_without_key` (Task 6) and `test_manual_flow_works_without_ai` (Task 8).
4. Model returns a meal total or an out-of-range macro → rejected, backend computes totals. Test: `test_provider_total_is_ignored` and `test_out_of_range_macro_is_rejected` (Task 3).
5. Model's serving grams disagree with USDA's portion → USDA portion is stored and used for scaling. Test: `test_usda_portion_overrides_model_serving` (Task 5).

---

### Task 1: Settings and runtime HTTP dependency

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_ai_settings.py` (new)

**Interfaces:**
- Produces: `Settings.openai_api_key: str | None`, `Settings.ai_model: str`, `Settings.ai_timeout_seconds: float`, `Settings.usda_api_key: str`. Because `Settings` uses `env_prefix="APP_"`, these map to `APP_OPENAI_API_KEY`, `APP_AI_MODEL`, `APP_AI_TIMEOUT_SECONDS`, `APP_USDA_API_KEY`.

- [ ] **Step 1: Write the failing test**

```python
def test_ai_settings_defaults_and_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    settings = Settings()
    assert settings.openai_api_key is None
    assert settings.ai_model == "gpt-6-luna"
    assert settings.ai_timeout_seconds == 10.0
    assert settings.usda_api_key == "DEMO_KEY"

    monkeypatch.setenv("APP_OPENAI_API_KEY", "server-only-key")
    monkeypatch.setenv("APP_AI_MODEL", "gpt-6.1-terra")
    assert Settings().openai_api_key == "server-only-key"
    assert Settings().ai_model == "gpt-6.1-terra"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/pytest -q tests/test_ai_settings.py`
Expected: FAIL — `Settings` has no `openai_api_key` attribute.

- [ ] **Step 3: Add the four fields to `Settings`**

Use `str | None = None` for the OpenAI key, `str = "gpt-6-luna"`, `float = 10.0`, and `str = "DEMO_KEY"`. Move `httpx` from the `dev` extra into main `dependencies` with its existing `>=0.28,<0.29` constraint. Add commented placeholders to `backend/.env.example` for all four variables. Do not add an OpenAI SDK.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv/bin/pytest -q tests/test_ai_settings.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/pyproject.toml backend/.env.example backend/tests/test_ai_settings.py
git commit -m "feat: add server-side AI settings and runtime httpx"
```

---

### Task 2: Source contract and source URL persistence

**Files:**
- Modify: `backend/app/schemas/food.py`
- Modify: `backend/app/schemas/meal.py`
- Modify: `backend/app/models/food.py`
- Modify: `backend/app/models/meal.py`
- Create: `backend/alembic/versions/0003_source_url.py`
- Test: `backend/tests/test_sources.py` (new), `backend/tests/test_meals_api.py`

**Interfaces:**
- Produces: `FoodSource = Literal["user_label", "usda_fdc", "web_search"]` exported from `app.schemas.food`; `FoodCreate.source_url: str | None = None`; `FoodUpdate.source_url: str | None = None`; `Food.source_url`, `MealItem.source_url` as nullable `String(500)`; `MealItemRead.source_url: str | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_food_create_accepts_provider_sources(client_with_db: TestClient) -> None:
    for source in ("user_label", "usda_fdc", "web_search"):
        response = client_with_db.post("/api/foods", json={
            "name": "Sandwich", "brand": "", "serving_label": "1 sandwich",
            "serving_grams": "187", "calories": "249", "protein_g": "16",
            "carbs_g": "21", "fat_g": "11", "fiber_g": "1", "sugar_g": "0",
            "sodium_mg": "753", "confidence": "high", "source": source,
            "source_url": "https://example.com/food/1",
        })
        assert response.status_code == 201
        assert response.json()["source"] == source
        assert response.json()["source_url"] == "https://example.com/food/1"


def test_food_create_rejects_unknown_source(client_with_db: TestClient) -> None:
    payload = {
        "name": "Sandwich", "brand": "", "serving_label": "1 sandwich",
        "serving_grams": "187", "calories": "249", "protein_g": "16",
        "carbs_g": "21", "fat_g": "11", "fiber_g": "1", "sugar_g": "0",
        "sodium_mg": "753", "confidence": "high", "source": "made_up",
    }
    assert client_with_db.post("/api/foods", json=payload).status_code == 422


def test_source_url_survives_into_meal_snapshot(client_with_db: TestClient) -> None:
    food = client_with_db.post("/api/foods", json={
        "name": "Sandwich", "brand": "", "serving_label": "1 sandwich",
        "serving_grams": "187", "calories": "249", "protein_g": "16",
        "carbs_g": "21", "fat_g": "11", "fiber_g": "1", "sugar_g": "0",
        "sodium_mg": "753", "confidence": "low", "source": "web_search",
        "source_url": "https://example.com/food/1",
    }).json()
    meal = client_with_db.post("/api/meals", json={
        "raw_input": "a sandwich", "eaten_at": "2026-11-20T12:00:00",
        "items": [{"food_id": food["id"], "quantity": "1"}],
    }).json()
    assert meal["items"][0]["source"] == "web_search"
    assert meal["items"][0]["source_url"] == "https://example.com/food/1"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest -q tests/test_sources.py`
Expected: FAIL — unknown source is accepted and `source_url` is absent.

- [ ] **Step 3: Widen the source union and add `source_url`**

Define `FoodSource` in `app/schemas/food.py`; use it in `FoodCreate.source` and `FoodUpdate.source` instead of `Literal["user_label"]`. Add `source_url: str | None = None` with `max_length=500` to both schemas and to `MealItemRead`. Add nullable `source_url = mapped_column(String(500), nullable=True)` to `Food` and `MealItem`. In `create_meal`, copy `food.source_url` into the `MealItem` alongside `source` and `confidence`.

- [ ] **Step 4: Write migration `0003_source_url.py` by hand**

`op.upgrade` adds `source_url` as nullable `String(500)` to `foods` and `meal_items`. `op.downgrade` drops both columns. Use Alembic batch mode as configured. Do not autogenerate without reading the file.

- [ ] **Step 5: Run the tests and migration check**

Run: `cd backend && .venv/bin/pytest -q tests/test_sources.py tests/test_meals_api.py && .venv/bin/python scripts/check_migrations.py`
Expected: PASS, including upgrade → downgrade → upgrade on the temporary database.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/food.py backend/app/schemas/meal.py backend/app/models/food.py backend/app/models/meal.py backend/alembic/versions/0003_source_url.py backend/app/services/meals.py backend/tests/test_sources.py backend/tests/test_meals_api.py
git commit -m "feat: allow sourced foods and persist source URLs"
```

---

### Task 3: Interpretation schemas and validation

**Files:**
- Create: `backend/app/schemas/interpretation.py`
- Test: `backend/tests/test_interpretation_schemas.py` (new)

**Interfaces:**
- Produces: `RawCandidate` (all seven macros as `DecimalText`, `name`, `brand`, `serving_label`, `serving_grams`, `quantity`, `source_url: HttpUrl | None`; no total field); `CandidateView` (same identifying fields plus `source: Literal["usda_fdc", "web_search"]`, `confidence: Literal["high", "low"]`, `incomplete: bool`, `missing_fields: list[str]`, and seven macros as `DecimalText | None`); `InterpretRequest(description)`; `InterpretResponse(candidates, warnings)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_provider_total_is_ignored() -> None:
    from app.schemas.interpretation import RawCandidate

    raw = RawCandidate.model_validate({
        "name": "Sandwich", "brand": "", "serving_label": "1 sandwich",
        "serving_grams": "187", "quantity": "1",
        "calories": "249", "protein_g": "16", "carbs_g": "21", "fat_g": "11",
        "fiber_g": "1", "sugar_g": "0", "sodium_mg": "753",
        "total_calories": "9999",
    })
    assert not hasattr(raw, "total_calories")


def test_out_of_range_macro_is_rejected() -> None:
    import pytest
    from pydantic import ValidationError
    from app.schemas.interpretation import RawCandidate

    with pytest.raises(ValidationError):
        RawCandidate.model_validate({
            "name": "Cake", "brand": "", "serving_label": "1 cake",
            "serving_grams": "500", "quantity": "1",
            "calories": "9000", "protein_g": "1", "carbs_g": "1", "fat_g": "1",
            "fiber_g": "1", "sugar_g": "1", "sodium_mg": "1",
        })
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest -q tests/test_interpretation_schemas.py`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Define the schemas**

Use `DecimalText` for numeric fields so JSON keeps string precision. Bound `description` to 1–500 characters; `calories <= 5000` and `sodium_mg <= 50000` per serving; `0 < quantity <= 20`; `name <= 200`, `brand <= 200`, `serving_label <= 100`. `source_url` is `HttpUrl | None`. Extra keys are ignored by default, and no total field is declared.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest -q tests/test_interpretation_schemas.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/interpretation.py backend/tests/test_interpretation_schemas.py
git commit -m "feat: define validated interpretation schemas"
```

---

### Task 4: OpenAI interpretation adapter

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/provider.py`
- Create: `backend/app/ai/openai_provider.py`
- Create: `backend/app/ai/dependencies.py`
- Test: `backend/tests/test_openai_provider.py` (new)

**Interfaces:**
- Consumes: `RawCandidate` (Task 3), `Settings` (Task 1).
- Produces: `MealInterpreter` protocol with `interpret(self, description: str) -> list[RawCandidate]`; `OpenAIInterpreter(api_key: str, model: str = "gpt-6-luna", timeout_seconds: float = 10.0, max_candidates: int = 4, client: httpx.Client | None = None)`; `get_interpreter() -> MealInterpreter | None` returning `None` when no key is configured, suitable for `app.dependency_overrides` in tests.

- [ ] **Step 1: Write the failing test**

```python
def test_interpreter_parses_candidates_and_uses_server_key() -> None:
    import httpx
    from app.ai.openai_provider import OpenAIInterpreter

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={
            "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"candidates": [{"name": "Chick-fil-A chicken sandwich", "brand": "Chick-fil-A", "serving_label": "1 sandwich", "serving_grams": "187", "quantity": "1", "calories": "249", "protein_g": "16.28", "carbs_g": "20.89", "fat_g": "11.19", "fiber_g": "1.4", "sugar_g": "0", "sodium_mg": "753", "source_url": "https://example.com/menu"}]}'}]}]
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    interpreter = OpenAIInterpreter("server-only-key", client=client)

    result = interpreter.interpret("chick fil a sandwich")
    assert len(result) == 1
    assert result[0].name == "Chick-fil-A chicken sandwich"
    assert "server-only-key" in seen[0].headers["Authorization"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/pytest -q tests/test_openai_provider.py`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the adapter**

POST to `https://api.openai.com/v1/responses` with the bearer key, `model` from settings, `text.format` set to a JSON schema for `{candidates: RawCandidate[]}`, and the web-search tool enabled. The prompt must say: propose only per-serving food values with a source URL, never meal totals, never estimates without a URL, and at most four candidates. Parse `output_text` as JSON and validate through `RawCandidate`. On `httpx.TimeoutException` or `httpx.TransportError`, retry once; on HTTP error status, raise `AIServiceError` with no retry. Cap the parsed list at `max_candidates`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv/bin/pytest -q tests/test_openai_provider.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai backend/tests/test_openai_provider.py
git commit -m "feat: add server-side OpenAI interpretation adapter"
```

---

### Task 5: Nutrition lookup with USDA-first and web fallback

**Files:**
- Create: `backend/app/services/nutrition_lookup.py`
- Test: `backend/tests/test_nutrition_lookup.py` (new)

**Interfaces:**
- Consumes: `RawCandidate`, `CandidateView` (Task 3), `Settings` (Task 1).
- Produces: `resolve_candidate(raw: RawCandidate, *, api_key: str = "DEMO_KEY", client: httpx.Client | None = None) -> tuple[CandidateView, str | None]`. The second value is a warning string or `None`. No database access.

- [ ] **Step 1: Write the failing tests**

```python
import httpx
from app.schemas.interpretation import RawCandidate
from app.services.nutrition_lookup import resolve_candidate

BASE = {
    "name": "Chick-fil-A chicken sandwich", "brand": "Chick-fil-A",
    "serving_label": "1 sandwich", "serving_grams": "1", "quantity": "1",
    "calories": "249", "protein_g": "16.28", "carbs_g": "20.89", "fat_g": "11.19",
    "fiber_g": "1.4", "sugar_g": "0", "sodium_mg": "753",
    "source_url": "https://example.com/menu",
}


def raw(**overrides: object) -> RawCandidate:
    return RawCandidate.model_validate({**BASE, **overrides})


def mock_client(foods_response: dict[str, object], food_response: dict[str, object]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/foods/search"):
            return httpx.Response(200, json=foods_response)
        return httpx.Response(200, json=food_response)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_usda_portion_overrides_model_serving() -> None:
    client = mock_client(
        {"foods": [{"fdcId": 170790, "description": "CHICK-FIL-A, chicken sandwich", "dataType": "SR Legacy"}]},
        _fdc_food(portion_grams="187"),
    )
    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)
    assert view.source == "usda_fdc"
    assert view.confidence == "high"
    assert view.serving_grams == "187.0000"
    assert view.calories == "465.6300"
    assert warning is None


def test_missing_sugar_is_flagged_not_zeroed() -> None:
    client = mock_client(
        {"foods": [{"fdcId": 170790, "description": "CHICK-FIL-A, chicken sandwich", "dataType": "SR Legacy"}]},
        _fdc_food(portion_grams="187", omit_sugar=True),
    )
    view, _ = resolve_candidate(raw(), api_key="free-key", client=client)
    assert view.incomplete is True
    assert "sugar_g" in view.missing_fields
    assert view.sugar_g is None


def test_web_candidate_without_valid_url_is_incomplete() -> None:
    client = mock_client({"foods": []}, {})
    view, warning = resolve_candidate(raw(source_url=None), api_key="free-key", client=client)
    assert view.source == "web_search"
    assert view.incomplete is True
    assert "source_url" in warning
```

`_fdc_food(portion_grams: str, omit_sugar: bool = False) -> dict[str, object]` is a builder-written helper that returns one FDC `/food/{id}` response: `dataType: "SR Legacy"`, `foodPortions: [{"amount": 1, "modifier": "sandwich", "gramWeight": 187.0}]`, and `foodNutrients` entries with `nutrient.name`/`nutrient.unitName`/`amount` for Energy(kcal) 249, Protein 16.28, Carbohydrate by difference 20.89, Total lipid (fat) 11.19, Fiber total dietary 1.4, Sodium (Na) 753, plus Sugars total including NLEA 0 unless `omit_sugar` is true. Values are per 100 g.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest -q tests/test_nutrition_lookup.py`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the lookup**

Search FDC `/foods/search`, then fetch `/food/{fdcId}` for the best `Branded` or `SR Legacy` name match. Map FDC nutrients by name and unit from the response, never by remembered numeric ids. Treat FDC amounts as per 100 g and scale by the record's own portion gram weight using `Decimal` and the quantizer in `app.domain.nutrition`. Store that portion's label and grams. If all seven macros are present, return `usda_fdc`/`high`. Otherwise, if the raw candidate has all seven macros and a valid `http(s)` URL of at most 500 characters, return `web_search`/`low` with the model's per-serving values unchanged. Otherwise set `incomplete`, list the missing macro names, and set missing values to `None`. A failed or rate-limited FDC call returns a warning and falls through to the web path. No zero-filling and no database writes.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest -q tests/test_nutrition_lookup.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nutrition_lookup.py backend/tests/test_nutrition_lookup.py
git commit -m "feat: add USDA-first nutrition lookup with web fallback"
```

---

### Task 6: Interpretation service and read-only endpoint

**Files:**
- Modify: `backend/app/api/routes/meals.py`
- Create: `backend/app/services/interpretation.py`
- Test: `backend/tests/test_interpretation_api.py` (new)

**Interfaces:**
- Consumes: `MealInterpreter`, `get_interpreter` (Task 4); `resolve_candidate` (Task 5); `InterpretRequest`, `InterpretResponse` (Task 3).
- Produces: `interpret_description(description: str, interpreter: MealInterpreter, *, api_key: str = "DEMO_KEY", client: httpx.Client | None = None) -> InterpretResponse`; `POST /api/meals/interpret`.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from app.ai.dependencies import get_interpreter


def test_interpret_returns_candidates_without_writing(
    client_with_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.interpretation as interpretation
    from app.schemas.interpretation import CandidateView, RawCandidate

    view = CandidateView.model_validate({
        "name": "Chick-fil-A sandwich", "brand": "Chick-fil-A",
        "serving_label": "1 sandwich", "serving_grams": "187.0000", "quantity": "1.0000",
        "source": "web_search", "source_url": "https://example.com/menu",
        "confidence": "low", "incomplete": False, "missing_fields": [],
        "calories": "249.0000", "protein_g": "16.0000", "carbs_g": "21.0000",
        "fat_g": "11.0000", "fiber_g": "1.0000", "sugar_g": "0.0000", "sodium_mg": "753.0000",
    })
    monkeypatch.setattr(
        interpretation, "resolve_candidate", lambda raw, **kwargs: (view, None)
    )
    from app.schemas.interpretation import RawCandidate

    class StubInterpreter:
        def interpret(self, description: str) -> list[RawCandidate]:
            assert description == "chick fil a sandwich"
            return [RawCandidate.model_validate({
                "name": "Chick-fil-A sandwich", "brand": "Chick-fil-A",
                "serving_label": "1 sandwich", "serving_grams": "187", "quantity": "1",
                "calories": "249", "protein_g": "16", "carbs_g": "21", "fat_g": "11",
                "fiber_g": "1", "sugar_g": "0", "sodium_mg": "753",
                "source_url": "https://example.com/menu",
            })]

    client_with_db.app.dependency_overrides[get_interpreter] = lambda: StubInterpreter()
    response = client_with_db.post("/api/meals/interpret", json={"description": "chick fil a sandwich"})
    assert response.status_code == 200
    assert response.json()["candidates"][0]["source"] in ("usda_fdc", "web_search")
    assert client_with_db.get("/api/meals").json() == []
    assert client_with_db.get("/api/foods").json() == []


def test_interpret_returns_503_without_key(client_with_db: TestClient) -> None:
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: None
    response = client_with_db.post("/api/meals/interpret", json={"description": "lunch"})
    assert response.status_code == 503
    assert response.json() == {"detail": "AI interpretation is not configured"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/pytest -q tests/test_interpretation_api.py`
Expected: FAIL — route does not exist.

- [ ] **Step 3: Implement the service and route**

`interpret_description` calls `interpreter.interpret`, caps at four candidates, resolves each with `resolve_candidate`, and collects warning strings. It accepts no `Session`, so it cannot write. The route depends on `get_interpreter`; when it returns `None`, raise `HTTPException(503, "AI interpretation is not configured")`. Provider exceptions are caught and converted to 503 with the same message. Validate `description` through `InterpretRequest`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/pytest -q tests/test_interpretation_api.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/interpretation.py backend/app/api/routes/meals.py backend/tests/test_interpretation_api.py
git commit -m "feat: add read-only meal interpretation endpoint"
```

---

### Task 7: Frontend API client and food type widening

**Files:**
- Create: `frontend/src/api/interpretation.ts`
- Create: `frontend/src/api/interpretation.test.ts`
- Modify: `frontend/src/api/foods.ts`
- Modify: `frontend/src/api/foods.test.ts`

**Interfaces:**
- Consumes: nothing from earlier frontend tasks.
- Produces: `FoodSource` union `"user_label" | "usda_fdc" | "web_search"` in `foods.ts`; `Food.source: FoodSource`; `FoodCreate.source?: FoodSource`; `CandidateView` and `InterpretResult` types; `interpretMeal(description: string, signal?: AbortSignal): Promise<InterpretResult>`.

- [ ] **Step 1: Write the failing test**

Import `describe`, `expect`, `it`, and `vi` from `vitest`, matching existing API tests.

```ts
it("parses an interpretation response and uses the long timeout", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({
      candidates: [{
        name: "Chick-fil-A sandwich", brand: "Chick-fil-A",
        serving_label: "1 sandwich", serving_grams: "187.0000", quantity: "1.0000",
        source: "usda_fdc", source_url: "https://fdc.example/170790",
        confidence: "high", incomplete: false, missing_fields: [],
        calories: "465.6300", protein_g: "30.4000", carbs_g: "39.1000",
        fat_g: "20.9000", fiber_g: "2.6000", sugar_g: "0.0000", sodium_mg: "1407.0000",
      }],
      warnings: [],
    }), { status: 200, headers: { "content-type": "application/json" } }),
  );

  const result = await interpretMeal("chick fil a sandwich");
  expect(result.candidates[0].source).toBe("usda_fdc");
  const signal = fetchSpy.mock.calls[0][1]?.signal as AbortSignal;
  expect(signal).toBeDefined();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm run test -- src/api/interpretation.test.ts`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the client and widen food types**

Use `requestJson("/api/meals/interpret", { method: "POST", body: JSON.stringify({ description }), signal }, isInterpretResult, 30_000)`. The guard checks every candidate field, including nullable macros and the three allowed source tags. In `foods.ts`, replace `"user_label"` with the `FoodSource` union in `Food`, `FoodCreate`, and `isFood`, and add optional `source_url?: string | null` to `FoodCreate` and `Food`. Existing manual payloads still send `source: "user_label"`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd frontend && npm run test -- src/api/interpretation.test.ts src/api/foods.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/interpretation.ts frontend/src/api/interpretation.test.ts frontend/src/api/foods.ts frontend/src/api/foods.test.ts
git commit -m "feat: add interpretation API client and sourced food types"
```

---

### Task 8: Candidate UI and MealLogger integration

**Files:**
- Create: `frontend/src/components/MealCandidates.tsx`
- Create: `frontend/src/components/MealCandidates.test.tsx`
- Modify: `frontend/src/components/MealLogger.tsx`
- Modify: `frontend/src/components/MealLogger.test.tsx`
- Test: `frontend/src/components/MealCandidates.test.tsx`

**Interfaces:**
- Consumes: `interpretMeal`, `CandidateView` (Task 7); `createFood`, `Food` (Task 7); `ReviewItem` from `MealReview`.
- Produces: `MealCandidates({ rawInput: string, onAdd: (food: Food, quantity: string) => void })`.

- [ ] **Step 1: Write the failing tests**

Import test helpers from `vitest` and `@testing-library/react` as `MealLogger.test.tsx` does, and stub `interpretMeal`/`createFood` with `vi.mock`.

```tsx
it("shows source badge and adds a complete candidate", async () => {
  render(<MealCandidates rawInput="chick fil a sandwich" onAdd={onAdd} />);
  fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
  const card = await screen.findByText("Chick-fil-A sandwich");
  expect(screen.getByText("USDA")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /add chick-fil-a sandwich/i }));
  await waitFor(() => expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({
    source: "usda_fdc",
  }), "1.0000"));
});

it("manual flow works without AI", async () => {
  // Mock /api/meals/interpret to return 503, then render MealLogger and
  // confirm FoodSearch and the description field are still usable.
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm run test -- src/components/MealCandidates.test.tsx`
Expected: FAIL — component does not exist.

- [ ] **Step 3: Build the candidate component**

Render an explicit "Find foods" button; do not call the API on every keystroke. Show loading, error, empty, and incomplete states. Each complete card shows name, brand, serving, a `USDA` badge for `usda_fdc` or `Web · low confidence` for `web_search`, a quantity input, and an Add button. On Add, call `createFood` with the candidate's values, `source`, `source_url`, and `confidence`, then call `onAdd(savedFood, quantity)`. Incomplete cards list `missing_fields` and offer no Add until the existing create-food form supplies the values. Abort in-flight requests on unmount.

- [ ] **Step 4: Integrate into `MealLogger`**

Place `<MealCandidates rawInput={rawInput} onAdd={handleCandidateAdd} />` after the description textarea and before `<FoodSearch>`. `handleCandidateAdd` pushes the saved food and proposed quantity into the existing review items, clears the error, and runs the existing preview. Confirm and `RecentMeals` stay unchanged. Do not modify `FoodSearch` behavior.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npm run test -- src/components/MealCandidates.test.tsx src/components/MealLogger.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/MealCandidates.tsx frontend/src/components/MealCandidates.test.tsx frontend/src/components/MealLogger.tsx frontend/src/components/MealLogger.test.tsx
git commit -m "feat: add AI candidate review to meal logging"
```

---

### Task 9: QA runbook and full gate

**Files:**
- Create: `docs/qa/2026-11-20-ai-meal-interpretation.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: Write the QA runbook**

Use the filename above, checkout-agnostic commands run from the repository root, no absolute paths and no worktree assumptions. Cover: create the two accounts and keys; put them in `backend/.env`; run `make setup`, `make migrate`, `make dev-backend`, `make dev-frontend`; describe "chick fil a sandwich"; verify the candidate's source badge, serving, and all seven macro values; change the quantity and verify the preview changes; Confirm and verify the meal in Recent Meals; call `POST /api/meals/interpret` directly and verify no food or meal was written; try a rare food to exercise web-search fallback; unset `APP_OPENAI_API_KEY`, restart the backend, and verify manual food creation and logging still work. Include the expected 503 text and the exact command to check the database is unchanged.

- [ ] **Step 2: Update README**

Add the two optional keys to setup and troubleshooting, note that interpretation is optional, and link the QA runbook. Do not change unrelated sections.

- [ ] **Step 3: Run the full gate**

Run: `make check`
Expected: PASS — backend lint/format/mypy/pytest, frontend lint/format/typecheck/vitest, migration round trip, and production build.

- [ ] **Step 4: Commit and push**

```bash
git add docs/qa/2026-11-20-ai-meal-interpretation.md README.md
git commit -m "docs: add AI interpretation QA runbook"
git push origin main
```
