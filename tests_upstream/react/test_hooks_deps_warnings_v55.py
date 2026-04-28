from __future__ import annotations

from ryact import create_element, use_memo
from ryact_testkit import WarningCapture, create_noop_root


def test_warns_if_deps_is_not_an_array() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "warns if deps is not an array"
    def App() -> object:
        with WarningCapture() as wc:
            use_memo(lambda: 1, ["not", "a", "tuple"])  # type: ignore[arg-type]
        wc.assert_any("final argument that is not an array")
        return create_element("span", {"children": ["ok"]})

    root = create_noop_root()
    root.render(create_element(App, {}))


def test_warns_if_switching_from_dependencies_to_no_dependencies() -> None:
    # Upstream: ReactHooks-test.internal.js
    # "warns if switching from dependencies to no dependencies"
    def App(*, no_deps: bool) -> object:
        with WarningCapture() as wc:
            if no_deps:
                use_memo(lambda: 1, None)  # type: ignore[arg-type]
            else:
                use_memo(lambda: 1, (1,))
        if no_deps:
            wc.assert_any("changed from defined to undefined")
        return create_element("span", {"children": ["ok"]})

    root = create_noop_root()
    root.render(create_element(App, {"no_deps": False}))
    root.render(create_element(App, {"no_deps": True}))

