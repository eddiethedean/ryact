from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Ref(Generic[T]):
    current: T | None = None


def create_ref() -> Ref[object]:
    return Ref()
