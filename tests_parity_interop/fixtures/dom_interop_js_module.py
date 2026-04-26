from __future__ import annotations

from ryact import create_element


def render(scope: dict[str, object]) -> object:
    return create_element("div", {"id": scope.get("id")})
