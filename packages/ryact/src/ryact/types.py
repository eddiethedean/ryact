from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, TypeVar

TProps = TypeVar("TProps", bound=Mapping[str, Any], covariant=True)

# Public typing helpers (keep stable and lightweight).
Props = Mapping[str, Any]
Key = str | None
Ref = Any | None


class FunctionComponent(Protocol[TProps]):
    def __call__(self, **props: Any) -> Any: ...


if TYPE_CHECKING:  # pragma: no cover
    from .element import Element

    Renderable: TypeAlias = Element[Any, Mapping[str, Any]] | str | int | float | None
else:
    Renderable = Any
