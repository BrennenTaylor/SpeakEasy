from fastapi.testclient import TestClient


def test_food_create_accepts_provider_sources(client_with_db: TestClient) -> None:
    for source in ("user_label", "usda_fdc", "web_search"):
        response = client_with_db.post(
            "/api/foods",
            json={
                "name": "Sandwich",
                "brand": "",
                "serving_label": "1 sandwich",
                "serving_grams": "187",
                "calories": "249",
                "protein_g": "16",
                "carbs_g": "21",
                "fat_g": "11",
                "fiber_g": "1",
                "sugar_g": "0",
                "sodium_mg": "753",
                "confidence": "high",
                "source": source,
                "source_url": "https://example.com/food/1",
            },
        )
        assert response.status_code == 201
        assert response.json()["source"] == source
        assert response.json()["source_url"] == "https://example.com/food/1"


def test_food_create_rejects_unknown_source(client_with_db: TestClient) -> None:
    payload = {
        "name": "Sandwich",
        "brand": "",
        "serving_label": "1 sandwich",
        "serving_grams": "187",
        "calories": "249",
        "protein_g": "16",
        "carbs_g": "21",
        "fat_g": "11",
        "fiber_g": "1",
        "sugar_g": "0",
        "sodium_mg": "753",
        "confidence": "high",
        "source": "made_up",
    }
    assert client_with_db.post("/api/foods", json=payload).status_code == 422


def test_source_url_survives_into_meal_snapshot(client_with_db: TestClient) -> None:
    food = client_with_db.post(
        "/api/foods",
        json={
            "name": "Sandwich",
            "brand": "",
            "serving_label": "1 sandwich",
            "serving_grams": "187",
            "calories": "249",
            "protein_g": "16",
            "carbs_g": "21",
            "fat_g": "11",
            "fiber_g": "1",
            "sugar_g": "0",
            "sodium_mg": "753",
            "confidence": "low",
            "source": "web_search",
            "source_url": "https://example.com/food/1",
        },
    ).json()
    meal = client_with_db.post(
        "/api/meals",
        json={
            "raw_input": "a sandwich",
            "eaten_at": "2026-11-20T12:00:00",
            "items": [{"food_id": food["id"], "quantity": "1"}],
        },
    ).json()
    assert meal["items"][0]["source"] == "web_search"
    assert meal["items"][0]["source_url"] == "https://example.com/food/1"
