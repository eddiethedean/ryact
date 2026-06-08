"""DEV-only frozen ``style`` objects (ReactDOMComponent parity)."""

from __future__ import annotations

from typing import Any


class FrozenStyleDict(dict[str, Any]):
    """Shallow-frozen style mapping; mutations raise like React frozen style objects."""

    def __setitem__(self, key: str, value: Any) -> None:
        raise TypeError("Can not mutate a frozen style object.")

    def __delitem__(self, key: str) -> None:
        raise TypeError("Can not mutate a frozen style object.")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Can not mutate a frozen style object.")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Can not mutate a frozen style object.")

    def popitem(self) -> tuple[str, Any]:
        raise TypeError("Can not mutate a frozen style object.")

    def clear(self) -> None:
        raise TypeError("Can not mutate a frozen style object.")

    def setdefault(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Can not mutate a frozen style object.")
