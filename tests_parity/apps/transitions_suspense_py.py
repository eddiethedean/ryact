from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, h, use_state, use_transition
from ryact.concurrent import Suspend, Thenable, suspense


def make_transitions_suspense_app(
    *, sink: dict[str, object], thenable: Thenable, log: list[str]
) -> Callable[[], object]:
    def App() -> object:
        pending, start = use_transition()
        value, set_value = use_state("A")

        sink["start"] = start
        sink["set_value"] = set_value

        def Child() -> object:
            log.append(f"render:pending={pending}")
            if value == "SUSPEND":
                raise Suspend(thenable)
            return h("span", {"id": "v"}, value)

        tree = suspense(fallback=h("div", {"id": "fb"}, "loading"), children=create_element(Child, None))
        return h("div", None, tree)

    return App


def build_tree(*, sink: dict[str, object], thenable: Thenable, log: list[str]) -> object:
    App = make_transitions_suspense_app(sink=sink, thenable=thenable, log=log)
    return create_element(App, None)
