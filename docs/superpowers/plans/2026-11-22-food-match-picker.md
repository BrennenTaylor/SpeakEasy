# Food Match Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace silent single-source interpretation with ranked per-food match groups that the user can review and choose from before saving.

**Architecture:** The backend will resolve each AI-proposed food into all usable source-backed matches from one generous USDA search page plus the AI/web result, then return them as ranked groups. The frontend will render each group as radio-style choices with an explicit **Add selected foods** action that feeds the unchanged meal review/confirm flow.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic unchanged, httpx, React, TypeScript, Vitest, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-11-22-food-match-picker-design.md`

## Global Constraints

- Never invent nutritional data.
- Never let the LLM perform authoritative calorie arithmetic.
- Preserve source, units, and confidence for nutrition records.
- Store nutrition snapshots with logged meals.
- Keep meal logging functional when AI services are unavailable.
- Require confirmation before committing an AI-interpreted meal.
- Use `Decimal` for nutrition calculations.
- Never expose API keys to the browser.
- Never silently change database schemas. No migration is in this plan.
- Never provide insulin-dosing recommendations.
- Retrieval page size starts at 10; initial visible match count starts at 3. Both are display/performance choices, not a product-level `N`.
- Every change must include user-runnable QA steps in `docs/qa/YYYY-MM-DD-<topic>.md`.

## Review Focus

- **Wrong-brand or wrong-food USDA records** (for example FDC `170303` Chick-n-Strips for nuggets) must be filtered before display. Covered by Task 3 `test_resolve_matches_excludes_wrong_food_and_brand`.
- **A complete web result must not disappear when USDA returns something**; it must remain as a distinct choice. Covered by Task 3 `test_resolve_matches_returns_usda_matches_and_web_match`.
- **Missing macros or missing source URL must stay visible as incomplete**, never zero-filled or directly added. Covered by Task 3 `test_resolve_matches_keeps_url_less_draft` and Task 5 `test_incomplete_selection_opens_prefill_without_creating_food`.
- **The saved food must come from the selected match**, with source, source URL, confidence, serving, and macros preserved. Covered by Task 5 `shows ranked matches and adds only the selected one`.
- **Interpretation remains read-only and manual logging still works without AI**. Covered by Task 4 `test_interpret_returns_groups_without_writing` and Task 6 QA steps.

---

### Task 1: Commit the existing match-validation fix

**Files:**
- Modify: `backend/app/services/nutrition_lookup.py`
- Modify: `backend/tests/test_nutrition_lookup.py`
- Modify: `backend/tests/test_ai_settings.py`
- Modify: `docs/qa/2026-11-20-ai-meal-interpretation.md`
- Add: `docs/superpowers/specs/2026-11-22-food-match-picker-design.md`
- Add: `docs/superpowers/plans/2026-11-22-food-match-picker.md`

**Interfaces:**
- Consumes: current working tree changes from the wrong-USDA-match debugging session.
- Produces: a clean baseline containing brand/food-token rejection, the URL-less draft behavior in the current resolver, and isolated AI settings tests.

- [ ] **Step 1: Inspect the existing working tree**

Run: `git status --short`
Expected: four modified files listed above plus the two new design/plan docs.

- [ ] **Step 2: Run the full gate**

Run: `make check`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/nutrition_lookup.py backend/tests/test_nutrition_lookup.py backend/tests/test_ai_settings.py docs/qa/2026-11-20-ai-meal-interpretation.md docs/superpowers/specs/2026-11-22-food-match-picker-design.md docs/superpowers/plans/2026-11-22-food-match-picker.md
git commit -m "fix: reject mismatched USDA matches and add picker docs"
```

### Task 2: Add grouped response schemas

**Files:**
- Modify: `backend/app/schemas/interpretation.py`
- Test: `backend/tests/test_interpretation_schemas.py`

**Interfaces:**
- Consumes: `MACRO_FIELDS` / `DecimalText` conventions already in `app.schemas`.
- Produces:
  - `MatchView` with `match_id: str`, `source_key: str | None`, `rank: int`, `rank_reasons: list[str]`, all existing `CandidateView` fields, and the seven nullable macro fields.
  - `FoodMatchGroup` with `group_id: str`, `label: str`, `quantity: DecimalText`, `matches: list[MatchView]`.
  - `InterpretResponse.groups: list[FoodMatchGroup]`.
- Compatibility during Tasks 2–4: keep `CandidateView` and `InterpretResponse.candidates` so existing tests stay green. Task 4 removes them.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_interpretation_schemas.py`:

```python
def test_interpret_response_groups_ranked_matches() -> None:
    from app.schemas.interpretation import FoodMatchGroup, InterpretResponse, MatchView

    match = MatchView.model_validate(
        {
            "match_id": "usda:170303",
            "source_key": "170303",
            "rank": 1,
            "rank_reasons": ["brand match", "complete macros"],
            "name": "CHICK-FIL-A, Chick-n-Strips",
            "brand": "",
            "serving_label": "4 pieces",
            "serving_grams": "201.0000",
            "quantity": "1.0000",
            "source": "usda_fdc",
            "source_url": "https://fdc.nal.usda.gov/fdc-app.html#/food-details/170303/nutrients",
            "confidence": "high",
            "incomplete": False,
            "missing_fields": [],
            "calories": "458.2800",
            "protein_g": "43.0140",
            "carbs_g": "20.8839",
            "fat_g": "22.5120",
            "fiber_g": "1.8090",
            "sugar_g": "2.4924",
            "sodium_mg": "1159.7700",
        }
    )
    response = InterpretResponse.model_validate(
        {
            "groups": [
                {
                    "group_id": "0",
                    "label": "12 ct Chick-fil-A Nuggets",
                    "quantity": "1.0000",
                    "matches": [match.model_dump(mode="json")],
                }
            ],
            "warnings": [],
        }
    )

    assert response.groups[0].matches[0].match_id == "usda:170303"
    assert response.groups[0].matches[0].rank == 1
    assert response.groups[0].matches[0].name == "CHICK-FIL-A, Chick-n-Strips"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_interpretation_schemas.py -q`
Expected: FAIL with `ImportError` for `FoodMatchGroup` or `MatchView`.

- [ ] **Step 3: Add the schemas**

In `backend/app/schemas/interpretation.py`:
- Keep `RawCandidate` and `CandidateView` unchanged.
- Add `MatchView(CandidateView)` with `match_id`, `source_key`, `rank`, and `rank_reasons`.
- Add `FoodMatchGroup`.
- Add `groups: list[FoodMatchGroup] = Field(default_factory=list)` to `InterpretResponse`; change `candidates` to `list[CandidateView] = Field(default_factory=list)` so the Task 2 test can validate `groups` alone while existing tests still pass.
- Use `rank: int = Field(ge=1)`.

- [ ] **Step 4: Run the test and verify it passes**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_interpretation_schemas.py -q`
Expected: PASS.

- [ ] **Step 5: Run the backend suite**

Run: `backend/.venv/bin/python -m pytest backend/tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/interpretation.py backend/tests/test_interpretation_schemas.py
git commit -m "feat: add grouped interpretation response schemas"
```

### Task 3: Resolve all source-backed matches

**Files:**
- Modify: `backend/app/services/nutrition_lookup.py`
- Test: `backend/tests/test_nutrition_lookup.py`

**Interfaces:**
- Consumes: `RawCandidate`, `CandidateView`, `MatchView` from Task 2.
- Produces:
  - `resolve_matches(raw: RawCandidate, *, api_key: str = "DEMO_KEY", client: httpx.Client | None = None) -> tuple[list[MatchView], list[str]]`.
  - `_view` gains optional `name: str | None` and `brand: str | None` keyword arguments; when omitted it keeps current raw-based behavior.
  - `_match_view(view: CandidateView, *, match_id: str, source_key: str | None, rank: int, rank_reasons: list[str]) -> MatchView`.
- `resolve_candidate` remains for compatibility until Task 4.

- [ ] **Step 1: Write failing tests**

Add a `mock_client_with_details(foods_response, details_by_id, *, search_status=200)` helper beside the existing `mock_client` in `backend/tests/test_nutrition_lookup.py`. It must return `details_by_id[int(request.url.path.rsplit('/', 1)[-1])]` for `/food/{id}` requests and otherwise behave like `mock_client`.

Then add these tests to `backend/tests/test_nutrition_lookup.py`:

```python
def test_resolve_matches_returns_usda_matches_and_web_match() -> None:
    first = _fdc_food("201")
    first["description"] = "CHICK-FIL-A, Nuggets"
    first["fdcId"] = 170790
    second = _fdc_food("170")
    second["description"] = "CHICK-FIL-A, Nuggets, 12 count"
    second["fdcId"] = 170791
    client = mock_client_with_details(
        {
            "foods": [
                {"fdcId": 170790, "description": first["description"], "dataType": "SR Legacy"},
                {"fdcId": 170791, "description": second["description"], "dataType": "SR Legacy"},
            ]
        },
        {170790: first, 170791: second},
    )

    matches, warnings = resolve_matches(
        raw(
            name="12 ct Chick-fil-A Nuggets",
            serving_label="12 nuggets",
            serving_grams="170",
            calories="380",
        ),
        api_key="free-key",
        client=client,
    )

    assert [match.match_id for match in matches] == ["usda:170790", "usda:170791", "web:0"]
    assert matches[0].source == "usda_fdc"
    assert matches[2].source == "web_search"
    assert matches[2].name == "12 ct Chick-fil-A Nuggets"
    assert warnings == []
```

```python
def test_resolve_matches_uses_source_identity_for_usda_cards() -> None:
    food = _fdc_food("201")
    food["description"] = "CHICK-FIL-A, Nuggets, 10 piece"
    client = mock_client(
        {"foods": [{**search_hit(), "description": food["description"]}]},
        food,
    )

    matches, _ = resolve_matches(
        raw(name="12 ct Chick-fil-A Nuggets", serving_grams="170", calories="380"),
        api_key="free-key",
        client=client,
    )

    assert matches[0].name == "CHICK-FIL-A, Nuggets, 10 piece"
    assert matches[0].brand == ""
```

```python
def test_resolve_matches_excludes_wrong_food_and_brand() -> None:
    strips = _fdc_food("201")
    strips["description"] = "CHICK-FIL-A, Chick-n-Strips"
    blount = _fdc_food("113")
    blount.update(
        {
            "description": "MAC & CHEESE",
            "dataType": "Branded",
            "brandOwner": "Blount Seafood Corporation",
        }
    )
    client = mock_client(
        {
            "foods": [
                {"fdcId": 170303, "description": strips["description"], "dataType": "SR Legacy"},
                {
                    "fdcId": 1894006,
                    "description": blount["description"],
                    "dataType": "Branded",
                    "brandOwner": blount["brandOwner"],
                },
            ]
        },
        strips,
    )

    matches, warnings = resolve_matches(
        raw(
            name="Medium Mac & Cheese",
            brand="Chick-fil-A",
            serving_label="Medium",
            serving_grams="227",
            calories="450",
        ),
        api_key="free-key",
        client=client,
    )

    assert [match.match_id for match in matches] == ["web:0"]
    assert warnings == ["No USDA match found"]
```

```python
def test_resolve_matches_keeps_url_less_draft() -> None:
    client = mock_client({"foods": []}, {})

    matches, warnings = resolve_matches(
        raw(source_url=None, calories="380"), api_key="free-key", client=client
    )

    assert len(matches) == 1
    assert matches[0].source == "web_search"
    assert matches[0].incomplete is True
    assert matches[0].source_url is None
    assert "source_url" in matches[0].missing_fields
    assert matches[0].calories is None
    assert any("source_url" in warning for warning in warnings)
```

```python
def test_resolve_matches_deduplicates_within_source_only() -> None:
    food = _fdc_food("201")
    food["fdcId"] = 170790
    food["description"] = "CHICK-FIL-A, Nuggets"
    client = mock_client(
        {
            "foods": [
                {"fdcId": 170790, "description": food["description"], "dataType": "SR Legacy"},
                {"fdcId": 170790, "description": food["description"], "dataType": "SR Legacy"},
            ]
        },
        food,
    )

    matches, _ = resolve_matches(raw(name="Chick-fil-A Nuggets"), api_key="free-key", client=client)

    assert [match.match_id for match in matches] == ["usda:170790", "web:0"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_nutrition_lookup.py -q`
Expected: FAIL with `ImportError` for `resolve_matches`.

- [ ] **Step 3: Implement the resolver**

In `backend/app/services/nutrition_lookup.py`:
- Use `_USDA_PAGE_SIZE = 10` for the new search request.
- Add `_resolve_usda_matches(raw, api_key, client) -> tuple[list[CandidateView], list[str]]` that searches once, filters with current `_rank_foods`, fetches accepted detail records concurrently with at most 4 workers, and reuses `_portion`, `_nutrient_amounts`, and `_view`.
- Call `_view(..., name=food_description, brand=brand_owner_or_brand_name_or_empty)` for USDA matches so cards show source identity. For SR Legacy records with no brand fields, `brand` is `""`.
- Build the web match from the existing `_web_view` behavior. Include it whenever `source_url` is valid. Emit the URL-less draft with all macros null and `source_url` in `missing_fields` only when no USDA match survives.
- Convert both groups of views through `_match_view`.
- Rank by identity score first (the `_rank_foods` output index for USDA, exact-name score for web), then complete before incomplete, then source with USDA before web, then `match_id`.
- Fill `rank` from 1 after sorting. Fill `rank_reasons` with `brand match`, `name match`, `complete macros`, and either `USDA source` or `web source` as applicable.
- Deduplicate USDA matches by FDC ID only. Never deduplicate across sources.
- Return the web match even when USDA matches exist.
- Aggregate warnings without duplicating identical strings.

- [ ] **Step 4: Run the resolver tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_nutrition_lookup.py -q`
Expected: PASS.

- [ ] **Step 5: Run the backend suite**

Run: `backend/.venv/bin/python -m pytest backend/tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/nutrition_lookup.py backend/tests/test_nutrition_lookup.py
git commit -m "feat: resolve multiple sourced food matches"
```

### Task 4: Return groups from the interpretation endpoint

**Files:**
- Modify: `backend/app/services/interpretation.py`
- Modify: `backend/app/schemas/interpretation.py`
- Modify: `backend/tests/test_interpretation_api.py`
- Modify: `backend/tests/test_nutrition_lookup.py` (remove obsolete `resolve_candidate` tests or convert them to `resolve_matches`)

**Interfaces:**
- Consumes: `resolve_matches` from Task 3 and `FoodMatchGroup` / `MatchView` from Task 2.
- Produces:
  - `interpret_description(...) -> InterpretResponse` where every selected raw candidate yields one `FoodMatchGroup`.
  - `POST /api/meals/interpret` response contains `groups` and `warnings`, not `candidates`.
  - `resolve_candidate` and `CandidateView` no longer exist in production code.

- [ ] **Step 1: Write failing API tests**

Replace the `CandidateView` fixtures in `backend/tests/test_interpretation_api.py` with `MatchView` fixtures, then add:

```python
def test_interpret_returns_groups_without_writing(
    client_with_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.schemas.interpretation import MatchView
    from app.services import interpretation

    match = MatchView.model_validate(
        {
            **VIEW,
            "match_id": "web:0",
            "source_key": None,
            "rank": 1,
            "rank_reasons": ["web source"],
        }
    )
    monkeypatch.setattr(
        interpretation,
        "resolve_matches",
        lambda raw, **kwargs: ([match], ["USDA lookup unavailable"]),
    )
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: StubInterpreter()

    response = client_with_db.post(
        "/api/meals/interpret", json={"description": "chick fil a sandwich"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["groups"][0]["group_id"] == "0"
    assert body["groups"][0]["label"] == "Chick-fil-A sandwich"
    assert body["groups"][0]["matches"][0]["match_id"] == "web:0"
    assert body["warnings"] == ["USDA lookup unavailable"]
    assert "candidates" not in body
    assert client_with_db.get("/api/meals").json() == []
    assert client_with_db.get("/api/foods").json() == []
```

Keep the existing 503 and long-description tests, adapting fixture names only.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_interpretation_api.py -q`
Expected: FAIL because `interpret_description` still returns `candidates`.

- [ ] **Step 3: Switch the service and schema**

In `backend/app/services/interpretation.py`:
- Import `resolve_matches`.
- For each raw candidate, produce `FoodMatchGroup(group_id=str(index), label=raw.name, quantity=raw.quantity, matches=matches)`.
- Aggregate and deduplicate warnings across groups.
- Keep the existing 4-candidate cap and concurrent resolution across raw candidates.

In `backend/app/schemas/interpretation.py`:
- Make `InterpretResponse.groups` required with `default_factory=list`.
- Remove `candidates`.
- Remove `CandidateView` after all backend references are converted.

In `backend/app/services/nutrition_lookup.py`:
- Remove `resolve_candidate`. Convert every existing `resolve_candidate` test in `backend/tests/test_nutrition_lookup.py` to call `resolve_matches` and assert against `matches[0]`; keep the assertions on serving, nutrients, completeness, warnings, and fallback behavior. Remove only tests whose sole subject was the deleted single-winner selection rule.

- [ ] **Step 4: Run backend tests**

Run: `backend/.venv/bin/python -m pytest backend/tests -q`
Expected: PASS.

- [ ] **Step 5: Run backend lint and type checks**

Run: `backend/.venv/bin/ruff check backend && backend/.venv/bin/ruff format --check backend && backend/.venv/bin/mypy backend/app`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/interpretation.py backend/app/schemas/interpretation.py backend/app/services/nutrition_lookup.py backend/tests/test_interpretation_api.py backend/tests/test_nutrition_lookup.py
git commit -m "feat: return ranked food match groups"
```

### Task 5: Build the grouped picker UI

**Files:**
- Modify: `frontend/src/api/interpretation.ts`
- Modify: `frontend/src/components/MealCandidates.tsx`
- Modify: `frontend/src/components/MealCandidates.test.tsx`
- Modify: `frontend/src/components/MealLogger.tsx`

**Interfaces:**
- Consumes: `GET/POST` response `{ groups: FoodMatchGroup[]; warnings: string[] }`.
- Produces:
  - `MatchView`, `FoodMatchGroup`, `InterpretResult` in `interpretation.ts`.
  - `MealCandidates` props remain `{ rawInput: string; onAdd: (food: Food, quantity: string) => void; onComplete?: (match: MatchView) => void }`.
  - Incomplete-match prefill remains `source: "user_label"` and `confidence: "low"`, preserving only the match's `source_url`.

- [ ] **Step 1: Write failing component tests**

Replace `MealCandidates.test.tsx` with grouped fixtures (`webMatch`, `stripsMatch`, `webFood`, `stripsFood`, and four distinct matches `m1`–`m4`) and add:

```tsx
it("shows ranked matches and adds only the selected one", async () => {
  const onAdd = vi.fn();
  mocks.interpretMeal.mockResolvedValue({
    groups: [
      {
        group_id: "0",
        label: "12 ct Chick-fil-A Nuggets",
        quantity: "1.0000",
        matches: [webMatch, stripsMatch],
      },
    ],
    warnings: [],
  });
  mocks.createFood.mockResolvedValue(stripsFood);
  render(<MealCandidates rawInput="nuggets" onAdd={onAdd} />);

  fireEvent.click(screen.getByRole("button", { name: /find foods/i }));
  fireEvent.click(await screen.findByRole("radio", { name: /usda.*Chick-n-Strips/i }));
  fireEvent.click(screen.getByRole("button", { name: /add selected foods/i }));

  await waitFor(() =>
    expect(mocks.createFood).toHaveBeenCalledWith(
      expect.objectContaining({ name: "CHICK-FIL-A, Chick-n-Strips" }),
    ),
  );
  expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ id: stripsFood.id }), "1.0000");
  expect(mocks.createFood).not.toHaveBeenCalledWith(
    expect.objectContaining({ name: webMatch.name }),
  );
});
```

Add these tests:

```tsx
it("reveals remaining matches with Show more", async () => {
  mocks.interpretMeal.mockResolvedValue({
    groups: [{ group_id: "0", label: "Nuggets", quantity: "1", matches: [m1, m2, m3, m4] }],
    warnings: [],
  });
  render(<MealCandidates rawInput="nuggets" onAdd={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

  await screen.findByText(m1.name);
  expect(screen.queryByText(m3.name)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /show more/i }));
  expect(await screen.findByText(m3.name)).toBeInTheDocument();
});
```

```tsx
it("incomplete selection opens prefill without creating food", async () => {
  const onComplete = vi.fn();
  mocks.interpretMeal.mockResolvedValue({
    groups: [
      {
        group_id: "0",
        label: "Nuggets",
        quantity: "1",
        matches: [{ ...webMatch, incomplete: true, missing_fields: ["source_url"], source_url: null }],
      },
    ],
    warnings: ["Web result has no valid source_url"],
  });
  render(<MealCandidates rawInput="nuggets" onAdd={vi.fn()} onComplete={onComplete} />);
  fireEvent.click(screen.getByRole("button", { name: /find foods/i }));

  expect(await screen.findByText(/missing: source_url/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /add selected foods/i })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /complete with a label/i }));
  expect(onComplete).toHaveBeenCalledWith(
    expect.objectContaining({ match_id: "web:0", source_url: null }),
  );
  expect(mocks.createFood).not.toHaveBeenCalled();
});
```

Adapt existing loading, empty, error, warning, and no-keystroke tests to the new `groups` response. Keep `FoodSearch` behavior unchanged.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `cd frontend && npm run test -- MealCandidates`
Expected: FAIL because the response and props still use `CandidateView` / `candidates`.

- [ ] **Step 3: Update the frontend API types**

In `frontend/src/api/interpretation.ts`:
- Replace `CandidateView` with `MatchView`, including `match_id`, `source_key`, `rank`, and `rank_reasons`.
- Add `FoodMatchGroup`.
- Change `InterpretResult` to `{ groups: FoodMatchGroup[]; warnings: string[] }`.
- Update runtime guards to validate the nested group shape.

- [ ] **Step 4: Rewrite the picker component**

In `frontend/src/components/MealCandidates.tsx`:
- Store groups and a `Record<string, string>` of selected match IDs.
- Default each group to its first match.
- Render each match as a radio input with source/identity badge, serving, macros, source link, missing fields, and rank reasons.
- Show matches 1–3 initially; **Show more** reveals the rest.
- Provide one **Add selected foods** button only when every selected match is complete. For each selected complete match, call `createFood`, then `onAdd(savedFood, group.quantity)`.
- For each incomplete selected match, show **Complete with a label** and call `onComplete(match)`; hide **Add selected foods** while any selection is incomplete so no partial meal is saved.
- Keep abort-on-unmount and explicit **Find foods** behavior.

- [ ] **Step 5: Preserve prefill provenance**

In `frontend/src/components/MealLogger.tsx`, change `prefillFromCandidate` to accept `MatchView` and keep setting `source: "user_label"` and `confidence: "low"`. Do not change `FoodSearch`.

- [ ] **Step 6: Run frontend checks**

Run: `cd frontend && npm run lint && npm run typecheck && npm run test`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/interpretation.ts frontend/src/components/MealCandidates.tsx frontend/src/components/MealCandidates.test.tsx frontend/src/components/MealLogger.tsx
git commit -m "feat: add per-food match selection UI"
```

### Task 6: QA runbook and final verification

**Files:**
- Create: `docs/qa/2026-11-22-food-match-picker.md`

**Interfaces:**
- Consumes: the running app from Tasks 1–5.

- [ ] **Step 1: Write the QA runbook**

Include steps to:
1. Interpret `chick fil a 12 count nuggets and mac and cheese`.
2. Verify separate groups for nuggets and mac.
3. Verify multiple ranked matches with source badges, source URLs, serving, macros, missing fields, and rank reasons.
4. Select the Chick-fil-A web nugget match over any USDA Chick-n-Strips match, and select the Chick-fil-A web mac match over Blount Seafood.
5. Use **Show more** and verify additional matches appear.
6. Click **Add selected foods**, then **Confirm**; verify saved foods and meal snapshots retain selected source, source URL, confidence, serving, and macros.
7. Use an incomplete match (including the URL-less draft), verify it cannot be added directly, complete it with a label, and verify the saved food is `user_label` / `low` with the match's `source_url` retained when one exists (and `null` for the URL-less draft).
8. Remove `APP_OPENAI_API_KEY`, restart the backend, and verify manual food search and logging still work.

- [ ] **Step 2: Run the full gate**

Run: `make check`
Expected: PASS, including 55+ backend tests, 62+ frontend tests, lint, types, migration round trip, and production build.

- [ ] **Step 3: Commit**

```bash
git add docs/qa/2026-11-22-food-match-picker.md
git commit -m "docs: add food match picker QA runbook"
```
