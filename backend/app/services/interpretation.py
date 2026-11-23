from concurrent.futures import ThreadPoolExecutor

import httpx

from app.ai.provider import MealInterpreter
from app.schemas.interpretation import FoodMatchGroup, InterpretResponse, MatchView, RawCandidate
from app.services.nutrition_lookup import resolve_matches

_MAX_CANDIDATES = 4


def interpret_description(
    description: str,
    interpreter: MealInterpreter,
    *,
    api_key: str = "DEMO_KEY",
    client: httpx.Client | None = None,
) -> InterpretResponse:
    """Interpret a description without touching the database."""
    selected: list[RawCandidate] = interpreter.interpret(description)[:_MAX_CANDIDATES]

    def resolve(raw: RawCandidate) -> tuple[list[MatchView], list[str]]:
        return resolve_matches(raw, api_key=api_key, client=client)

    workers = min(_MAX_CANDIDATES, max(len(selected), 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        resolved = list(pool.map(resolve, selected))

    groups = [
        FoodMatchGroup(
            group_id=str(index),
            label=raw.name,
            quantity=raw.quantity,
            matches=matches,
        )
        for index, (raw, (matches, _)) in enumerate(zip(selected, resolved, strict=True))
    ]
    warnings = list(
        dict.fromkeys(warning for _, group_warnings in resolved for warning in group_warnings)
    )
    return InterpretResponse(groups=groups, warnings=warnings)
