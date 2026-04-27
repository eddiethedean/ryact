from __future__ import annotations

from ryact import create_element, create_ref, forward_ref
from ryact_testkit import create_noop_root


def test_should_forward_a_ref_for_a_single_child() -> None:
    # Upstream: forwardRef-test.internal.js
    # "should forward a ref for a single child"
    r = create_ref()
    Fancy = forward_ref(lambda _props, ref: create_element("div", {"ref": ref}))
    root = create_noop_root()
    root.render(create_element(Fancy, {"ref": r}))
    assert r.current is not None


def test_should_forward_a_ref_for_multiple_children() -> None:
    # Upstream: forwardRef-test.internal.js
    # "should forward a ref for multiple children"
    r = create_ref()

    def Render(_props, ref):  # noqa: ANN001
        return create_element("div", None, create_element("span", {"ref": ref}), create_element("b"))

    Fancy = forward_ref(Render)
    root = create_noop_root()
    root.render(create_element(Fancy, {"ref": r}))
    assert r.current is not None


def test_should_maintain_child_instance_and_ref_through_updates() -> None:
    # Upstream: forwardRef-test.internal.js
    # "should maintain child instance and ref through updates"
    r = create_ref()

    def Render(props, ref):  # noqa: ANN001
        return create_element("div", {"ref": ref, "x": props.get("x")})

    Fancy = forward_ref(Render)
    root = create_noop_root()
    root.render(create_element(Fancy, {"ref": r, "x": 1}))
    first = r.current
    root.render(create_element(Fancy, {"ref": r, "x": 2}))
    assert r.current is first

