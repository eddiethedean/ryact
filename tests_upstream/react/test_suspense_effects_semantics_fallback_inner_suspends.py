from __future__ import annotations

from ryact import Component, create_element
from ryact.concurrent import Suspend, Thenable, suspense
from ryact_testkit import create_noop_root


def _fallback_tree(*, inner_fb_text: str, t_inner: Thenable, ok_inner: dict[str, bool]) -> object:
    def InnerAsync() -> object:
        if not ok_inner["v"]:
            raise Suspend(t_inner)
        return create_element("span", {"text": "in-fb-resolved"})

    return suspense(
        fallback=create_element("div", {"text": inner_fb_text}),
        children=create_element(InnerAsync),
    )


class OuterPrimary(Component):
    def render(self) -> object:
        t_outer: Thenable = self.props["t_outer"]
        ok_outer: dict[str, bool] = self.props["ok_outer"]
        if not ok_outer["v"]:
            raise Suspend(t_outer)
        return create_element("span", {"text": "outer-primary"})


def test_fallback_that_contains_suspense_shows_inner_fallback() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be cleaned up inside of a fallback that suspends"
    t_outer, t_inner = Thenable(), Thenable()
    ok_outer, ok_inner = {"v": False}, {"v": False}

    root = create_noop_root()
    root.render(
        suspense(
            fallback=_fallback_tree(inner_fb_text="inner_fb", t_inner=t_inner, ok_inner=ok_inner),
            children=create_element(OuterPrimary, {"t_outer": t_outer, "ok_outer": ok_outer}),
        ),
    )
    snap = root.container.last_committed
    assert snap == {"type": "div", "key": None, "props": {"text": "inner_fb"}, "children": []}
    ok_inner["v"] = True
    t_inner.resolve()
    root.flush()
    mid = root.container.last_committed
    assert mid == {
        "type": "span",
        "key": None,
        "props": {"text": "in-fb-resolved"},
        "children": [],
    }
    ok_outer["v"] = True
    t_outer.resolve()
    root.flush()
    assert root.container.last_committed == {
        "type": "span",
        "key": None,
        "props": {"text": "outer-primary"},
        "children": [],
    }


def test_fallback_that_contains_suspense_shows_inner_fallback_alternate() -> None:
    # Upstream: ReactSuspenseEffectsSemantics-test.js
    # "should be cleaned up inside of a fallback that suspends (alternate)"
    t_outer, t_inner = Thenable(), Thenable()
    ok_outer, ok_inner = {"v": False}, {"v": False}

    root = create_noop_root()
    root.render(
        suspense(
            fallback=_fallback_tree(
                inner_fb_text="inner_fb_alt",
                t_inner=t_inner,
                ok_inner=ok_inner,
            ),
            children=create_element(OuterPrimary, {"t_outer": t_outer, "ok_outer": ok_outer}),
        ),
    )
    assert root.container.last_committed == {
        "type": "div",
        "key": None,
        "props": {"text": "inner_fb_alt"},
        "children": [],
    }
