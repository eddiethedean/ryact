from __future__ import annotations

from ryact import create_element
from ryact.concurrent import lazy


def test_create_element_with_lazy_does_not_invoke_loader() -> None:
    # Upstream: ReactElementValidator-test.internal.js — "does not call lazy initializers eagerly"
    called: dict[str, bool] = {"v": False}

    def loader() -> object:
        called["v"] = True

        def Inner(**_props: object) -> object:
            return None

        return Inner

    create_element(lazy(loader), {})
    assert not called["v"]
