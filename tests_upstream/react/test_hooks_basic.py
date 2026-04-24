from __future__ import annotations

import pytest
from ryact import create_element
from ryact.hooks import HookError, use_memo, use_state
from ryact_testkit import create_noop_root


def test_warns_on_using_differently_ordered_hooks_on_subsequent_renders() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "warns on using differently ordered hooks (...) on subsequent renders"
    root = create_noop_root()

    flip = {"v": False}

    def App() -> object:
        if not flip["v"]:
            use_state(0)
            use_memo(lambda: 123, ())
        else:
            use_memo(lambda: 123, ())
            use_state(0)
        return create_element("div")

    root.render(create_element(App))
    flip["v"] = True
    with pytest.raises(HookError):
        root.render(create_element(App))


def test_rendering_more_hooks_than_previous_render_throws() -> None:
    # Upstream: ReactHooks-test.internal.js (hook ordering family)
    root = create_noop_root()

    flip = {"v": False}

    def App() -> object:
        use_state(0)
        if flip["v"]:
            use_memo(lambda: 123, ())
        return create_element("div")

    root.render(create_element(App))
    flip["v"] = True
    with pytest.raises(HookError):
        root.render(create_element(App))
