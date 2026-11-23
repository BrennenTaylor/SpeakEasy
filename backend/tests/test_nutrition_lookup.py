import httpx

from app.schemas.interpretation import MatchView, RawCandidate
from app.services.nutrition_lookup import resolve_matches

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


def mock_client_with_details(
    foods_response: dict[str, object],
    details_by_id: dict[int, dict[str, object]],
    *,
    search_status: int = 200,
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/foods/search"):
            return httpx.Response(search_status, json=foods_response)
        return httpx.Response(200, json=details_by_id[int(request.url.path.rsplit("/", 1)[-1])])

    return httpx.Client(transport=httpx.MockTransport(handler))


def search_hit() -> dict[str, object]:
    return {
        "fdcId": 170790,
        "description": "CHICK-FIL-A, chicken sandwich",
        "dataType": "SR Legacy",
    }


def test_usda_portion_overrides_model_serving() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187"))

    matches, warnings = resolve_matches(raw(), api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "usda_fdc"
    assert view.confidence == "high"
    assert view.serving_label == "1 sandwich"
    assert str(view.serving_grams) == "187.0000"
    assert str(view.calories) == "465.6300"
    assert warnings == []


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

    matches, warnings = resolve_matches(raw(), api_key="free-key", client=client)
    view = matches[0]

    assert warnings == []
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

    matches, warnings = resolve_matches(raw(), api_key="free-key", client=client)
    view = matches[0]

    assert warnings == []
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

    matches, warnings = resolve_matches(raw(source_url=None), api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.incomplete is True
    assert "USDA record had no portion" in warnings


def test_missing_sugar_is_flagged_not_zeroed() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187", omit_sugar=True))

    matches, _ = resolve_matches(raw(source_url=None), api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "usda_fdc"
    assert view.incomplete is True
    assert "sugar_g" in view.missing_fields
    assert view.sugar_g is None


def test_complete_web_fallback_is_used_when_usda_is_incomplete() -> None:
    client = mock_client({"foods": [search_hit()]}, _fdc_food("187", omit_sugar=True))

    matches, warnings = resolve_matches(raw(), api_key="free-key", client=client)

    # The incomplete USDA record ranks first; the complete web fallback stays
    # available as the next match instead of replacing it.
    view = next(match for match in matches if match.match_id == "web:0")
    assert view.source == "web_search"
    assert view.confidence == "low"
    assert view.incomplete is False
    assert str(view.calories) == "249.0000"
    assert warnings == ["USDA record was incomplete"]


def test_web_candidate_without_valid_url_is_incomplete() -> None:
    client = mock_client({"foods": []}, {})

    matches, warnings = resolve_matches(raw(source_url=None), api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.incomplete is True
    assert any("source_url" in warning for warning in warnings)


def test_usda_failure_falls_back_to_web_with_warning() -> None:
    client = mock_client({"foods": []}, {}, search_status=429)

    matches, warnings = resolve_matches(raw(), api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.confidence == "low"
    assert any("429" in warning for warning in warnings)


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

    matches, warnings = resolve_matches(candidate, api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.serving_label == "12-count serving"
    assert str(view.serving_grams) == "170.0000"
    assert str(view.calories) == "380.0000"
    assert warnings == ["No USDA match found"]


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

    matches, warnings = resolve_matches(candidate, api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.serving_label == "Medium serving"
    assert str(view.serving_grams) == "227.0000"
    assert str(view.calories) == "450.0000"
    assert warnings == ["No USDA match found"]


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

    matches, warnings = resolve_matches(candidate, api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "web_search"
    assert view.serving_label == "Medium"
    assert str(view.serving_grams) == "227.0000"
    assert str(view.calories) == "450.0000"
    assert warnings == ["No USDA match found"]


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

    matches, warnings = resolve_matches(candidate, api_key="free-key", client=client)
    view = matches[0]

    assert view.source == "usda_fdc"
    assert warnings == []


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


def test_overlong_serving_label_is_truncated_to_schema_cap() -> None:
    # A 120-char modifier once built a serving_label past MatchView's 100-char
    # cap; the ValidationError then took down the whole interpretation request.
    modifier = "nuggets " * 15
    good = _fdc_food("187")
    good["fdcId"] = 170790
    good["description"] = "CHICK-FIL-A, Nuggets"
    overlong = _fdc_food("187")
    overlong["fdcId"] = 170791
    overlong["description"] = "CHICK-FIL-A, Nuggets, 12 count"
    overlong["foodPortions"] = [{"amount": 1, "modifier": modifier, "gramWeight": 187.0}]
    client = mock_client_with_details(
        {
            "foods": [
                {"fdcId": 170790, "description": good["description"], "dataType": "SR Legacy"},
                {"fdcId": 170791, "description": overlong["description"], "dataType": "SR Legacy"},
            ]
        },
        {170790: good, 170791: overlong},
    )

    matches, warnings = resolve_matches(
        raw(name="Chick-fil-A Nuggets", serving_grams="170", calories="380"),
        api_key="free-key",
        client=client,
    )

    # The overlong record survives with a schema-valid label; the sibling and
    # the web fallback keep their places.
    assert [match.match_id for match in matches] == ["usda:170790", "usda:170791", "web:0"]
    overlong_view = next(match for match in matches if match.match_id == "usda:170791")
    assert overlong_view.serving_label == f"1 {modifier.strip()}"[:100]
    assert len(overlong_view.serving_label) == 100
    assert warnings == []


def test_unusable_usda_record_drops_while_sibling_matches_survive(monkeypatch) -> None:
    # The truncation keeps today's overlong labels valid, but any future
    # external-data/schema mismatch must still degrade one record to a
    # warning instead of failing the whole request. The injection below
    # simulates such a mismatch while building the bad record's view.
    from app.services import nutrition_lookup as lookup

    good = _fdc_food("187")
    good["fdcId"] = 170790
    good["description"] = "CHICK-FIL-A, Nuggets"
    bad = _fdc_food("187")
    bad["fdcId"] = 170791
    bad["description"] = "CHICK-FIL-A, Nuggets, 12 count"
    bad["foodPortions"] = [{"amount": 1, "modifier": "nuggets " * 15, "gramWeight": 187.0}]
    bad_page = lookup._FDC_PAGE.format(id=170791)
    real_view = lookup._view

    def view_rejecting_bad_record(*args: object, **kwargs: object) -> MatchView:
        if kwargs.get("source_url") == bad_page:
            MatchView.model_validate({"serving_label": "x" * 120})  # raises ValidationError
        return real_view(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(lookup, "_view", view_rejecting_bad_record)
    client = mock_client_with_details(
        {
            "foods": [
                {"fdcId": 170790, "description": good["description"], "dataType": "SR Legacy"},
                {"fdcId": 170791, "description": bad["description"], "dataType": "SR Legacy"},
            ]
        },
        {170790: good, 170791: bad},
    )

    matches, warnings = resolve_matches(
        raw(name="Chick-fil-A Nuggets", serving_grams="170", calories="380"),
        api_key="free-key",
        client=client,
    )

    # The unusable record drops with a warning; the sibling USDA match and the
    # web fallback keep the meal resolvable.
    assert [match.match_id for match in matches] == ["usda:170790", "web:0"]
    assert "USDA record was unusable" in warnings


def test_long_name_and_brand_are_truncated_to_schema_cap() -> None:
    food = _fdc_food("187")
    food["description"] = "N" * 250
    food["brandOwner"] = "B" * 250
    client = mock_client(
        {"foods": [{**search_hit(), "description": "CHICK-FIL-A, Nuggets"}]},
        food,
    )

    matches, _ = resolve_matches(
        raw(name="Chick-fil-A Nuggets", serving_grams="170", calories="380"),
        api_key="free-key",
        client=client,
    )

    assert len(matches[0].name) == 200
    assert len(matches[0].brand) == 200


def test_resolve_matches_ranks_and_explains_matches() -> None:
    first = _fdc_food("201")
    first["description"] = "CHICK-FIL-A, Nuggets"
    first["fdcId"] = 170790
    second = _fdc_food("170", omit_sugar=True)
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
        raw(name="12 ct Chick-fil-A Nuggets", serving_grams="170", calories="380"),
        api_key="free-key",
        client=client,
    )

    assert [match.rank for match in matches] == [1, 2, 3]
    assert matches[0].source_key == "170790"
    assert matches[0].rank_reasons == [
        "brand match",
        "name match",
        "complete macros",
        "USDA source",
    ]
    # Identity quality outranks completeness: the incomplete 12-count record stays
    # visible and still ranks ahead of the complete web match.
    assert matches[1].source_key == "170791"
    assert matches[1].incomplete is True
    assert matches[1].rank_reasons == ["brand match", "name match", "USDA source"]
    assert matches[2].match_id == "web:0"
    assert matches[2].source_key is None
    assert matches[2].rank_reasons == ["complete macros", "web source"]
    assert warnings == ["USDA record was incomplete"]
