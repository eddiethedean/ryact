from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class QueryKey:
    parts: tuple[object, ...]


@dataclass(frozen=True)
class QueryResult(Generic[T]):
    data: Optional[T]
    error: Optional[BaseException]
    is_loading: bool


class QueryClient:
    def __init__(self) -> None:
        raise NotImplementedError("ryact-query is a scaffold; QueryClient is not implemented.")


def use_query(
    *,
    query_key: QueryKey,
    query_fn: Callable[[], T],
    enabled: bool = True,
    initial_data: Optional[T] = None,
    meta: Optional[Mapping[str, Any]] = None,
) -> QueryResult[T]:
    raise NotImplementedError("ryact-query is a scaffold; use_query is not implemented.")


__all__ = ["QueryClient", "QueryKey", "QueryResult", "use_query"]
