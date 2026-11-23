import httpx

from app.schemas.interpretation import RawCandidate
from app.services.nutrition_lookup import resolve_candidate

BASE = {
    "name": "Chick-fil-A chicken sandwich",
    "brand": "Chick-fil-A",
    "serving_label": "1 sandwich",
    "serving_grams": "1",
    "quantity": "1",
    "calories": "249",
    "protein_g": "16.28",
    "carbs_g": "20.89",
    "fat_g": "11.19",
    "fiber_g": "1.4",
    "sugar_g": "0",
    "sodium_mg": "753",
    "source_url": "https://example.com/menu",
}


def raw(**overrides: object) -> RawCandidate:
    return RawCandidate.model_validate({**BASE, **overrides})


def _fdc_food(
    portion_grams: str,
    omit_sugar: bool = False,
    extra_nutrients: list[tuple[str, str, str]] | None = None,
) -> dict[str, object]:
    nutrients = [
        ("Energy", "KCAL", "249"),
        ("Protein", "G", "16.28"),
        ("Carbohydrate, by difference", "G", "20.89"),
        ("Total lipid (fat)", "G", "11.19"),
        ("Fiber, total dietary", "G", "1.4"),
        ("Sodium, Na", "MG", "753"),
    ]
    if not omit_sugar:
        nutrients.append(("Sugars, Total including NLEA", "G", "0"))
    nutrients.extend(extra_nutrients or [])
    return {
        "fdcId": 170790,
        "description": "CHICK-FIL-A, chicken sandwich",
        "dataType": "SR Legacy",
        "foodPortions": [
            {
                "amount": 1,
                "modifier": "sandwich",
                "gramWeight": float(portion_grams),
            }
        ],
        "foodNutrients": [
            {
                "nutrient": {"name": name, "unitName": unit},
                "amount": float(amount),
            }
            for name, unit, amount in nutrients
        ],
    }


def mock_client(
    foods_response: dict[str, object],
    food_response: dict[str, object],
    *,
    search_status: int = 200,
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/foods/search"):
            return httpx.Response(search_status, json=foods_response)
        return httpx.Response(200, json=food_response)

    return httpx.Client(transport=httpx.MockTransport(handler))


def search_hit() -> dict[str, object]:
    return {
        "fdcId": 170790,
        "description": "CHICK-FIL-A, chicken sandwich",
        "dataType": "SR Legacy",
    }


def test_usda_portion_overrides_model_serving() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187"))

    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)

    assert view.source == "usda_fdc"
    assert view.confidence == "high"
    assert view.serving_label == "1 sandwich"
    assert str(view.serving_grams) == "187.0000"
    assert str(view.calories) == "465.6300"
    assert warning is None


def test_canonical_nutrient_wins_over_similar_entries() -> None:
    food = _fdc_food(
        "187",
        extra_nutrients=[
            ("Sugars, added", "G", "9"),
            ("Fiber, soluble", "G", "9"),
            ("Carbohydrate, by summation", "G", "9"),
        ],
    )
    food["foodNutrients"] = list(reversed(food["foodNutrients"]))
    client = mock_client({"foods": [search_hit()]}, food)

    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)

    assert warning is None
    assert str(view.sugar_g) == "0.0000"
    assert str(view.fiber_g) == "2.6180"
    assert str(view.carbs_g) == "39.0643"


def test_branded_food_with_serving_size_but_no_portions() -> None:
    food = _fdc_food("187")
    food["dataType"] = "Branded"
    food.pop("foodPortions")
    food["servingSize"] = 187
    food["servingSizeUnit"] = "G"
    food["householdServingFullText"] = "1 sandwich"
    client = mock_client(
        {"foods": [{**search_hit(), "dataType": "Branded"}]},
        food,
    )

    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)

    assert warning is None
    assert view.source == "usda_fdc"
    assert view.serving_label == "1 sandwich"
    assert str(view.serving_grams) == "187.0000"
    assert str(view.calories) == "465.6300"


def test_non_gram_serving_size_is_not_treated_as_grams() -> None:
    food = _fdc_food("187")
    food.pop("foodPortions")
    food["servingSize"] = 187
    food["servingSizeUnit"] = "ML"
    client = mock_client({"foods": [search_hit()]}, food)

    view, warning = resolve_candidate(raw(source_url=None), api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.incomplete is True
    assert "USDA record had no portion" in warning


def test_missing_sugar_is_flagged_not_zeroed() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187", omit_sugar=True))

    view, _ = resolve_candidate(raw(source_url=None), api_key="free-key", client=client)

    assert view.source == "usda_fdc"
    assert view.incomplete is True
    assert "sugar_g" in view.missing_fields
    assert view.sugar_g is None


def test_complete_web_fallback_is_used_when_usda_is_incomplete() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187", omit_sugar=True))

    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.confidence == "low"
    assert view.incomplete is False
    assert str(view.calories) == "249.0000"
    assert warning is not None


def test_web_candidate_without_valid_url_is_incomplete() -> None:
    client = mock_client({"foods": []}, {})

    view, warning = resolve_candidate(raw(source_url=None), api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.incomplete is True
    assert "source_url" in warning


def test_usda_failure_falls_back_to_web_with_warning() -> None:
    client = mock_client({"foods": []}, {}, search_status=429)

    view, warning = resolve_candidate(raw(), api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.confidence == "low"
    assert warning is not None
    assert "429" in warning


def test_mismatched_usda_food_falls_back_to_web() -> None:
    candidate = raw(
        name="12 ct Chick-fil-A Nuggets",
        serving_label="12-count serving",
        serving_grams="170",
        calories="380",
    )
    food = _fdc_food("201")
    food["description"] = "CHICK-FIL-A, Chick-n-Strips"
    client = mock_client(
        {
            "foods": [
                {
                    **search_hit(),
                    "description": "CHICK-FIL-A, Chick-n-Strips",
                }
            ]
        },
        food,
    )

    view, warning = resolve_candidate(candidate, api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.serving_label == "12-count serving"
    assert str(view.serving_grams) == "170.0000"
    assert str(view.calories) == "380.0000"
    assert warning == "No USDA match found"


def test_mismatched_usda_brand_falls_back_to_web() -> None:
    candidate = raw(
        name="Medium Mac & Cheese",
        serving_label="Medium serving",
        serving_grams="227",
        calories="450",
    )
    food = _fdc_food("113")
    food.update(
        {
            "description": "MAC & CHEESE",
            "dataType": "Branded",
            "brandOwner": "Blount Seafood Corporation",
        }
    )
    search_result = {
        **search_hit(),
        "description": "MAC & CHEESE",
        "dataType": "Branded",
        "brandOwner": "Blount Seafood Corporation",
    }
    client = mock_client({"foods": [search_result]}, food)

    view, warning = resolve_candidate(candidate, api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.serving_label == "Medium serving"
    assert str(view.serving_grams) == "227.0000"
    assert str(view.calories) == "450.0000"
    assert warning == "No USDA match found"


def test_empty_brand_rejects_branded_usda_record_without_name_overlap() -> None:
    candidate = raw(
        name="Medium Mac & Cheese",
        brand="",
        serving_label="Medium",
        serving_grams="227",
        calories="450",
    )
    food = _fdc_food("113")
    food.update(
        {
            "description": "MAC & CHEESE",
            "dataType": "Branded",
            "brandOwner": "Blount Seafood Corporation",
        }
    )
    search_result = {
        **search_hit(),
        "description": "MAC & CHEESE",
        "dataType": "Branded",
        "brandOwner": "Blount Seafood Corporation",
    }
    client = mock_client({"foods": [search_result]}, food)

    view, warning = resolve_candidate(candidate, api_key="free-key", client=client)

    assert view.source == "web_search"
    assert view.serving_label == "Medium"
    assert str(view.serving_grams) == "227.0000"
    assert str(view.calories) == "450.0000"
    assert warning == "No USDA match found"


def test_empty_brand_accepts_branded_usda_record_with_name_overlap() -> None:
    candidate = raw(
        name="CHICK-FIL-A Chicken Nuggets",
        brand="",
        serving_label="12-count serving",
        serving_grams="170",
        calories="380",
    )
    # brandOwner has no comma because punctuation tokenization is a Task 3 concern;
    # this test only pins that name/brandOwner word overlap corroborates the match.
    food = _fdc_food("187")
    food.update(
        {
            "description": "CHICK-FIL-A, Chicken Nuggets",
            "dataType": "Branded",
            "brandOwner": "Chick-fil-A Inc.",
        }
    )
    search_result = {
        **search_hit(),
        "description": "CHICK-FIL-A, Chicken Nuggets",
        "dataType": "Branded",
        "brandOwner": "Chick-fil-A Inc.",
    }
    client = mock_client({"foods": [search_result]}, food)

    view, warning = resolve_candidate(candidate, api_key="free-key", client=client)

    assert view.source == "usda_fdc"
    assert warning is None
