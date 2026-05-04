from __future__ import annotations

import pytest
from ryact import Component, create_element, create_ref
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_class_refs_are_initialized_to_a_frozen_shared_object() -> None:
    # Upstream: ReactFiberRefs-test.js — "class refs are initialized to a frozen shared object"
    class Dummy(Component):
        def render(self) -> object:
            return None

    a = Dummy()
    b = Dummy()
    assert a.refs is b.refs
    assert dict(a.refs) == {}
    with pytest.raises(TypeError):
        a.refs["x"] = 1  # type: ignore[index]


def test_ref_is_attached_even_if_there_are_no_other_updates_class() -> None:
    # Upstream: ReactFiberRefs-test.js — "ref is attached even if there are no other updates (class)"
    r = create_ref()
    inst: App | None = None

    class App(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            nonlocal inst
            inst = self

        def render(self) -> object:
            return create_element("div")

    root = create_noop_root()
    root.render(create_element(App, {"ref": r}))
    assert inst is not None
    assert r.current is inst


def test_ref_is_attached_even_if_there_are_no_other_updates_host() -> None:
    # Upstream: ReactFiberRefs-test.js — "ref is attached even if there are no other updates (host component)"
    r = create_ref()
    root = create_noop_root()
    root.render(create_element("div", {"ref": r}))
    assert isinstance(r.current, dict)
    assert r.current.get("type") == "div"


def test_create_ref_returns_object_with_current() -> None:
    ref = create_ref()
    assert hasattr(ref, "current")
    assert ref.current is None


def test_object_ref_attaches_and_detaches_in_noop_host() -> None:
    root = create_noop_root()
    ref = create_ref()
    root.render(create_element("div", {"ref": ref}))
    assert ref.current is not None
    root.render(None)
    assert ref.current is None


def test_callback_ref_attaches_and_detaches_in_noop_host() -> None:
    root = create_noop_root()
    seen: list[object | None] = []

    def cb(value: object | None) -> None:
        seen.append(value)

    root.render(create_element("div", {"ref": cb}))
    root.render(None)
    assert seen[0] is not None
    assert seen[-1] is None


def test_should_warn_in_dev_if_an_invalid_ref_object_is_provided() -> None:
    # Upstream: ReactCreateRef-test.js
    set_dev(True)
    root = create_noop_root()
    with WarningCapture() as cap:
        root.render(create_element("div", {"ref": object()}))
    assert any("invalid ref object" in str(r.message).lower() for r in cap.records)
