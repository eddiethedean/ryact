# Translated: DOMPropertyOperations-test.js — ``input is=`` / ``input type=radio is=`` events (v112)
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


def test_input_is_matches_plain_input_oninput_onchange_click() -> None:
    reg = _marks()
    cus = _marks()
    r_in, r_ch, r_cl = _handlers(reg)
    c_in, c_ch, c_cl = _handlers(cus)
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "children": (
                    create_element("input", {"key": "r", "onInput": r_in, "onChange": r_ch, "onClick": r_cl}),
                    create_element(
                        "input",
                        {
                            "key": "c",
                            "is": "my-custom-element",
                            "onInput": c_in,
                            "onChange": c_ch,
                            "onClick": c_cl,
                        },
                    ),
                ),
            },
        )
    )
    div = c.root.children[0]
    inp_r = div.children[0]
    inp_c = div.children[1]
    assert isinstance(inp_r, ElementNode)
    assert isinstance(inp_c, ElementNode)

    inp_r.dispatch_event("input")
    inp_c.dispatch_event("input")
    assert reg == cus == {"in": 1, "ch": 1, "cl": 0}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("change")
    inp_c.dispatch_event("change")
    assert reg == cus == {"in": 0, "ch": 0, "cl": 0}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("click")
    inp_c.dispatch_event("click")
    assert reg == cus == {"in": 0, "ch": 0, "cl": 1}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("input")
    inp_c.dispatch_event("input")
    assert reg == cus == {"in": 1, "ch": 1, "cl": 0}


def test_input_type_radio_is_matches_plain_radio_click_and_input() -> None:
    reg = _marks()
    cus = _marks()
    r_in, r_ch, r_cl = _handlers(reg)
    c_in, c_ch, c_cl = _handlers(cus)
    c = Container()
    root = create_root(c)
    root.render(
        create_element(
            "div",
            {
                "children": (
                    create_element(
                        "input",
                        {"key": "r", "type": "radio", "onInput": r_in, "onChange": r_ch, "onClick": r_cl},
                    ),
                    create_element(
                        "input",
                        {
                            "key": "c",
                            "type": "radio",
                            "is": "my-custom-element",
                            "onInput": c_in,
                            "onChange": c_ch,
                            "onClick": c_cl,
                        },
                    ),
                ),
            },
        )
    )
    div = c.root.children[0]
    inp_r = div.children[0]
    inp_c = div.children[1]
    assert isinstance(inp_r, ElementNode)
    assert isinstance(inp_c, ElementNode)

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("click")
    inp_c.dispatch_event("click")
    assert reg == cus == {"in": 0, "ch": 1, "cl": 1}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("input")
    inp_c.dispatch_event("input")
    assert reg == cus == {"in": 1, "ch": 0, "cl": 0}

    reg.update({"in": 0, "ch": 0, "cl": 0})
    cus.update({"in": 0, "ch": 0, "cl": 0})
    inp_r.dispatch_event("click")
    inp_c.dispatch_event("click")
    assert reg == cus == {"in": 0, "ch": 1, "cl": 1}
