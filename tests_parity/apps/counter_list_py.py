from __future__ import annotations

from typing import Callable

from ryact import create_element, h, use_state


def make_counter_list_app(*, sink: dict[str, object]) -> Callable[[], object]:
    """
    Return a component function. The component writes interaction handles into `sink`.
    """

    def App() -> object:
        count, set_count = use_state(0)
        order, set_order = use_state(["a", "b", "c"])

        sink["set_count"] = set_count
        sink["set_order"] = set_order

        items = [h("li", {"key": k, "data-k": k}, k) for k in order]
        return h("div", None, h("span", {"id": "count"}, str(count)), h("ul", None, items))

    return App


def build_tree(*, sink: dict[str, object]) -> object:
    App = make_counter_list_app(sink=sink)
    return create_element(App, None)
