from __future__ import annotations

from ryact import component, create_element
from ryact_testkit import create_noop_root


def test_component_decorator_preserves_render_behavior() -> None:
    root = create_noop_root()

    @component
    def App() -> object:
        return create_element("div", {"id": "x"})

    root.render(create_element(App))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["type"] == "div"
    assert committed["props"]["id"] == "x"
