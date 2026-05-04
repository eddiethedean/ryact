from __future__ import annotations

from ryact import Component, create_element
from ryact_testkit import create_noop_root
from ryact_testkit.warnings import WarningCapture


def test_should_ignore_error_if_it_doesnt_throw_on_retry() -> None:
    # Upstream: ReactIncrementalErrorReplay-test.js
    # "should ignore error if it doesn't throw on retry"
    did_init = False

    def bad_lazy_init() -> None:
        nonlocal did_init
        needs_init = not did_init
        did_init = True
        if needs_init:
            raise RuntimeError("Hi")

    class App(Component):
        def render(self) -> object:
            bad_lazy_init()
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(App))
    wc.assert_any("recover")
