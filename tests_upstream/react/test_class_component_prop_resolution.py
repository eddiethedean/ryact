from __future__ import annotations

from ryact import Component, create_element, create_ref
from ryact_testkit import create_noop_root


def test_resolves_ref_and_default_props_before_calling_lifecycle_methods() -> None:
    # Upstream: ReactClassComponentPropResolution-test.js
    seen: list[str] = []
    ref = create_ref()

    class App(Component):
        defaultProps = {"label": "default"}

        def UNSAFE_componentWillMount(self) -> None:  # noqa: N802
            seen.append(f"cwm:label={self.props.get('label')},ref={ref.current is self}")

        def componentDidMount(self) -> None:  # noqa: N802
            seen.append(f"cdm:label={self.props.get('label')},ref={ref.current is self}")

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    root.render(create_element(App, {"ref": ref}))
    assert seen[0] == "cwm:label=default,ref=True"
    assert seen[1] == "cdm:label=default,ref=True"
