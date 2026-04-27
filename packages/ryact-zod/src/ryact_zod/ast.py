from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict


class Issue(TypedDict):
    path: list[object]
    code: str
    message: str


UnknownKeys = Literal["strip", "passthrough", "strict"]

# For cross-lane portability (JSON) and simpler typing, we treat the AST node as an
# unstructured dict at the type level. The AST "spec" is enforced by validator tests.
Node = dict[str, Any]


@dataclass(frozen=True)
class ParseResult:
    success: bool
    data: Any | None
    issues: list[Issue]

