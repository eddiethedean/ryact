# Translated from: packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js
# Burndown v157: portal namespaces, empty portal unmount, namespace unwind on errors.
from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from ryact import Component, create_element, create_portal, create_ref, fragment
from ryact.dev import is_dev, set_dev
from ryact_dom.dom import Container, ElementNode
from ryact_dom.dom_internals import reset_component_dom_registry
from ryact_dom.legacy_mount import legacy_render, reset_legacy_mount_state
from ryact_dom.root import create_root
from ryact_dom.svg_namespace import HTML_NAMESPACE, MATH_NAMESPACE, SVG_NAMESPACE
from ryact_testkit import act, set_act_environment_enabled

HTML_NS = HTML_NAMESPACE
SVG_NS = SVG_NAMESPACE
MATH_NS = MATH_NAMESPACE


@pytest.fixture(autouse=True)
def _dev_and_legacy_state() -> Iterator[None]:
    prev = is_dev()
    set_dev(True)
    reset_legacy_mount_state()
    reset_component_dom_registry()
    yield
    reset_legacy_mount_state()
    reset_component_dom_registry()


def _ns_ref(bucket: list[str]) -> Callable[[object], None]:
    def attach(node: object) -> None:
        if isinstance(node, ElementNode):
            bucket.append(node.namespaceURI)

    return attach


def _use_portal(tree: object, portal_c: Container) -> object:
    return create_portal(children=tree, container=portal_c)


# --- ReactDOMLegacyFiber ---


def test_should_keep_track_of_namespace_across_portals_simple() -> None:
    portal_c = Container()
    svg_els: list[str] = []
    html_els: list[str] = []
    math_els: list[str] = []
    legacy_render(
        create_element(
            "svg",
            {"ref": _ns_ref(svg_els)},
            create_element("image", {"ref": _ns_ref(svg_els)}),
            _use_portal(create_element("div", {"ref": _ns_ref(html_els)}), portal_c),
            create_element("image", {"ref": _ns_ref(svg_els)}),
        ),
        Container(),
    )
    assert all(u == SVG_NS for u in svg_els)
    assert all(u == HTML_NS for u in html_els)

    portal_c2 = Container()
    svg_els, html_els, math_els = [], [], []
    legacy_render(
        create_element(
            "math",
            {"ref": _ns_ref(math_els)},
            create_element("mi", {"ref": _ns_ref(math_els)}),
            _use_portal(create_element("div", {"ref": _ns_ref(html_els)}), portal_c2),
            create_element("mi", {"ref": _ns_ref(math_els)}),
        ),
        Container(),
    )
    assert all(u == MATH_NS for u in math_els)
    assert all(u == HTML_NS for u in html_els)

    portal_c3 = Container()
    svg_els, html_els = [], []
    legacy_render(
        create_element(
            "div",
            {"ref": _ns_ref(html_els)},
            create_element("p", {"ref": _ns_ref(html_els)}),
            _use_portal(
                create_element(
                    "svg",
                    {"ref": _ns_ref(svg_els)},
                    create_element("image", {"ref": _ns_ref(svg_els)}),
                ),
                portal_c3,
            ),
            create_element("p", {"ref": _ns_ref(html_els)}),
        ),
        Container(),
    )
    assert all(u == SVG_NS for u in svg_els)
    assert all(u == HTML_NS for u in html_els)


def test_should_keep_track_of_namespace_across_portals_medium() -> None:
    p1, p2 = Container(), Container()
    svg_els: list[str] = []
    html_els: list[str] = []
    legacy_render(
        create_element(
            "svg",
            None,
            create_element("image", {"ref": _ns_ref(svg_els)}),
            _use_portal(create_element("div", {"ref": _ns_ref(html_els)}), p1),
            create_element("image", {"ref": _ns_ref(svg_els)}),
            _use_portal(create_element("div", {"ref": _ns_ref(html_els)}), p2),
            create_element("image", {"ref": _ns_ref(svg_els)}),
        ),
        Container(),
    )
    assert all(u == SVG_NS for u in svg_els)
    assert all(u == HTML_NS for u in html_els)

    p6 = Container()
    svg_els, html_els, math_els = [], [], []
    legacy_render(
        create_element(
            "div",
            None,
            create_element(
                "math",
                None,
                create_element("mi", {"ref": _ns_ref(math_els)}),
                _use_portal(
                    create_element(
                        "svg",
                        None,
                        create_element("image", {"ref": _ns_ref(svg_els)}),
                    ),
                    p6,
                ),
            ),
            create_element("p", {"ref": _ns_ref(html_els)}),
        ),
        Container(),
    )
    assert all(u == SVG_NS for u in svg_els)
    assert all(u == HTML_NS for u in html_els)
    assert all(u == MATH_NS for u in math_els)


def test_should_keep_track_of_namespace_across_portals_complex() -> None:
    p = Container()
    svg_els: list[str] = []
    html_els: list[str] = []
    legacy_render(
        create_element(
            "div",
            None,
            _use_portal(
                create_element(
                    "svg",
                    None,
                    create_element("image", {"ref": _ns_ref(svg_els)}),
                ),
                p,
            ),
            create_element("p", {"ref": _ns_ref(html_els)}),
            create_element("svg", None, create_element("image", {"ref": _ns_ref(svg_els)})),
        ),
        Container(),
    )
    assert all(u == SVG_NS for u in svg_els)
    assert all(u == HTML_NS for u in html_els)


def test_should_unmount_empty_portal_component_wherever_it_appears() -> None:
    portal_c = Container()

    class Wrapper(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state = {"show": True}

        def render(self) -> object:
            if not self.state["show"]:
                return create_element("div", None, create_element("div", None, "parent"))
            return create_element(
                "div",
                None,
                fragment(
                    create_portal(children=None, container=portal_c),
                    create_element("div", None, "child"),
                ),
                create_element("div", None, "parent"),
            )

    host = Container()
    inst_ref = create_ref()
    legacy_render(create_element(Wrapper, {"ref": inst_ref}), host)
    assert host.text_content == "childparent"
    assert portal_c.text_content == ""
    inst = inst_ref.current
    assert isinstance(inst, Wrapper)
    inst.set_state({"show": False})
    assert host.text_content == "parent"
    assert portal_c.text_content == ""


def test_should_reconcile_portal_children_null() -> None:
    portal_c = Container()
    host = Container()
    legacy_render(
        create_element("div", None, create_portal(children=create_element("div", None, "one"), container=portal_c)),
        host,
    )
    assert portal_c.text_content == "one"
    legacy_render(
        create_element("div", None, create_portal(children=None, container=portal_c)),
        host,
    )
    assert portal_c.text_content == ""


def test_should_unwind_namespaces_on_uncaught_errors() -> None:
    class Broken(Component):
        def render(self) -> object:
            raise RuntimeError("Hello")

    host = Container()
    with pytest.raises(RuntimeError, match="Hello"):
        legacy_render(create_element("svg", None, create_element(Broken)), host)
    html_els: list[str] = []
    legacy_render(create_element("div", {"ref": _ns_ref(html_els)}), host)
    assert html_els == [HTML_NS]


def test_should_unwind_namespaces_on_caught_errors() -> None:
    class Broken(Component):
        def render(self) -> object:
            raise RuntimeError("Hello")

    class ErrorBoundary(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state: dict[str, object | None] = {"error": None}

        def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
            self._state = {"error": error}

        def render(self) -> object:
            if self.state["error"] is not None:
                return create_element("p", {"ref": _ns_ref([])})
            child = self.props.get("children")
            if isinstance(child, tuple) and len(child) == 1:
                return child[0]
            return child

    host = Container()
    set_act_environment_enabled(True)
    try:
        with act():
            create_root(host).render(
                create_element(
                    "svg",
                    None,
                    create_element(
                        "foreignObject",
                        None,
                        create_element(ErrorBoundary, None, create_element("math", None, create_element(Broken))),
                    ),
                    create_element("image", {"ref": _ns_ref([])}),
                )
            )
        html_els: list[str] = []
        with act():
            create_root(Container()).render(create_element("div", {"ref": _ns_ref(html_els)}))
        assert html_els == [HTML_NS]
    finally:
        set_act_environment_enabled(False)


def test_should_unwind_namespaces_on_caught_errors_in_a_portal() -> None:
    portal_c = Container()

    class Broken(Component):
        def render(self) -> object:
            raise RuntimeError("Hello")

    class ErrorBoundary(Component):
        def __init__(self, **props: object) -> None:
            super().__init__(**props)
            self._state: dict[str, object | None] = {"error": None}

        def componentDidCatch(self, error: BaseException) -> None:  # noqa: N802
            self._state = {"error": error}

        def render(self) -> object:
            if self.state["error"] is not None:
                return create_element("image", {"ref": _ns_ref([])})
            child = self.props.get("children")
            if isinstance(child, tuple) and len(child) == 1:
                return child[0]
            return child

    host = Container()
    set_act_environment_enabled(True)
    try:
        with act():
            create_root(host).render(
                create_element(
                    "svg",
                    None,
                    create_element(
                        ErrorBoundary,
                        None,
                        create_portal(
                            children=create_element(
                                "svg",
                                None,
                                create_element("image", {"ref": _ns_ref([])}),
                                create_element(Broken),
                            ),
                            container=portal_c,
                        ),
                    ),
                    create_element("image", {"ref": _ns_ref([])}),
                )
            )
        svg_els: list[str] = []
        with act():
            create_root(Container()).render(
                create_element("svg", None, create_element("image", {"ref": _ns_ref(svg_els)}))
            )
        assert svg_els == [SVG_NS]
    finally:
        set_act_environment_enabled(False)
