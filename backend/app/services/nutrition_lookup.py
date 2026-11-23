from __future__ import annotations

import string
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
from typing import Any, NamedTuple, cast

import httpx

from app.domain.nutrition import MACRO_FIELDS, _quantize
from app.schemas.interpretation import MatchView, RawCandidate

_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_FOOD_URL = "https://api.nal.usda.gov/fdc/v1/food"
_FDC_PAGE = "https://fdc.nal.usda.gov/fdc-app.html#/food-details/{id}/nutrients"
_LOOKUP_TIMEOUT_SECONDS = 3.0
_USDA_PAGE_SIZE = 10
_USDA_DETAIL_WORKERS = 4
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
    # Strip edge punctuation so FDC values like "Chick-fil-A, Inc." tokenize as
    # "chick-fil-a"/"inc" and can overlap candidate tokens; interior hyphens are
    # meaningful and survive.
    cleaned = (token.strip(string.punctuation) for token in _normalize(text).split())
    return {_stem(token) for token in cleaned if len(token) > 1 and not token.isdigit()}


def _food_tokens(raw: RawCandidate) -> set[str]:
    brand_tokens = _tokens(raw.brand)
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


def _exact_name_score(wanted: str, shown: str) -> int:
    """0 when either normalized name contains the other, else 1. Lower is better."""
    return 0 if wanted in shown or shown in wanted else 1


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
        exact = _exact_name_score(wanted, description)
        overlap = len(wanted_tokens & _tokens(description))
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
    name: str | None = None,
    brand: str | None = None,
) -> MatchView:
    payload: dict[str, object] = {
        # name/brand default to the AI candidate's claim; USDA callers override
        # them with the source record's own identity.
        "name": raw.name if name is None else name,
        "brand": raw.brand if brand is None else brand,
        "serving_label": serving_label,
        "serving_grams": _quantize(serving_grams),
        "quantity": _quantize(raw.quantity),
        "source": source,
        "source_url": source_url,
        "confidence": confidence,
        "incomplete": bool(missing),
        "missing_fields": missing,
        # Provisional match metadata: resolve_matches assigns the final values
        # via _match_view before any view leaves this module.
        "match_id": "",
        "source_key": None,
        "rank": 1,
        "rank_reasons": [],
    }
    payload.update({field: values.get(field) for field in MACRO_FIELDS})
    return MatchView.model_validate(payload)


def _web_view(raw: RawCandidate) -> tuple[MatchView, str | None]:
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


def _match_view(
    view: MatchView,
    *,
    match_id: str,
    source_key: str | None,
    rank: int,
    rank_reasons: list[str],
) -> MatchView:
    payload = view.model_dump()
    payload.update(
        {
            "match_id": match_id,
            "source_key": source_key,
            "rank": rank,
            "rank_reasons": rank_reasons,
        }
    )
    return MatchView.model_validate(payload)


def _fdc_page_id(source_url: object) -> str | None:
    """Recover the FDC id from a detail-page URL built by this module."""
    if source_url is None:
        return None
    marker = "/food-details/"
    text = str(source_url)
    if marker not in text:
        return None
    return text.split(marker, 1)[1].split("/", 1)[0] or None


def _rank_reasons(raw: RawCandidate, view: MatchView) -> list[str]:
    reasons: list[str] = []
    if view.source == "usda_fdc":
        brand = _normalize(raw.brand)
        corroborated = (
            any(brand in _normalize(field) for field in (view.brand, view.name))
            if brand
            else bool(_tokens(raw.name) & _tokens(view.brand))
        )
        if corroborated:
            reasons.append("brand match")
        exact = _exact_name_score(_normalize(raw.name), _normalize(view.name)) == 0
        if exact or _food_tokens(raw) & _tokens(view.name):
            reasons.append("name match")
    if not view.incomplete:
        reasons.append("complete macros")
    reasons.append("USDA source" if view.source == "usda_fdc" else "web source")
    return reasons


def _fetch_usda_detail(
    raw: RawCandidate,
    fdc_id: int,
    hit: dict[str, Any],
    api_key: str,
    client: httpx.Client,
) -> tuple[MatchView | None, str | None]:
    try:
        response = client.get(
            f"{_FOOD_URL}/{fdc_id}",
            params={"api_key": api_key},
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return None, "USDA lookup unavailable"
    if response.status_code != 200:
        return None, f"USDA lookup returned {response.status_code}"
    try:
        detail_payload: object = response.json()
    except ValueError:
        return None, "USDA lookup returned invalid JSON"
    food = _as_dict(detail_payload)
    if food is None:
        return None, "USDA record was unusable"
    portion = _portion(food)
    if portion is None:
        return None, "USDA record had no portion"
    serving_label, serving_grams = portion
    # Cards show the source record's own identity; the schema caps display text
    # at 200 chars. Truncation never touches nutrient values.
    name = str(food.get("description") or hit.get("description") or "").strip()[:200]
    if not name:
        return None, "USDA record was unusable"
    brand = str(food.get("brandOwner") or food.get("brandName") or "").strip()[:200]
    values = _nutrient_amounts(food, serving_grams)
    missing = [field for field in MACRO_FIELDS if values[field] is None]
    return (
        _view(
            values,
            missing,
            raw=raw,
            serving_label=serving_label,
            serving_grams=serving_grams,
            source="usda_fdc",
            source_url=_FDC_PAGE.format(id=fdc_id),
            confidence="high" if not missing else "low",
            name=name,
            brand=brand,
        ),
        "USDA record was incomplete" if missing else None,
    )


def _resolve_usda_matches(
    raw: RawCandidate, api_key: str, client: httpx.Client
) -> tuple[list[MatchView], list[str]]:
    """Resolve every USDA record that survives the identity gate, in rank order."""
    try:
        response = client.get(
            _SEARCH_URL,
            params={
                "query": raw.name,
                "api_key": api_key,
                "pageSize": _USDA_PAGE_SIZE,
                "dataType": list(_ALLOWED_DATA_TYPES),
            },
            timeout=_LOOKUP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        return [], ["USDA lookup unavailable"]
    if response.status_code != 200:
        return [], [f"USDA lookup returned {response.status_code}"]
    try:
        search_payload: object = response.json()
    except ValueError:
        return [], ["USDA lookup returned invalid JSON"]
    search_data = _as_dict(search_payload)
    foods = _as_list(search_data.get("foods")) if search_data is not None else None
    ranked = _rank_foods(foods or [], raw)

    # Deduplicate by FDC ID only; never deduplicate across sources.
    accepted: list[tuple[int, dict[str, Any]]] = []
    warnings: list[str] = []
    seen: set[int] = set()
    for food in ranked:
        fdc_id = _fdc_id(food)
        if fdc_id is None:
            warnings.append("USDA match had no id")
        elif fdc_id not in seen:
            seen.add(fdc_id)
            accepted.append((fdc_id, food))
    if not accepted:
        return [], warnings or ["No USDA match found"]

    def fetch(item: tuple[int, dict[str, Any]]) -> tuple[MatchView | None, str | None]:
        detail_id, hit = item
        return _fetch_usda_detail(raw, detail_id, hit, api_key, client)

    # pool.map preserves input order, so results stay deterministic in rank order.
    with ThreadPoolExecutor(max_workers=min(_USDA_DETAIL_WORKERS, len(accepted))) as pool:
        fetched = list(pool.map(fetch, accepted))

    views: list[MatchView] = []
    for view, warning in fetched:
        if view is not None:
            views.append(view)
        if warning is not None:
            warnings.append(warning)
    return views, warnings


class _Entry(NamedTuple):
    identity: int
    view: MatchView
    match_id: str
    source_key: str | None


def resolve_matches(
    raw: RawCandidate,
    *,
    api_key: str = "DEMO_KEY",
    client: httpx.Client | None = None,
) -> tuple[list[MatchView], list[str]]:
    """Resolve every source-backed match for one raw candidate, best first."""
    owns_client = client is None
    lookup_client = client or httpx.Client()
    try:
        usda_views, warnings = _resolve_usda_matches(raw, api_key, lookup_client)
    finally:
        if owns_client:
            lookup_client.close()

    entries: list[_Entry] = []
    for index, view in enumerate(usda_views):
        fdc_key = _fdc_page_id(view.source_url)
        if fdc_key is None:
            continue  # unreachable: USDA views always carry this module's FDC page URL
        entries.append(_Entry(index, view, f"usda:{fdc_key}", fdc_key))

    web_view, web_warning = _web_view(raw)
    if web_warning is not None:
        warnings.append(web_warning)
    if web_view.source_url is not None or not usda_views:
        # The web card repeats the AI's own name, so its exact-name score is
        # self-referential evidence; offset it past every source-checked USDA
        # identity so it never interleaves with the ranked USDA group.
        identity = len(usda_views) + _exact_name_score(
            _normalize(raw.name), _normalize(web_view.name)
        )
        entries.append(_Entry(identity, web_view, "web:0", None))

    # Identity score first, then complete before incomplete, then USDA before
    # web, then match_id: a deterministic total order.
    entries.sort(
        key=lambda entry: (
            entry.identity,
            entry.view.incomplete,
            entry.view.source != "usda_fdc",
            entry.match_id,
        )
    )
    matches = [
        _match_view(
            entry.view,
            match_id=entry.match_id,
            source_key=entry.source_key,
            rank=rank,
            rank_reasons=_rank_reasons(raw, entry.view),
        )
        for rank, entry in enumerate(entries, start=1)
    ]
    return matches, list(dict.fromkeys(warnings))
