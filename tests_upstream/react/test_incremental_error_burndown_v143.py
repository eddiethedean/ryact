# Translated from: packages/react-reconciler/src/__tests__/ReactIncrementalErrorHandling-test.internal.js
# Burndown v143: single-root error scheduling slices.
from __future__ import annotations

from typing import Any

import pytest
from ryact import Component, create_element
from ryact_testkit import act, create_noop_root, set_act_environment_enabled


def test_defers_additional_sync_work_to_a_separate_event_after_an_error() -> None:
    root = create_noop_root()
    root.render(create_element("span", {"text": "a:1"}))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "a:1"

    def batch() -> None:
        root.render(create_element("span", {"text": "a:2"}))
        root.render(create_element("span", {"text": "a:3"}))
        raise RuntimeError("Hello")

    with pytest.raises(RuntimeError, match="Hello"):
        root.flush_sync(lambda: root.batched_updates(batch))

    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "a:3"


@pytest.mark.skip(reason="Deferred: uncaught error unmount should emit AggregateError and run cWU lifecycles")
def test_unmounts_components_with_uncaught_errors() -> None:
    log: list[str] = []
    inst_holder: list[Any] = []

    class BrokenRenderAndUnmount(Component):
        def render(self) -> object:
            inst_holder.append(self)
            if bool(self.state.get("fail")):
                raise RuntimeError("Hello.")
            return None

        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("BrokenRenderAndUnmount componentWillUnmount")

    class Parent(Component):
        def componentWillUnmount(self) -> None:  # noqa: N802
            log.append("Parent componentWillUnmount [!]")
            raise RuntimeError("One does not simply unmount me.")

        def render(self) -> object:
            return self.props.get("children")

    root = create_noop_root()
    set_act_environment_enabled(True)
    try:
        root.render(
            create_element(
                Parent,
                {"children": create_element(Parent, {"children": create_element(BrokenRenderAndUnmount)})},
            )
        )
        root.flush()

        aggregate: BaseException | None = None
        try:
            with act(flush=root.flush):
                root.flush_sync(lambda: inst_holder[0].set_state({"fail": True}))
        except BaseException as err:
            aggregate = err

        assert log == [
            "Parent componentWillUnmount [!]",
            "Parent componentWillUnmount [!]",
            "BrokenRenderAndUnmount componentWillUnmount",
        ]
        assert root.get_children_snapshot() is None
        assert aggregate is not None
        errors = getattr(aggregate, "errors", None)
        if errors is None and isinstance(aggregate, ExceptionGroup):
            errors = aggregate.exceptions
        assert errors is not None
        assert len(errors) == 3
        assert str(errors[0]) == "Hello."
    finally:
        set_act_environment_enabled(False)
