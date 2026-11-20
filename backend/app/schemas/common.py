from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def _as_string(value: Decimal) -> str:
    return str(value)


DecimalText = Annotated[Decimal, PlainSerializer(_as_string, return_type=str, when_used="json")]
