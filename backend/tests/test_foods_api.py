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


def test_food_edit_leaves_logged_snapshot_unchanged(
    client_with_db: TestClient, food_ids: list[int]
) -> None:
    nuggets_id = food_ids[1]
    logged = client_with_db.post(
        "/api/meals",
        json={
            "raw_input": "nuggets",
            "eaten_at": "2026-11-19T12:00:00",
            "items": [{"food_id": nuggets_id, "quantity": "1"}],
        },
    )
    assert logged.status_code == 201
    assert logged.json()["items"][0]["calories"] == "250.0000"

    edited = client_with_db.patch(f"/api/foods/{nuggets_id}", json={"calories": "999.0000"})
    assert edited.status_code == 200
    assert edited.json()["calories"] == "999.0000"

    meals = client_with_db.get("/api/meals")
    assert meals.status_code == 200
    assert meals.json()[0]["items"][0]["calories"] == "250.0000"


def test_patch_unknown_food_returns_404(client_with_db: TestClient) -> None:
    response = client_with_db.patch("/api/foods/999999", json={"calories": "999.0000"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Food not found"}
