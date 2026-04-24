from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Suspense:
    fallback: Any
    children: Any


@dataclass
class Transition:
    name: str = "default"


_in_transition = False


def start_transition(fn: Callable[[], None]) -> None:
    global _in_transition
    prev = _in_transition
    _in_transition = True
    try:
        fn()
    finally:
        _in_transition = prev


def is_in_transition() -> bool:
    return _in_transition


class Lazy:
    def __init__(self, loader: Callable[[], Any]) -> None:
        self._loader = loader
        self._resolved = False
        self._value: Any | None = None

    def get(self) -> Any:
        if not self._resolved:
            self._value = self._loader()
            self._resolved = True
        return self._value
