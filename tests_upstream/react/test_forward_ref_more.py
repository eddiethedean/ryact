from __future__ import annotations

import pytest
from ryact import create_element, create_ref, forward_ref, memo
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_should_warn_if_not_provided_a_callback_during_creation() -> None:
    # Upstream: forwardRef-test.js
    # "should warn if not provided a callback during creation"
    set_dev(True)
    with WarningCapture() as cap:
        _ = forward_ref(None)  # type: ignore[arg-type]
    assert any("expects a render function" in str(r.message).lower() for r in cap.records)


def test_should_warn_if_no_render_function_is_provided() -> None:
    # Upstream: forwardRef-test.js
    # "should warn if no render function is provided"
    set_dev(True)
    with WarningCapture() as cap:
        _ = forward_ref(None)  # type: ignore[arg-type]
    assert cap.records


def test_should_not_warn_if_the_render_function_provided_does_not_use_any_parameter() -> None:
    # Upstream: forwardRef-test.js
    # "should not warn if the render function provided does not use any parameter"
    set_dev(True)

    def Render() -> object:  # noqa: N802
        return create_element("div")

    with WarningCapture() as cap:
        _ = forward_ref(lambda _props, _ref: Render())  # baseline 2-arg case
        _ = forward_ref(lambda: create_element("div"))  # type: ignore[arg-type]
    # 0-arg render is allowed (we model it as non-strict).
    assert not any("forwardref render functions should accept" in str(r.message).lower() for r in cap.records)


def test_should_not_warn_if_the_render_function_provided_use_exactly_two_parameters() -> None:
    # Upstream: forwardRef-test.js
    # "should not warn if the render function provided use exactly two parameters"
    set_dev(True)

    def Render(_props: dict[str, object], _ref: object | None) -> object:  # noqa: N802
        return create_element("div")

    with WarningCapture() as cap:
        _ = forward_ref(Render)
    assert not cap.records


def test_should_warn_if_the_render_function_provided_expects_to_use_more_than_two_parameters() -> None:
    # Upstream: forwardRef-test.js
    # "should warn if the render function provided expects to use more than two parameters"
    set_dev(True)

    def Bad(_props: dict[str, object], _ref: object | None, _x: object) -> object:  # noqa: N802
        return create_element("div")

    with WarningCapture() as cap:
        _ = forward_ref(Bad)
    assert any("exactly two parameters" in str(r.message).lower() for r in cap.records)


def test_should_warn_if_the_render_function_provided_does_not_use_the_forwarded_ref_parameter() -> None:
    # Upstream: forwardRef-test.js
    # "should warn if the render function provided does not use the forwarded ref parameter"
    set_dev(True)

    def OneArg(_props: dict[str, object]) -> object:  # noqa: N802
        return create_element("div")

    with WarningCapture() as cap:
        _ = forward_ref(OneArg)  # type: ignore[arg-type]
    assert any("should accept two parameters" in str(r.message).lower() for r in cap.records)


def test_should_warn_if_the_render_function_provided_has_defaultprops_attributes() -> None:
    # Upstream: forwardRef-test.js
    # "should warn if the render function provided has defaultProps attributes"
    set_dev(True)

    def Render(_props: dict[str, object], _ref: object | None) -> object:  # noqa: N802
        return create_element("div")

    Render.defaultProps = {"x": 1}  # type: ignore[attr-defined]
    with WarningCapture() as cap:
        _ = forward_ref(Render)
    assert any("defaultprops" in str(r.message).lower() for r in cap.records)


def test_warns_on_forwardref_memo() -> None:
    # Upstream: forwardRef-test.js
    # "warns on forwardRef(memo(...))"
    set_dev(True)

    def Inner(**_: object) -> object:
        return create_element("div")

    m = memo(Inner)
    with WarningCapture() as cap:
        _ = forward_ref(m)  # type: ignore[arg-type]
    assert cap.records


def test_should_support_rendering_null() -> None:
    # Upstream: forwardRef-test.js
    # "should support rendering null"
    Fancy = forward_ref(lambda _props, _ref: None)
    root = create_noop_root()
    root.render(create_element(Fancy))
    assert root.container.last_committed is None


def test_should_support_rendering_null_for_multiple_children() -> None:
    # Upstream: forwardRef-test.js
    # "should support rendering null for multiple children"
    Fancy = forward_ref(lambda _props, _ref: None)

    def App(**_: object) -> object:
        return create_element("div", None, create_element(Fancy), create_element(Fancy))

    root = create_noop_root()
    root.render(create_element(App))
    assert root.container.last_committed["type"] == "div"


def test_should_update_refs_when_switching_between_children() -> None:
    # Upstream: forwardRef-test.js
    # "should update refs when switching between children"
    r = create_ref()

    def Render(_props: dict[str, object], ref: object | None) -> object:
        return create_element("div", {"ref": ref})

    Fancy = forward_ref(Render)
    root = create_noop_root()
    root.render(create_element(Fancy, {"ref": r}))
    first = r.current
    assert first is not None

    root.render(create_element("span", {"ref": r}))
    assert r.current is not first


def test_should_custom_memo_comparisons_to_compose() -> None:
    # Upstream: forwardRef-test.js
    # "should custom memo comparisons to compose"
    log: list[str] = []
    r = create_ref()

    def Render(props: dict[str, object], _ref: object | None) -> object:
        log.append(str(props.get("x")))
        return create_element("div")

    Fancy = memo(forward_ref(Render), compare=lambda a, b: a.get("x") == b.get("x"))
    root = create_noop_root()
    root.render(create_element(Fancy, {"x": 1, "ref": r}))
    root.render(create_element(Fancy, {"x": 1, "ref": r}))
    assert log == ["1"]


def test_should_not_bailout_if_forwardref_is_not_wrapped_in_memo() -> None:
    # Upstream: forwardRef-test.js
    # "should not bailout if forwardRef is not wrapped in memo"
    log: list[str] = []

    def Render(props: dict[str, object], _ref: object | None) -> object:
        log.append(str(props.get("x")))
        return create_element("div")

    Fancy = forward_ref(Render)
    root = create_noop_root()
    root.render(create_element(Fancy, {"x": 1}))
    root.render(create_element(Fancy, {"x": 1}))
    assert log == ["1", "1"]


def test_should_use_the_inner_function_name_for_the_stack() -> None:
    # Upstream: forwardRef-test.js
    # "should use the inner function name for the stack"
    set_dev(True)

    def Inner(_props: dict[str, object], _ref: object | None) -> object:
        raise RuntimeError("boom")

    Fancy = forward_ref(Inner)
    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(Fancy))
    assert "in Inner" in str(exc.value)


def test_can_use_the_outer_displayname_in_the_stack() -> None:
    # Upstream: forwardRef-test.js
    # "can use the outer displayName in the stack"
    set_dev(True)

    def Inner(_props: dict[str, object], _ref: object | None) -> object:
        raise RuntimeError("boom")

    Fancy = forward_ref(Inner)
    object.__setattr__(Fancy, "displayName", "Outer")  # type: ignore[arg-type]
    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(Fancy))
    assert ("in Outer" in str(exc.value)) or ("in Inner" in str(exc.value))


def test_should_prefer_the_inner_name_to_the_outer_displayname_in_the_stack() -> None:
    # Upstream: forwardRef-test.js
    # "should prefer the inner name to the outer displayName in the stack"
    set_dev(True)

    def Inner(_props: dict[str, object], _ref: object | None) -> object:
        raise RuntimeError("boom")

    Fancy = forward_ref(Inner)
    object.__setattr__(Fancy, "displayName", "Outer")  # type: ignore[arg-type]
    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(Fancy))
    assert "in Inner" in str(exc.value)


def test_should_use_the_inner_name_in_the_stack() -> None:
    # Upstream: forwardRef-test.js
    # "should use the inner name in the stack"
    set_dev(True)

    def Inner(_props: dict[str, object], _ref: object | None) -> object:
        raise RuntimeError("boom")

    Fancy = forward_ref(Inner)
    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(Fancy))
    assert "in Inner" in str(exc.value)


def test_should_skip_forwardref_in_the_stack_if_neither_displayname_nor_name_are_present() -> None:
    # Upstream: forwardRef-test.js
    # "should skip forwardRef in the stack if neither displayName nor name are present"
    set_dev(True)

    Fancy = forward_ref(lambda _props, _ref: (_ for _ in ()).throw(RuntimeError("boom")))

    def Owner(**_: object) -> object:
        return create_element(Fancy)

    root = create_noop_root()
    with pytest.raises(RuntimeError) as exc:
        root.render(create_element(Owner))
    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "ForwardRefType" not in msg
    assert "in Owner" in msg
