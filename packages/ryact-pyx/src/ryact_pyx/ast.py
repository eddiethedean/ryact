from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class Expr:
    source: str


@dataclass(frozen=True)
class Element:
    tag: str
    attrs: dict[str, Any]
    children: list[Any]


@dataclass(frozen=True)
class Root:
    children: list[Any]


Node = Text | Expr | Element | Root
