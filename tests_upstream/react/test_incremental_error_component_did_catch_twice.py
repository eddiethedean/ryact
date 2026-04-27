from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_component_did_catch_runs_twice_for_two_mount_errors() -> None:
    # Upstream: ReactIncrementalErrorHandling-test.internal.js
    # "calls componentDidCatch multiple times for multiple errors"
    log: list[str] = []

    class Bad(Component):
        def render(self) -> object:
            raise RuntimeError("boom")

    class Boundary(Component):
        @classmethod
        def getDerivedStateFromError(cls, _err: BaseException) -> dict[str, object] | None:  # noqa: N802
            return {"hasError": True}

        def componentDidCatch(self, _err: BaseException) -> None:  # noqa: N802
            log.append("didCatch")
            n = int(self.state.get("n", 0)) + 1
            if n == 1:
                self.set_state({"n": n, "hasError": False, "retryKey": 1})
            else:
                self.set_state({"n": n, "settled": True})

        def render(self) -> object:
            if bool(self.state.get("settled")):
                return create_element("div", {"text": "done"})
            if bool(self.state.get("hasError")):
                return create_element("div", {"text": "fb"})
            return create_element(Bad, {"key": int(self.state.get("retryKey", 0))})

    root = create_noop_root()
    root.render(create_element(Boundary))
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "fb"},
        "children": [],
    }
    root.flush()
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "done"},
        "children": [],
    }
    assert log == ["didCatch", "didCatch"]
