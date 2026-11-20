from concurrent.futures import ThreadPoolExecutor

import httpx

from app.ai.provider import MealInterpreter
from app.schemas.interpretation import CandidateView, InterpretResponse, RawCandidate
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
    selected: list[RawCandidate] = interpreter.interpret(description)[:_MAX_CANDIDATES]

    def resolve(raw: RawCandidate) -> tuple[CandidateView, str | None]:
        return resolve_candidate(raw, api_key=api_key, client=client)

    workers = min(_MAX_CANDIDATES, max(len(selected), 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        resolved = list(pool.map(resolve, selected))

    candidates = [view for view, _ in resolved]
    warnings = [warning for _, warning in resolved if warning]
    return InterpretResponse(candidates=candidates, warnings=warnings)
