from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


@dataclass(frozen=True)
class TailwindResult:
    class_name: str
    style: Mapping[str, object]


def tw(class_name: str, *, theme: Optional[Mapping[str, object]] = None) -> TailwindResult:
    """
    Placeholder entrypoint.

    In the long run, this compiles a Tailwind-like class string into a style dict
    suitable for ryact-dom/native renderers.
    """
    raise NotImplementedError("ryact-tailwindcss is a scaffold; tw() is not implemented.")


__all__ = ["TailwindResult", "tw"]

