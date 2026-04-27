from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


class _NotAnError(Exception):
    """Upstream uses a thrown object with ``nonStandardMessage``; model as Exception subclass."""

    def __init__(self) -> None:
        super().__init__("legacy")
        self.nonStandardMessage = "oops"


def test_error_boundaries_capture_non_errors() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "error boundaries capture non-errors"
    log: list[str] = []

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"error": err}

        def componentDidCatch(self, err: BaseException) -> None:  # noqa: N802
            log.append("componentDidCatch")
            assert isinstance(err, _NotAnError)

        def render(self) -> object:
            if "error" in self.state:
                err = self.state["error"]
                assert isinstance(err, _NotAnError)
                msg = err.nonStandardMessage
                return create_element("span", {"text": f"Caught an error: {msg}"})
            ch = self.props.get("children") or ()
            return ch[0] if ch else None

    class Bad(Component):
        def render(self) -> object:
            raise _NotAnError()

    root = create_noop_root()
    root.render(create_element(Boundary, None, create_element(Bad)))
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "Caught an error: oops"},
        "children": [],
    }
    assert log == ["componentDidCatch"]
