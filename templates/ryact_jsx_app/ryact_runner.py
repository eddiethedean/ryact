from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from ryact_dom import create_root
from ryact_dom.dom import Container

from scripts.jsx_to_py import eval_compiled


def _dump_dom(container: Container) -> str:
    def walk(node) -> str:
        from ryact_dom.dom import ElementNode, TextNode

        if isinstance(node, TextNode):
            return node.text
        if isinstance(node, ElementNode):
            attrs = ""
            if node.props:
                items = " ".join(f'{k}="{v}"' for k, v in sorted(node.props.items()))
                attrs = " " + items
            inner = "".join(walk(c) for c in node.children)
            return f"<{node.tag}{attrs}>{inner}</{node.tag}>"
        raise TypeError(type(node))

    return "".join(walk(c) for c in container.root.children)


def main() -> None:
    app_py = Path(__file__).parent / "build" / "app.py"
    code = app_py.read_text(encoding="utf8")

    element = eval_compiled(code, scope={})
    container = Container()
    root = create_root(container)
    root.render(cast(Any, element))

    print(_dump_dom(container))


if __name__ == "__main__":
    main()
