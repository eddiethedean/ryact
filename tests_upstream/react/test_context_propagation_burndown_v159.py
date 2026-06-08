# Translated from: packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js
# Burndown v159: memoized consumers re-render when context changes.
from __future__ import annotations

from typing import Any

from ryact import PureComponent, create_element, use_context, use_memo, use_state
from ryact.context import context_provider, create_context
from ryact_testkit import create_noop_root


def test_context_change_should_prevent_bailout_of_memoized_component_purecomponent() -> None:
    Ctx = create_context(0)
    log: list[str] = []

    class Consumer(PureComponent):
        contextType = Ctx

        def render(self) -> object:
            return create_element(DeepChild, {"value": self.context})

    def DeepChild(**props: Any) -> object:
        log.append(int(props["value"]))
        return create_element("span", {"text": str(props["value"])})

    holder: dict[str, Any] = {}

    def App() -> object:
        value, set_value = use_state(0)
        holder["set"] = set_value
        return context_provider(Ctx, value, create_element(Consumer))

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert log == [0]
    assert root.get_children_snapshot()["props"]["text"] == "0"

    log.clear()
    holder["set"](1)
    root.flush()
    assert log == [1]
    assert root.get_children_snapshot()["props"]["text"] == "1"


def test_context_change_should_prevent_bailout_of_memoized_component_usememo_no_intermediate_fiber() -> None:
    Ctx = create_context(0)
    log: list[str] = []

    def Consumer() -> object:
        value = use_context(Ctx)
        return create_element(DeepChild, {"value": value})

    def DeepChild(**props: Any) -> object:
        log.append(int(props["value"]))
        return create_element("span", {"text": str(props["value"])})

    holder: dict[str, Any] = {}

    def App() -> object:
        value, set_value = use_state(0)
        holder["set"] = set_value
        consumer = use_memo(lambda: create_element(Consumer), ())
        return context_provider(Ctx, value, consumer)

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert log == [0]

    log.clear()
    holder["set"](1)
    root.flush()
    assert log == [1]
