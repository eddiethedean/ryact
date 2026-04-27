from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_getderivedstatefromerror_called_without_error_info_arg() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "does not provide component stack to the error boundary with getDerivedStateFromError"
    class Bomb(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, *args: object) -> dict[str, object] | None:  # noqa: N802
            assert len(args) == 1
            assert isinstance(args[0], BaseException)
            return {"hasError": True}

        def render(self) -> object:
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "ok"})
            return create_element(Bomb)

    root = create_noop_root()
    root.render(create_element(Boundary))
    assert root.container.last_committed["props"]["text"] == "ok"
