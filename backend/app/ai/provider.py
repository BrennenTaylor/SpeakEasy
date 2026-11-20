from typing import Protocol

from app.schemas.interpretation import RawCandidate


class AIServiceError(RuntimeError):
    """Raised when the AI provider is unavailable or returns unusable output."""


class MealInterpreter(Protocol):
    def interpret(self, description: str) -> list[RawCandidate]: ...
