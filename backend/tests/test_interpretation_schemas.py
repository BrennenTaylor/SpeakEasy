from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.interpretation import RawCandidate


def test_provider_total_is_ignored() -> None:
    raw = RawCandidate.model_validate(
        {
            "name": "Sandwich",
            "brand": "",
            "serving_label": "1 sandwich",
            "serving_grams": "187",
            "quantity": "1",
            "calories": "249",
            "protein_g": "16",
            "carbs_g": "21",
            "fat_g": "11",
            "fiber_g": "1",
            "sugar_g": "0",
            "sodium_mg": "753",
            "total_calories": "9999",
        }
    )
    assert not hasattr(raw, "total_calories")


def test_blank_model_values_become_missing() -> None:
    raw = RawCandidate.model_validate(
        {
            "name": "Waikiki Platter",
            "brand": "Yummi Sushi",
            "serving_label": "5 pieces",
            "serving_grams": "",
            "quantity": "1",
            "calories": "190",
            "protein_g": "9",
            "carbs_g": "27",
            "fat_g": "4.5",
            "fiber_g": "",
            "sugar_g": "",
            "sodium_mg": "280",
            "source_url": "",
        }
    )

    assert raw.serving_grams is None
    assert raw.fiber_g is None
    assert raw.sugar_g is None
    assert raw.source_url is None
    assert raw.calories == Decimal("190")


def test_out_of_range_macro_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawCandidate.model_validate(
            {
                "name": "Cake",
                "brand": "",
                "serving_label": "1 cake",
                "serving_grams": "500",
                "quantity": "1",
                "calories": "9000",
                "protein_g": "1",
                "carbs_g": "1",
                "fat_g": "1",
                "fiber_g": "1",
                "sugar_g": "1",
                "sodium_mg": "1",
            }
        )


def test_invalid_source_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawCandidate.model_validate(
            {
                "name": "Sandwich",
                "brand": "",
                "serving_label": "1 sandwich",
                "serving_grams": "187",
                "quantity": "1",
                "calories": "249",
                "protein_g": "16",
                "carbs_g": "21",
                "fat_g": "11",
                "fiber_g": "1",
                "sugar_g": "0",
                "sodium_mg": "753",
                "source_url": "not-a-url",
            }
        )


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

    assert isinstance(response.groups[0], FoodMatchGroup)
    assert response.groups[0].matches[0].match_id == "usda:170303"
    assert response.groups[0].matches[0].rank == 1
    assert response.groups[0].matches[0].name == "CHICK-FIL-A, Chick-n-Strips"
