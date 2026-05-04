from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

TState = TypeVar("TState")


Subscriber = Callable[[TState, TState], None]
Unsubscribe = Callable[[], None]


@dataclass(frozen=True)
class StoreApi(Generic[TState]):
    get_state: Callable[[], TState]
    set_state: Callable[[Callable[[TState], TState] | TState, bool], None]
    subscribe: Callable[[Subscriber[TState]], Unsubscribe]


def create_store(*, initial_state: TState) -> StoreApi[TState]:
    raise NotImplementedError("ryact-zustand is a scaffold; create_store is not implemented.")


def use_store(store: StoreApi[TState], selector: Optional[Callable[[TState], Any]] = None) -> Any:
    raise NotImplementedError("ryact-zustand is a scaffold; use_store is not implemented.")


__all__ = ["StoreApi", "create_store", "use_store"]
