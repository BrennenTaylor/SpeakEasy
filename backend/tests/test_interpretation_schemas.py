import pytest
from pydantic import ValidationError

from app.schemas.interpretation import RawCandidate


def test_provider_total_is_ignored() -> None:
    raw = RawCandidate.model_validate({
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
    })
    assert not hasattr(raw, "total_calories")


def test_out_of_range_macro_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawCandidate.model_validate({
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
        })


def test_invalid_source_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawCandidate.model_validate({
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
        })
