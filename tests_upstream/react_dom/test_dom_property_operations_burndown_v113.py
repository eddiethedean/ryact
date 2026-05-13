# Translated: DOMPropertyOperations-test.js — ``select is=`` click/input/change parity (v113)
from __future__ import annotations

from ryact import create_element
from ryact_dom.dom import Container, ElementNode, SyntheticEvent
from ryact_dom.root import create_root


def _marks() -> dict[str, int]:
    return {"in": 0, "ch": 0, "cl": 0}


def _handlers(m: dict[str, int]) -> tuple[object, object, object]:
    def on_in(_: SyntheticEvent) -> None:
        m["in"] += 1

    def on_ch(_: SyntheticEvent) -> None:
        m["ch"] += 1

    def on_cl(_: SyntheticEvent) -> None:
        m["cl"] += 1

    return on_in, on_ch, on_cl


def _options(prefix: str) -> tuple[object, object]:
    return (
        create_element("option", {"key": f"{prefix}-a", "value": "a", "children": "A"}),
        create_element("option", {"key": f"{prefix}-b", "value": "b", "children": "B"}),
    )


def test_select_is_matches_plain_select_click_input_change() -> None:
    reg = _marks()
    cus = _marks()
    r_in, r_ch, r_cl = _handlers(reg)
    c_in, c_ch, c_cl = _handlers(cus)
    opts_r = _options("r")
    opts_c = _options("c")
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "children": (
                    create_element(
                        "select",
                        {
                            "key": "r",
                            "onInput": r_in,
                            "onChange": r_ch,
                            "onClick": r_cl,
                            "children": opts_r,
                        },
                    ),
                    create_element(
                        "select",
                        {
                            "key": "c",
                            "is": "my-custom-element",
                            "onInput": c_in,
                            "onChange": c_ch,
                            "onClick": c_cl,
                            "children": opts_c,
                        },
                    ),
                ),
            },
        )
    )
    div = c.root.children[0]
    sel_r = div.children[0]
    sel_c = div.children[1]
    assert isinstance(sel_r, ElementNode)
    assert isinstance(sel_c, ElementNode)

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    sel_r.dispatch_event("click")
    sel_c.dispatch_event("click")
    assert reg == cus == {"in": 0, "ch": 0, "cl": 1}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    sel_r.dispatch_event("input")
    sel_c.dispatch_event("input")
    assert reg == cus == {"in": 1, "ch": 0, "cl": 0}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    sel_r.dispatch_event("change")
    sel_c.dispatch_event("change")
    assert reg == cus == {"in": 0, "ch": 1, "cl": 0}
