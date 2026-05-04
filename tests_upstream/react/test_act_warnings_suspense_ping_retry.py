from __future__ import annotations

import pytest
from ryact import create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import WarningCapture, act, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _reset_act_environment_enabled() -> object:
    set_act_environment_enabled(False)
    try:
        yield None
    finally:
        set_act_environment_enabled(False)


def test_warns_if_suspense_ping_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    thenable = Thenable()

    def Suspender() -> object:  # function component
        raise Suspend(thenable)

    root = create_noop_root()
    set_act_environment_enabled(True)

    # Render inside act to avoid root-update act warning.
    with act(root.flush):
        root.render(
            suspense(
                fallback=create_element("div", {"text": "loading"}),
                children=create_element(Suspender),
            )
        )

    # Resolving the thenable outside act schedules a ping and should warn.
    with WarningCapture() as wc:
        thenable.resolve()
    wc.assert_any("Suspense ping was not wrapped in act")

    root.flush()


def test_warns_if_suspense_retry_is_not_wrapped() -> None:
    # Upstream: ReactActWarnings-test.js
    thenable = Thenable()
    attempts = {"n": 0}

    def Suspender() -> object:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise Suspend(thenable)
        return create_element("div", {"text": "done"})

    root = create_noop_root()
    set_act_environment_enabled(True)

    with act(root.flush):
        root.render(
            suspense(
                fallback=create_element("div", {"text": "loading"}),
                children=create_element(Suspender),
            )
        )

    # Retrying outside act should warn (we approximate retry via the same wake path).
    with WarningCapture() as wc:
        thenable.resolve()
    wc.assert_any("Suspense ping was not wrapped in act")

    root.flush()
