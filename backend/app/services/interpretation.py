import httpx

from app.ai.provider import MealInterpreter
from app.schemas.interpretation import InterpretResponse
from app.services.nutrition_lookup import resolve_candidate

_MAX_CANDIDATES = 4


def interpret_description(
    description: str,
    interpreter: MealInterpreter,
    *,
    api_key: str = "DEMO_KEY",
    client: httpx.Client | None = None,
) -> InterpretResponse:
    """Interpret a description without touching the database."""
    raw_candidates = interpreter.interpret(description)
    candidates = []
    warnings: list[str] = []
    for raw in raw_candidates[:_MAX_CANDIDATES]:
        view, warning = resolve_candidate(raw, api_key=api_key, client=client)
        candidates.append(view)
        if warning:
            warnings.append(warning)
    return InterpretResponse(candidates=candidates, warnings=warnings)
