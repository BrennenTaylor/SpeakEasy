from app.ai.openai_provider import OpenAIInterpreter
from app.ai.provider import MealInterpreter
from app.core.config import get_settings


def get_interpreter() -> MealInterpreter | None:
    """Return a server-side interpreter, or None when AI is not configured."""
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAIInterpreter(
        api_key=settings.openai_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
