from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_catches_reconciler_errors_in_a_boundary_during_mounting() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "catches reconciler errors in a boundary during mounting"
    #
    # Noop host maps failing child work during mount into the same error-boundary path
    # as render-time throws for this slice.
    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("span", {"text": "recovered"})
            return create_element(Bomb)

    root = create_noop_root()
    root.render(create_element(Boundary))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["type"] == "span"
    assert committed["props"]["text"] == "recovered"
