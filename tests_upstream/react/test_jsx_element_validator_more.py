from __future__ import annotations

import pytest
from ryact import create_element
from ryact.concurrent import lazy
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


def test_does_not_call_lazy_initializers_eagerly() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "does not call lazy initializers eagerly"
    called = {"v": False}

    def loader() -> object:
        called["v"] = True

        def Inner(**_props: object) -> object:
            return None

        return Inner

    _ = create_element(lazy(loader), {})
    assert called["v"] is False


def test_does_not_warn_for_numeric_keys_in_entry_iterable_as_a_child() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "does not warn for numeric keys in entry iterable as a child"
    set_dev(True)
    iterable = (create_element("span", {"key": 0}), create_element("b", {"key": 1}))
    with WarningCapture() as cap:
        _ = create_element("div", None, iterable)
    assert cap.records == []


def test_warns_for_keys_for_arrays_of_elements_with_owner_info() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "warns for keys for arrays of elements with owner info"
    set_dev(True)

    def Owner(**_: object) -> object:
        return create_element("div", None, [create_element("span"), create_element("b")])

    with WarningCapture() as cap:
        create_noop_root().render(create_element(Owner))
    msg = "\n".join(str(r.message) for r in cap.records).lower()
    assert "key" in msg
    assert "component stack" in msg
    assert "in owner" in msg


def test_should_give_context_for_errors_in_nested_components() -> None:
    # Upstream: ReactJSXElementValidator-test.js
    # "should give context for errors in nested components."
    set_dev(True)

    def Inner(**_: object) -> object:
        return create_element(None)

    def Outer(**_: object) -> object:
        return create_element(Inner)

    root = create_noop_root()
    with pytest.raises(TypeError) as exc:
        root.render(create_element(Outer))
    msg = str(exc.value)
    assert "Component stack:" in msg
    assert "in Inner" in msg
    assert "in Outer" in msg
