from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


@dataclass(frozen=True)
class Location:
    pathname: str = "/"
    search: str = ""
    hash: str = ""
    state: Any = None
    key: str = ""


class History:
    def push(self, to: str, state: Any = None) -> None:
        raise NotImplementedError("ryact-router-dom is a scaffold; no history implementation yet.")

    def replace(self, to: str, state: Any = None) -> None:
        raise NotImplementedError("ryact-router-dom is a scaffold; no history implementation yet.")


def create_browser_history() -> History:
    raise NotImplementedError("ryact-router-dom is a scaffold; no browser history yet.")


def BrowserRouter(
    props: Optional[Mapping[str, Any]] = None,
    *children: Any,
    **kwargs: Any,
) -> Any:
    raise NotImplementedError("ryact-router-dom is a scaffold; BrowserRouter is not implemented.")


def Routes(
    props: Optional[Mapping[str, Any]] = None,
    *children: Any,
    **kwargs: Any,
) -> Any:
    raise NotImplementedError("ryact-router-dom is a scaffold; Routes is not implemented.")


def Route(
    props: Optional[Mapping[str, Any]] = None,
    *children: Any,
    **kwargs: Any,
) -> Any:
    raise NotImplementedError("ryact-router-dom is a scaffold; Route is not implemented.")


def Link(
    props: Optional[Mapping[str, Any]] = None,
    *children: Any,
    **kwargs: Any,
) -> Any:
    raise NotImplementedError("ryact-router-dom is a scaffold; Link is not implemented.")


def use_location() -> Location:
    raise NotImplementedError("ryact-router-dom is a scaffold; use_location is not implemented.")


def use_navigate() -> Callable[[str], None]:
    raise NotImplementedError("ryact-router-dom is a scaffold; use_navigate is not implemented.")


def use_params() -> Mapping[str, str]:
    raise NotImplementedError("ryact-router-dom is a scaffold; use_params is not implemented.")


__all__ = [
    "BrowserRouter",
    "History",
    "Link",
    "Location",
    "Route",
    "Routes",
    "create_browser_history",
    "use_location",
    "use_navigate",
    "use_params",
]

