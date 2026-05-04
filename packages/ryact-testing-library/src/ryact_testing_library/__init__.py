from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class RenderResult:
    container: object

    def debug(self) -> str:
        raise NotImplementedError(
            "ryact-testing-library is a scaffold; debug() is not implemented."
        )


def render(element: Any) -> RenderResult:
    raise NotImplementedError("ryact-testing-library is a scaffold; render() is not implemented.")


def get_by_text(container: object, text: str) -> object:
    raise NotImplementedError(
        "ryact-testing-library is a scaffold; get_by_text is not implemented."
    )


def query_by_text(container: object, text: str) -> Optional[object]:
    raise NotImplementedError(
        "ryact-testing-library is a scaffold; query_by_text is not implemented."
    )


__all__ = [
    "RenderResult",
    "get_by_text",
    "query_by_text",
    "render",
]
