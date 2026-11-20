from fastapi.testclient import TestClient

FOOD_PAYLOAD = {
    "name": "Costco nuggets",
    "brand": "Kirkland Signature",
    "serving_label": "4 pieces",
    "serving_grams": "88",
    "calories": "250.0000",
    "protein_g": "14.0000",
    "carbs_g": "16.0000",
    "fat_g": "14.0000",
    "fiber_g": "1.0000",
    "sugar_g": "2.0000",
    "sodium_mg": "400.0000",
    "confidence": "high",
    "aliases": ["those costco nuggets"],
}


def test_create_food_returns_string_decimals(client_with_db: TestClient) -> None:
    response = client_with_db.post("/api/foods", json=FOOD_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["calories"] == "250.0000"


def test_search_finds_alias_with_different_casing(client_with_db: TestClient) -> None:
    assert client_with_db.post("/api/foods", json=FOOD_PAYLOAD).status_code == 201
    response = client_with_db.get("/api/foods?q=THOSE COSTCO NUGGETS")
    assert [item["name"] for item in response.json()] == ["Costco nuggets"]


def test_search_returns_empty_for_unknown_query(client_with_db: TestClient) -> None:
    assert client_with_db.get("/api/foods?q=unrelated").json() == []


def test_create_food_rejects_negative_calories(client_with_db: TestClient) -> None:
    payload = dict(FOOD_PAYLOAD)
    payload["calories"] = "-1"
    response = client_with_db.post("/api/foods", json=payload)
    assert response.status_code == 422
