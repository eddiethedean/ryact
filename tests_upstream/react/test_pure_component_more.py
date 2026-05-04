from __future__ import annotations

from ryact import Component, PureComponent, create_element
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_render() -> None:
    # Upstream: ReactPureComponent-test.js
    # "should render"
    root = create_noop_root()

    class App(PureComponent):
        def render(self) -> object:
            return create_element("div", {"text": "ok"})

    root.render(create_element(App))
    assert root.container.last_committed_as_dict()["type"] == "div"


def test_extends_react_component() -> None:
    # Upstream: ReactPureComponent-test.js
    # "extends React.Component"
    class App(PureComponent):
        def render(self) -> object:
            return None

    assert issubclass(App, Component)


def test_can_override_shouldcomponentupdate() -> None:
    # Upstream: ReactPureComponent-test.js
    # "can override shouldComponentUpdate"
    set_dev(True)
    root = create_noop_root()
    calls: list[str] = []

    class App(PureComponent):
        def shouldComponentUpdate(self, nextProps, nextState):  # noqa: N802, ANN001
            calls.append("scu")
            return False

        def render(self) -> object:
            calls.append("render")
            return create_element("div", {"x": self.props.get("x")})

    root.render(create_element(App, {"x": 1}))
    with WarningCapture() as cap:
        root.render(create_element(App, {"x": 2}))
    assert any("purecomponent" in str(r.message).lower() for r in cap.records)
    # render should not run second time because SCU returned False.
    assert calls == ["render", "scu"]


def test_should_warn_when_shouldcomponentupdate_is_defined_on_react_purecomponent() -> None:
    # Upstream: ReactPureComponent-test.js
    # "should warn when shouldComponentUpdate is defined on React.PureComponent"
    set_dev(True)
    root = create_noop_root()

    class App(PureComponent):
        def shouldComponentUpdate(self, nextProps, nextState):  # noqa: N802, ANN001
            return True

        def render(self) -> object:
            return create_element("div")

    with WarningCapture() as cap:
        root.render(create_element(App))
        root.render(create_element(App))
    assert any(
        "purecomponent" in str(r.message).lower() and "shouldcomponentupdate" in str(r.message).lower()
        for r in cap.records
    )
