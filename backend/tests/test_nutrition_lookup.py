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


def _fdc_food(portion_grams: str, omit_sugar: bool = False) -> dict[str, object]:
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
