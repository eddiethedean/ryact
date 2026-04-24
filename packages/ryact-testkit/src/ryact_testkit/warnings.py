from __future__ import annotations

import warnings
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Optional


def emit_warning(
    message: str,
    *,
    category: type[Warning] = RuntimeWarning,
    stacklevel: int = 2,
) -> None:
    warnings.warn(message, category, stacklevel=stacklevel)


def format_warnings(records: list[warnings.WarningMessage]) -> list[str]:
    return [str(r.message) for r in records]


@dataclass
class WarningCapture(AbstractContextManager):
    records: list[warnings.WarningMessage]

    def __init__(self) -> None:
        self.records = []
        self._cm: Optional[AbstractContextManager[list[warnings.WarningMessage]]] = None

    def __enter__(self) -> WarningCapture:
        self._cm = warnings.catch_warnings(record=True)
        self.records = self._cm.__enter__()
        warnings.simplefilter("always")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        assert self._cm is not None
        return self._cm.__exit__(exc_type, exc, tb)

    @property
    def messages(self) -> list[str]:
        return format_warnings(self.records)

    def assert_any(self, substring: str) -> None:
        sub = substring.lower()
        if not any(sub in m.lower() for m in self.messages):
            raise AssertionError(
                f"Expected warning containing {substring!r}; got: {self.messages!r}"
            )
