from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root


def test_setstate_callback_only_fires_once() -> None:
    # Upstream: ReactClassSetStateCallback-test.js —
    # "regression: setState callback (2nd arg) should only fire once, even after a rebase"
    calls: list[str] = []

    class App(Component):
        def componentDidMount(self) -> None:  # noqa: N802
            self.set_state({"n": 1}, callback=lambda: calls.append("cb"))

        def render(self) -> object:
            return create_element("div", {"text": str(self.state.get("n", 0))})

    root = create_noop_root()
    root.render(create_element(App))

    # Flush the scheduled update.
    root.flush()
    assert calls == ["cb"]

    # Flushing again (even if a "rebase-like" extra render occurs in some models)
    # must not re-run the same callback.
    root.flush()
    assert calls == ["cb"]

