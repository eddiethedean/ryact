from __future__ import annotations

import warnings
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class WarningCapture(AbstractContextManager):
    records: List[warnings.WarningMessage]

    def __init__(self) -> None:
        self.records = []
        self._cm = None

    def __enter__(self) -> "WarningCapture":
        self._cm = warnings.catch_warnings(record=True)
        self.records = self._cm.__enter__()  # type: ignore[assignment]
        warnings.simplefilter("always")
        return self

    def __exit__(self, exc_type, exc, tb) -> Optional[bool]:
        assert self._cm is not None
        return self._cm.__exit__(exc_type, exc, tb)

