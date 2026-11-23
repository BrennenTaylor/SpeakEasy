from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, cast

import httpx

from app.domain.nutrition import MACRO_FIELDS, _quantize
from app.schemas.interpretation import CandidateView, RawCandidate

_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_FOOD_URL = "https://api.nal.usda.gov/fdc/v1/food"
_FDC_PAGE = "https://fdc.nal.usda.gov/fdc-app.html#/food-details/{id}/nutrients"
_LOOKUP_TIMEOUT_SECONDS = 3.0
_ALLOWED_DATA_TYPES = {"Branded", "SR Legacy"}
_NUTRIENT_MATCHES: dict[str, tuple[str, str]] = {
    "calories": ("energy", "KCAL"),
    "protein_g": ("protein", "G"),
    "carbs_g": ("carbohydrate", "G"),
    "fat_g": ("total lipid", "G"),
    "fiber_g": ("fiber", "G"),
    "sugar_g": ("sugars", "G"),
    "sodium_mg": ("sodium", "MG"),
}
_NUTRIENT_PREFERRED: dict[str, str] = {
    "calories": "energy",
    "protein_g": "protein",
    "carbs_g": "carbohydrate, by difference",
    "fat_g": "total lipid (fat)",
    "fiber_g": "fiber, total dietary",
    "sugar_g": "sugars, total including nlea",
    "sodium_mg": "sodium, na",
}
_NUTRIENT_EXCLUDED: dict[str, tuple[str, ...]] = {
    "carbs_g": ("by summation",),
    "fat_g": ("saturated", "monounsaturated", "polyunsaturated", "trans"),
    "fiber_g": ("soluble", "insoluble"),
    "sugar_g": ("added",),
}


def _as_dict(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def _as_list(value: object) -> list[Any] | None:
    return value if isinstance(value, list) else None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


_SIZE_TOKENS = {
    "box",
    "count",
    "ct",
    "cup",
    "cups",
    "large",
    "medium",
    "piece",
    "pieces",
    "regular",
    "serving",
    "servings",
    "small",
}


def _stem(token: str) -> str:
    return token[:-1] if len(token) > 3 and token.endswith("s") else token


def _tokens(text: str) -> set[str]:
    return {
        _stem(token) for token in _normalize(text).split() if len(token) > 1 and not token.isdigit()
    }


def _food_tokens(raw: RawCandidate) -> set[str]:
    brand_tokens = set(_normalize(raw.brand).split())
    return {
        token
        for token in _tokens(raw.name)
        if token not in brand_tokens and token not in _SIZE_TOKENS
    }


def _brand_matches(raw: RawCandidate, food: dict[str, Any]) -> bool:
    brand = _normalize(raw.brand)
    if brand:
        fields = (food.get("brandOwner"), food.get("brandName"), food.get("description"))
        return any(brand in _normalize(str(value)) for value in fields if value)
    # The AI is not required to populate brand, so an empty brand must not wave a
    # Branded record through uncorroborated: require at least one candidate-name
    # token to overlap the record's brand fields. SR Legacy stays food-token-gated.
    if food.get("dataType") == "Branded":
        owner_tokens = _tokens(str(food.get("brandOwner") or "")) | _tokens(
            str(food.get("brandName") or "")
        )
        return bool(_tokens(raw.name) & owner_tokens)
    return True


def _food_matches(raw: RawCandidate, food: dict[str, Any]) -> bool:
    wanted = _food_tokens(raw)
    if not wanted:
        return True
    description = _tokens(str(food.get("description") or ""))
    return bool(wanted & description)


def _format_amount(amount: Decimal) -> str:
    if amount == amount.to_integral_value():
        return str(int(amount))
    return format(amount.normalize(), "f")


def _portion(food: dict[str, Any]) -> tuple[str, Decimal] | None:
    for entry in _as_list(food.get("foodPortions")) or []:
        portion = _as_dict(entry)
        if portion is None:
            continue
        grams = _decimal(portion.get("gramWeight"))
        if grams is None or grams <= 0:
            continue
        amount = _decimal(portion.get("amount")) or Decimal(1)
        modifier = str(portion.get("modifier") or "").strip()
        label = f"{_format_amount(amount)} {modifier or 'serving'}"
        return label, _quantize(grams)

    serving_size = _decimal(food.get("servingSize"))
    unit = str(food.get("servingSizeUnit") or "").upper()
    if serving_size is not None and serving_size > 0 and unit == "G":
        label = str(food.get("householdServingFullText") or "").strip()
        if not label:
            label = f"{_format_amount(serving_size)} g"
        return label, _quantize(serving_size)
    return None


def _nutrient_amounts(food: dict[str, Any], portion_grams: Decimal) -> dict[str, Decimal | None]:
    best: dict[str, tuple[int, Decimal] | None] = {field: None for field in MACRO_FIELDS}
    factor = portion_grams / Decimal(100)
    for entry in _as_list(food.get("foodNutrients")) or []:
        item = _as_dict(entry)
        nutrient = _as_dict(item.get("nutrient")) if item is not None else None
        if nutrient is None:
            continue
        name = _normalize(str(nutrient.get("name") or ""))
        unit = str(nutrient.get("unitName") or "").upper()
        amount = _decimal(item.get("amount")) if item is not None else None
        if amount is None:
            continue
        for field, (needle, expected_unit) in _NUTRIENT_MATCHES.items():
            if needle not in name or unit != expected_unit:
                continue
            if any(excluded in name for excluded in _NUTRIENT_EXCLUDED.get(field, ())):
                continue
            score = 2 if name == _NUTRIENT_PREFERRED.get(field) else 1
            current = best[field]
            if current is None or score > current[0]:
                best[field] = (score, amount * factor)
            break
    return {
        field: _quantize(match[1]) if match is not None else None for field, match in best.items()
    }


def _fdc_id(item: dict[str, Any]) -> int | None:
    value = item.get("fdcId")
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _rank_foods(foods: list[Any], raw: RawCandidate) -> list[dict[str, Any]]:
    wanted = _normalize(raw.name)
    wanted_tokens = _tokens(raw.name)
    ranked: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    for entry in foods:
        food = _as_dict(entry)
        if food is None:
            continue
        if food.get("dataType") not in _ALLOWED_DATA_TYPES:
            continue
        if not _brand_matches(raw, food) or not _food_matches(raw, food):
            continue
        description = _normalize(str(food.get("description") or ""))
        exact = 0 if wanted in description or description in wanted else 1
        overlap = len(wanted_tokens & set(description.split()))
        key = (exact, -overlap, str(food.get("fdcId", "")))
        ranked.append((key, food))
    ranked.sort(key=lambda pair: pair[0])
    return [food for _, food in ranked]


def _view(
    values: dict[str, Decimal | None],
    missing: list[str],
    *,
    raw: RawCandidate,
    serving_label: str,
    serving_grams: Decimal,
    source: str,
    source_url: str | None,
    confidence: str,
) -> CandidateView:
    payload: dict[str, object] = {
        "name": raw.name,
        "brand": raw.brand,
        "serving_label": serving_label,
        "serving_grams": _quantize(serving_grams),
        "quantity": _quantize(raw.quantity),
        "source": source,
        "source_url": source_url,
        "confidence": confidence,
        "incomplete": bool(missing),
        "missing_fields": missing,
    }
    payload.update({field: values.get(field) for field in MACRO_FIELDS})
    return CandidateView.model_validate(payload)


def _web_view(raw: RawCandidate) -> tuple[CandidateView, str | None]:
    url = str(raw.source_url) if raw.source_url is not None else None
    valid_url = url is not None and url.startswith(("http://", "https://")) and len(url) <= 500
    if valid_url:
        values: dict[str, Decimal | None] = {
            field: _quantize(getattr(raw, field)) for field in MACRO_FIELDS
        }
        return (
            _view(
                values,
                [],
                raw=raw,
                serving_label=raw.serving_label,
                serving_grams=raw.serving_grams,
                source="web_search",
                source_url=url,
                confidence="low",
            ),
            None,
        )
    return (
        _view(
            {field: None for field in MACRO_FIELDS},
            ["source_url", *MACRO_FIELDS],
            raw=raw,
            serving_label=raw.serving_label,
            serving_grams=raw.serving_grams,
            source="web_search",
            source_url=None,
            confidence="low",
        ),
        "Web result has no valid source_url",
    )


def _resolve_usda(
    raw: RawCandidate, api_key: str, client: httpx.Client
) -> tuple[CandidateView | None, str | None]:
    try:
        response = client.get(
            _SEARCH_URL,
            params={
                "query": raw.name,
                "api_key": api_key,
                "pageSize": 5,
                "dataType": list(_ALLOWED_DATA_TYPES),
            },
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return None, "USDA lookup unavailable"
    if response.status_code != 200:
        return None, f"USDA lookup returned {response.status_code}"
    try:
        search_payload: object = response.json()
    except ValueError:
        return None, "USDA lookup returned invalid JSON"
    search_data = _as_dict(search_payload)
    foods = _as_list(search_data.get("foods")) if search_data is not None else None
    if not foods:
        return None, "No USDA match found"

    ranked = _rank_foods(foods, raw)
    if not ranked:
        return None, "No USDA match found"
    fdc_id = _fdc_id(ranked[0])
    if fdc_id is None:
        return None, "USDA match had no id"

    try:
        detail_response = client.get(
            f"{_FOOD_URL}/{fdc_id}",
            params={"api_key": api_key},
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return None, "USDA lookup unavailable"
    if detail_response.status_code != 200:
        return None, f"USDA lookup returned {detail_response.status_code}"
    try:
        detail_payload: object = detail_response.json()
    except ValueError:
        return None, "USDA lookup returned invalid JSON"
    food = _as_dict(detail_payload)
    if food is None:
        return None, "USDA record was unusable"

    portion = _portion(food)
    if portion is None:
        return None, "USDA record had no portion"
    serving_label, serving_grams = portion
    values = _nutrient_amounts(food, serving_grams)
    missing = [field for field in MACRO_FIELDS if values[field] is None]
    page_url = _FDC_PAGE.format(id=fdc_id)
    return (
        _view(
            values,
            missing,
            raw=raw,
            serving_label=serving_label,
            serving_grams=serving_grams,
            source="usda_fdc",
            source_url=page_url,
            confidence="high" if not missing else "low",
        ),
        None if not missing else "USDA record was incomplete",
    )


def resolve_candidate(
    raw: RawCandidate,
    *,
    api_key: str = "DEMO_KEY",
    client: httpx.Client | None = None,
) -> tuple[CandidateView, str | None]:
    """Resolve a candidate from USDA first, then from the sourced web result."""
    owns_client = client is None
    lookup_client = client or httpx.Client()
    try:
        usda_view, usda_warning = _resolve_usda(raw, api_key, lookup_client)
    finally:
        if owns_client:
            lookup_client.close()

    if usda_view is not None and not usda_view.incomplete:
        return usda_view, None

    web_view, web_warning = _web_view(raw)
    if web_view is not None and not web_view.incomplete:
        warning = usda_warning or "USDA record was incomplete; used web source"
        return web_view, warning

    if usda_view is not None:
        missing = list(dict.fromkeys([*usda_view.missing_fields, *web_view.missing_fields]))
        values = {field: getattr(usda_view, field) for field in MACRO_FIELDS}
        return (
            _view(
                values,
                missing,
                raw=raw,
                serving_label=usda_view.serving_label,
                serving_grams=usda_view.serving_grams,
                source="usda_fdc",
                source_url=str(usda_view.source_url) if usda_view.source_url else None,
                confidence="low",
            ),
            usda_warning or web_warning,
        )
    warnings = [warning for warning in (usda_warning, web_warning) if warning]
    return web_view, "; ".join(warnings) or None
