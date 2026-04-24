from __future__ import annotations

from collections.abc import Callable

from ryact import Component, create_element, use_state
from ryact_testkit import create_noop_root


def test_calls_componentdidmount_update_after_insertion_update() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "calls componentDidMount/Update after insertion/update"
    root = create_noop_root()
    log: list[str] = []
    api: dict[str, Callable[[int], None]] = {}

    class Child(Component):
        def render(self) -> object:
            log.append(f"render:{self.props['value']}")
            return create_element("div", {"value": self.props["value"]})

        def componentDidMount(self) -> None:  # noqa: N802 (React naming)
            log.append(f"didMount:{self.props['value']}")

        def componentDidUpdate(self) -> None:  # noqa: N802 (React naming)
            log.append(f"didUpdate:{self.props['value']}")

    def App() -> object:
        value, set_value = use_state(0)
        api["set"] = set_value
        return create_element(Child, {"value": value})

    root.render(create_element(App))
    assert log == ["render:0", "didMount:0"]

    log.clear()
    api["set"](1)
    root.flush()
    assert log == ["render:1", "didUpdate:1"]


def test_calls_componentwillunmount_after_a_deletion_even_if_nested() -> None:
    # Upstream: ReactIncrementalSideEffects-test.js
    # "calls componentWillUnmount after a deletion, even if nested"
    root = create_noop_root()
    log: list[str] = []
    api: dict[str, Callable[[bool], None]] = {}

    class Child(Component):
        def render(self) -> object:
            return create_element("span")

        def componentWillUnmount(self) -> None:  # noqa: N802 (React naming)
            log.append("willUnmount")

    def App() -> object:
        show, set_show = use_state(True)
        api["set"] = set_show
        return create_element("div", None, create_element(Child) if show else None)

    root.render(create_element(App))
    api["set"](False)
    root.flush()
    assert log == ["willUnmount"]
