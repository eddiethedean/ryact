from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

from ryact_dom import create_root
from ryact_dom.dom import Container, ElementNode, TextNode

from scripts.jsx_to_py import eval_compiled


def dom_to_html(container: Container) -> str:
    def walk(node) -> str:
        if isinstance(node, TextNode):
            return node.text
        if isinstance(node, ElementNode):
            attrs = ""
            if node.props:
                props = {k: v for k, v in node.props.items() if k != "children"}
                items = " ".join(f'{k}="{v}"' for k, v in sorted(props.items()))
                attrs = " " + items
            inner = "".join(walk(c) for c in node.children)
            return f"<{node.tag}{attrs}>{inner}</{node.tag}>"
        raise TypeError(type(node))

    return "".join(walk(c) for c in container.root.children)


def _format_tsx_loc(module_globals: dict[str, object]) -> str | None:
    source = module_globals.get("__ryact_jsx_source__")
    mapping = module_globals.get("__ryact_jsx_map__")
    if not isinstance(source, str) or not isinstance(mapping, list) or not mapping:
        return None
    first = mapping[0]
    if not isinstance(first, dict):
        return None
    first_any = cast(dict[str, Any], first)
    loc = first_any.get("loc")
    if not isinstance(loc, dict):
        return None
    loc_any = cast(dict[str, Any], loc)
    start = loc_any.get("start")
    if not isinstance(start, dict):
        return None
    start_any = cast(dict[str, Any], start)
    line = start_any.get("line")
    col = start_any.get("col")
    if not isinstance(line, int) or not isinstance(col, int):
        return None
    return f"{source}:{line}:{col}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a compiled JSX->Python module against ryact-dom."
    )
    parser.add_argument("module", type=Path, help="Path to generated Python module (mode=module).")
    args = parser.parse_args()

    code = args.module.read_text(encoding="utf8")
    try:
        element = eval_compiled(code, scope={})
    except Exception:
        g: dict[str, object] = {}
        loc: dict[str, object] = {}
        exec(code, g, loc)
        hint = _format_tsx_loc({**g, **loc})
        if hint is not None:
            print(f"Original TSX location (best-effort): {hint}")
        raise

    container = Container()
    root = create_root(container)
    root.render(cast(Any, element))

    print(dom_to_html(container))


if __name__ == "__main__":
    main()
