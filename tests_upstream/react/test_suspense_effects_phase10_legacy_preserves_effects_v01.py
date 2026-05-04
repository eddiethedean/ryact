from __future__ import annotations

from typing import Any

from ryact import create_element, use_effect
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def _span(value: str) -> Any:
    return create_element("span", {"text": value})


def test_should_not_be_destroyed_or_recreated_in_legacy_roots() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should not be destroyed or recreated in legacy roots"
    t = Thenable()
    state = {"ready": True}
    log: list[str] = []

    def Child(*, label: str) -> Any:
        def eff() -> Any:
            log.append(f"create:{label}")
            return lambda: log.append(f"cleanup:{label}")

        use_effect(eff, ())
        if not state["ready"]:
            raise Suspend(t)
        return _span(label)

    root = create_noop_root(legacy=True)
    root.render(
        suspense(
            fallback=_span("Loading"),
            children=create_element(Child, {"label": "A"}),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"
    assert log == ["create:A"]

    # Re-suspend during update: legacy roots should keep the committed primary tree and
    # not destroy/recreate effects.
    state["ready"] = False
    root.render(
        suspense(
            fallback=_span("Loading"),
            children=create_element(Child, {"label": "A"}),
        )
    )
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "A"
    assert log == ["create:A"]
