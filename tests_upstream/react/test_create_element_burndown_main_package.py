from __future__ import annotations

import math
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import set_dev
from ryact.element import raw_element_ref, reset_create_element_dev_warning_state
from ryact_testkit import WarningCapture, act_call, create_noop_root, set_act_environment_enabled


@pytest.fixture(autouse=True)
def _dev_and_act_env() -> Iterator[None]:
    set_dev(True)
    set_act_environment_enabled(True)
    reset_create_element_dev_warning_state()
    yield
    set_act_environment_enabled(False)


def test_returns_complete_element_spec_string_host() -> None:
    # Upstream: "returns a complete element according to spec" / "allows a string..."
    el = create_element("div")
    assert el.type == "div"
    assert el.key is None
    assert el.ref is None
    assert dict(el.props) == {}


def test_dev_frozen_element_and_props() -> None:
    el = create_element("div")
    with pytest.raises(AttributeError):
        el.type = "span"  # type: ignore[misc]


def test_allows_static_method_on_element_type() -> None:
    class StaticCmp(Component):
        @staticmethod
        def some_static_method() -> str:
            return "someReturnValue"

        def render(self) -> object:
            return create_element("div")

    el = create_element(StaticCmp)
    assert el.type.some_static_method() == "someReturnValue"


def test_config_without_dict_prototype() -> None:
    # Upstream: Object.create(null, {foo: {value: 1, enumerable: true}})
    class NullProtoMap(Mapping[str, Any]):
        def __getitem__(self, k: str) -> Any:
            if k != "foo":
                raise KeyError(k)
            return 1

        def __iter__(self) -> Iterator[str]:
            yield "foo"

        def __len__(self) -> int:
            return 1

    class C(Component):
        def render(self) -> object:
            return create_element("span")

    el = create_element(C, NullProtoMap())
    assert el.props["foo"] == 1


def test_class_element_keeps_ref_on_element_and_in_props() -> None:
    # Upstream React 19: "does not extract ref from the rest of the props"
    class C(Component):
        def render(self) -> object:
            return create_element("span")

    ref = create_ref()
    el = create_element(C, {"key": "12", "ref": ref, "foo": "56"})
    assert el.type is C
    assert el.key == "12"
    assert raw_element_ref(el) is ref
    assert el.props["foo"] == "56"
    assert el.props["ref"] is ref


def test_dev_warns_when_reading_element_ref_on_class_component() -> None:
    class C(Component):
        def render(self) -> object:
            return create_element("span")

    ref = create_ref()
    el = create_element(C, {"ref": ref})
    with WarningCapture() as cap:
        _ = el.ref
    assert raw_element_ref(el) is ref
    assert any(
        "Accessing element.ref was removed in React 19" in str(r.message) for r in cap.records
    )


def test_ignores_key_and_ref_warning_getters_on_reused_props() -> None:
    # Upstream: createElement('div'); createElement('div', elementA.props)
    a = create_element("div")
    b = create_element("div", a.props)
    assert b.key is None
    assert b.ref is None


def test_does_not_warn_for_nan_props() -> None:
    class T(Component):
        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    with WarningCapture() as cap:
        act_call(lambda: root.render(create_element(T, {"value": float("nan")})), flush=root.flush)
    assert cap.records == []
    el = create_element(T, {"value": float("nan")})
    assert math.isnan(el.props["value"])  # type: ignore[arg-type]


def test_warns_outdated_jsx_transform_when_self_present() -> None:
    reset_create_element_dev_warning_state()
    with WarningCapture() as cap:
        create_element("div", {"className": "foo", "__self": {}})
    assert any("outdated JSX" in str(r.message) for r in cap.records)


def test_outdated_jsx_transform_warns_only_first_time() -> None:
    reset_create_element_dev_warning_state()
    with WarningCapture() as cap:
        create_element("div", {"className": "a", "__self": {}})
        create_element("div", {"className": "b", "__self": {}})
    assert sum(1 for r in cap.records if "outdated JSX" in str(r.message)) == 1


def test_no_outdated_jsx_warn_when_key_present() -> None:
    reset_create_element_dev_warning_state()
    with WarningCapture() as cap:
        create_element("div", {"key": "foo", "__self": {}})
    assert cap.records == []


def test_warn_when_accessing_key_on_host_element_props() -> None:
    el = create_element("div", {"key": "3"})
    with WarningCapture() as cap:
        _ = el.props["key"]
    assert any("`key` is not a prop" in str(r.message) for r in cap.records)


def test_warn_when_accessing_key_on_class_render_props() -> None:
    class Child(Component):
        def render(self) -> object:
            return create_element("div", None, str(self.props["key"]))

    class Parent(Component):
        def render(self) -> object:
            return create_element(
                "div",
                None,
                create_element(Child, {"key": "0"}),
                create_element(Child, {"key": "1"}),
                create_element(Child, {"key": "2"}),
            )

    root = create_noop_root()
    with WarningCapture() as cap:
        act_call(lambda: root.render(create_element(Parent)), flush=root.flush)
    assert any("`key` is not a prop" in str(r.message) for r in cap.records)


def test_dev_throws_when_mutating_element_props() -> None:
    el = create_element("div", {"className": "moo"})
    with pytest.raises(TypeError):
        el.props["className"] = "quack"


def test_dev_throws_when_adding_element_prop() -> None:
    el = create_element("div", None, "x")
    with pytest.raises(TypeError):
        el.props["className"] = "quack"


def test_should_normalize_props_with_default_values() -> None:
    snapshots: list[dict[str, Any]] = []

    class C(Component):
        defaultProps = {"prop": "testKey"}

        def render(self) -> object:
            snapshots.append(dict(self._props))
            return create_element("span", None, str(self.props.get("prop")))

    root = create_noop_root()
    act_call(lambda: root.render(create_element(C)), flush=root.flush)
    assert snapshots[-1]["prop"] == "testKey"

    act_call(lambda: root.render(create_element(C, {"prop": None})), flush=root.flush)
    assert snapshots[-1]["prop"] is None


def test_should_use_default_prop_value_when_removing_a_prop() -> None:
    class C(Component):
        defaultProps = {"fruit": "persimmon"}

        def render(self) -> object:
            return create_element("span")

    ref = create_ref()
    root = create_noop_root()
    act_call(
        lambda: root.render(create_element(C, {"ref": ref, "fruit": "mango"})), flush=root.flush
    )
    assert ref.current is not None
    assert ref.current.props["fruit"] == "mango"

    act_call(lambda: root.render(create_element(C, {"ref": ref})), flush=root.flush)
    assert ref.current.props["fruit"] == "persimmon"
