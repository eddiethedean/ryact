from __future__ import annotations

from typing import Any

from ryact import (
    create_element,
    use,
    use_effect,
    use_memo,
    use_state,
)
from ryact.concurrent import Thenable
from ryact_testkit import WarningCapture, create_noop_root


def _span(text: str, *, key: str | None = None) -> Any:
    p: dict[str, Any] = {"text": text}
    if key is not None:
        p["key"] = key
    return create_element("span", p)


def test_use_combined_with_render_phase_updates() -> None:
    # Upstream: ReactUse-test.js — "use() combined with render phase updates"
    t = Thenable()
    t.resolve("ok")

    def App() -> Any:
        x = use(t)
        v, set_v = use_state(0)
        if x == "ok" and v < 2:
            set_v(v + 1)
        return _span(f"{x}:{v}")

    root = create_noop_root()
    root.render(create_element(App))
    root.flush()
    assert root.get_children_snapshot()["props"]["text"] == "ok:2"


def test_regression_updates_while_suspended_not_mistaken_for_render_phase() -> None:
    # Upstream: ReactUse-test.js
    # "regression test: updates while component is suspended should not be mistaken for render phase updates"
    t = Thenable()

    def Child() -> Any:
        use(t)
        return _span("child", key="c")

    def Parent() -> Any:
        v, set_v = use_state(0)

        def bump() -> None:
            set_v(1)

        use_effect(bump, ())
        return create_element(
            "div",
            {
                "key": "root",
                "children": [
                    _span(f"p:{v}", key="p"),
                    create_element(
                        "__suspense__",
                        {
                            "key": "s",
                            "fallback": _span("fb", key="fb"),
                            "children": (create_element(Child, {"key": "ch"}),),
                        },
                    ),
                ],
            },
        )

    root = create_noop_root()
    with WarningCapture() as wc:
        root.render(create_element(Parent))
        root.flush()
    msgs = " ".join(wc.messages).lower()
    assert "cannot update a component while rendering a different component" not in msgs

    t.resolve("done")
    root.flush()
    snap = root.get_children_snapshot()
    assert snap["type"] == "div"
    texts = sorted(c["props"]["text"] for c in (snap.get("children") or []) if isinstance(c, dict))
    assert texts == ["child", "p:1"]


def test_wrap_async_function_with_use_memo_skips_second_factory_while_loading() -> None:
    # Upstream: ReactUse-test.js
    # "wrap an async function with useMemo to skip running the function twice when loading new data"
    runs: list[str] = []
    t = Thenable()

    def factory() -> Thenable:
        runs.append("factory")
        return t

    def App() -> Any:
        memoed = use_memo(factory, ())
        val = use(memoed)
        return _span(str(val))

    root = create_noop_root()
    root.render(
        create_element(
            "__suspense__",
            {
                "key": "sus",
                "fallback": _span("loading", key="fb"),
                "children": (create_element(App, {"key": "app"}),),
            },
        )
    )
    root.flush()
    assert runs == ["factory"]
    assert root.get_children_snapshot()["props"]["text"] == "loading"

    t.resolve("data")
    root.flush()
    assert runs == ["factory"]
    assert root.get_children_snapshot()["props"]["text"] == "data"
