from __future__ import annotations

from typing import cast

from ryact import create_element, create_ref, forward_ref
from ryact_testkit import create_noop_root


def test_forward_ref_works_without_ref() -> None:
    # Upstream: forwardRef-test.internal.js
    # "should work without a ref to be forwarded"
    root = create_noop_root()

    def render(props: dict[str, object], ref: object | None) -> object:
        assert ref is None
        return create_element("div", {"id": props.get("id")})

    F = forward_ref(render)
    root.render(create_element(F, {"id": "x"}))
    committed = root.container.last_committed
    assert committed is not None
    assert committed["props"]["id"] == "x"


def test_forward_ref_attaches_ref_when_provided() -> None:
    root = create_noop_root()

    def render(props: dict[str, object], ref: object | None) -> object:
        return create_element("div", {"id": props.get("id"), "ref": ref})

    F = forward_ref(render)
    r = create_ref()
    root.render(create_element(F, {"id": "y", "ref": r}))
    root.flush()
    assert r.current is not None
    assert isinstance(r.current, dict)
    host = cast(dict[str, object], r.current)
    assert host["type"] == "div"
