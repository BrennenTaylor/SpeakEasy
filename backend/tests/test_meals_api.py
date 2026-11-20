from fastapi.testclient import TestClient

from app.domain.nutrition import MACRO_FIELDS


def test_preview_returns_totals_without_writing(
    client_with_db: TestClient, food_ids: list[int]
) -> None:
    payload = {
        "raw_input": "two eggs and nuggets",
        "eaten_at": "2026-11-19T12:00:00",
        "items": [{"food_id": food_ids[0], "quantity": "1.5"}],
    }
    response = client_with_db.post("/api/meals/preview", json=payload)
    assert response.status_code == 200
    assert response.json()["calories"] == "210.0000"
    assert client_with_db.get("/api/meals").json() == []


def test_create_meal_stores_snapshots_and_totals(
    client_with_db: TestClient, food_ids: list[int]
) -> None:
    payload = {
        "raw_input": "one egg and two nuggets",
        "eaten_at": "2026-11-19T12:00:00",
        "items": [
            {"food_id": food_ids[0], "quantity": "1"},
            {"food_id": food_ids[1], "quantity": "2"},
        ],
    }
    response = client_with_db.post("/api/meals", json=payload)
    assert response.status_code == 201
    meal = response.json()
    assert meal["totals"]["calories"] == "640.0000"
    assert [item["quantity"] for item in meal["items"]] == ["1.0000", "2.0000"]

    foods = {food["id"]: food for food in client_with_db.get("/api/foods").json()}
    for item in meal["items"]:
        food = foods[item["food_id"]]
        assert item["unit"] == "serving"
        for field in MACRO_FIELDS:
            assert item[field] == food[field]
        for field in ("serving_label", "serving_grams", "source", "confidence"):
            assert item[field] == food[field]


def test_unknown_food_writes_nothing(client_with_db: TestClient, food_ids: list[int]) -> None:
    payload = {
        "raw_input": "one egg and a mystery",
        "eaten_at": "2026-11-19T12:00:00",
        "items": [
            {"food_id": food_ids[0], "quantity": "1"},
            {"food_id": 999999, "quantity": "1"},
        ],
    }
    response = client_with_db.post("/api/meals", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Unknown food id: 999999"}
    assert client_with_db.get("/api/meals").json() == []


def test_preview_rejects_unknown_food(client_with_db: TestClient, food_ids: list[int]) -> None:
    payload = {
        "raw_input": "a mystery",
        "eaten_at": "2026-11-19T12:00:00",
        "items": [{"food_id": 999999, "quantity": "1"}],
    }
    response = client_with_db.post("/api/meals/preview", json=payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "Unknown food id: 999999"}
    assert client_with_db.get("/api/meals").json() == []


def test_empty_items_is_rejected(client_with_db: TestClient) -> None:
    payload = {"raw_input": "nothing", "eaten_at": "2026-11-19T12:00:00", "items": []}
    assert client_with_db.post("/api/meals", json=payload).status_code == 422


def test_non_positive_quantity_is_rejected(client_with_db: TestClient, food_ids: list[int]) -> None:
    payload = {
        "raw_input": "zero eggs",
        "eaten_at": "2026-11-19T12:00:00",
        "items": [{"food_id": food_ids[0], "quantity": "0"}],
    }
    assert client_with_db.post("/api/meals", json=payload).status_code == 422


def test_list_meals_returns_recent_meals(client_with_db: TestClient, food_ids: list[int]) -> None:
    for raw_input, eaten_at in (
        ("older meal", "2026-11-18T12:00:00"),
        ("newer meal", "2026-11-19T12:00:00"),
    ):
        response = client_with_db.post(
            "/api/meals",
            json={
                "raw_input": raw_input,
                "eaten_at": eaten_at,
                "items": [{"food_id": food_ids[0], "quantity": "1"}],
            },
        )
        assert response.status_code == 201

    limited = client_with_db.get("/api/meals?limit=1")
    assert limited.status_code == 200
    assert [meal["raw_input"] for meal in limited.json()] == ["newer meal"]
    assert len(limited.json()[0]["items"]) == 1
    assert [meal["raw_input"] for meal in client_with_db.get("/api/meals").json()] == [
        "newer meal",
        "older meal",
    ]
