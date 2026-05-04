from __future__ import annotations

from collections.abc import Callable

from ryact import Fragment, create_element, use_state
from ryact_testkit import create_noop_root


def test_should_not_preserve_state_between_unkeyed_and_keyed_fragment() -> None:
    # Upstream: ReactFragment-test.js
    # "should not preserve state between unkeyed and keyed fragment"
    root = create_noop_root()
    api: dict[str, Callable[[int], None]] = {}

    def Child() -> object:
        value, set_value = use_state(0)
        api["set"] = set_value
        return create_element("div", {"value": value})

    root.render(create_element(Fragment, None, create_element(Child)))
    api["set"](1)
    root.flush()
    committed = root.container.last_committed
    assert committed is not None
    assert isinstance(committed, list)
    assert committed[0]["props"]["value"] == 1

    # Switch to a keyed fragment: should remount and reset state.
    root.render(create_element(Fragment, {"key": "k"}, create_element(Child)))
    committed2 = root.container.last_committed
    assert committed2 is not None
    assert isinstance(committed2, list)
    assert committed2[0]["props"]["value"] == 0


def test_should_not_preserve_state_in_non_top_level_fragment_nesting() -> None:
    # Upstream: ReactFragment-test.js
    # "should not preserve state in non-top-level fragment nesting"
    root = create_noop_root()
    api: dict[str, Callable[[int], None]] = {}
    mode = {"fragment": True}

    def Child() -> object:
        value, set_value = use_state(0)
        api["set"] = set_value
        return create_element("span", {"value": value})

    def App() -> object:
        inner = create_element(Fragment, None, create_element(Child)) if mode["fragment"] else create_element(Child)
        return create_element("div", None, inner)

    root.render(create_element(App))
    api["set"](1)
    root.flush()

    mode["fragment"] = False
    root.render(create_element(App))
    committed = root.container.last_committed
    assert committed is not None
    # Child should remount in the new shape, resetting its hook state.
    assert committed["children"][0]["props"]["value"] == 0
