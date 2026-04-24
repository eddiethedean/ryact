from __future__ import annotations

from ryact import create_element, create_ref
from ryact.dev import set_dev
from ryact_testkit import WarningCapture, create_noop_root


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
