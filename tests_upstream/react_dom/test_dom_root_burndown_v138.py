"""ReactDOMRoot-test.js parity: createRoot, hydrateRoot, render, unmount (v138)."""

from __future__ import annotations

import warnings
from collections.abc import Iterator

import pytest
from ryact import Component, create_element
from ryact.dev import is_dev
from ryact_dom.dom import Container, ElementNode, TextNode
from ryact_dom.root import create_root, hydrate_root
from ryact_dom.root_dev import reset_root_dev_state
from ryact_dom.server import render_to_string


@pytest.fixture(autouse=True)
def _reset_root_dev() -> Iterator[None]:
    reset_root_dev_state()
    yield


def _host(c: Container) -> ElementNode:
    h = c.root.children[0]
    assert isinstance(h, ElementNode)
    return h


def test_renders_children() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    assert c.text_content == "Hi"


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_if_a_callback_parameter_is_provided_to_render() -> None:
    c = Container()
    r = create_root(c)
    cb = lambda: None
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", None, "Hi"), cb)
    assert any("does not support the second callback argument" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warn_if_a_object_is_passed_to_root_render() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", None, "Child"), {})
    assert any("second argument to root.render" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warn_if_a_container_is_passed_to_root_render() -> None:
    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", None, "Child"), c)
    assert any("passed a container to the second argument" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_if_a_callback_parameter_is_provided_to_unmount() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    cb = lambda: None
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.unmount(cb)
    assert any("does not support a callback argument" in str(w.message) for w in rec)


def test_unmounts_children() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    assert c.text_content == "Hi"
    r.unmount()
    assert c.text_content == ""


def test_can_be_immediately_unmounted() -> None:
    c = Container()
    r = create_root(c)
    r.unmount()


def test_supports_hydration() -> None:
    markup_host = create_element("span", {"class": "server"}, "text")
    c = Container()
    c.root.children = [
        ElementNode(tag="span", props={"class": "server"}, children=[TextNode(text="text")]),
    ]
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        hydrate_root(c, create_element("span", {"class": "client"}, "text"))
    assert any("hydrated but some attributes" in str(w.message) for w in rec)


def test_clears_existing_children() -> None:
    c = Container()
    c.root.children = [TextNode(text="ab")]
    r = create_root(c)
    r.render(
        create_element(
            "div",
            None,
            create_element("span", None, "c"),
            create_element("span", None, "d"),
        ),
    )
    assert c.text_content == "cd"
    r.render(
        create_element(
            "div",
            None,
            create_element("span", None, "d"),
            create_element("span", None, "c"),
        ),
    )
    assert c.text_content == "dc"


def test_throws_a_good_message_on_invalid_containers() -> None:
    with pytest.raises(TypeError, match="Target container is not a DOM element"):
        create_root(object())  # type: ignore[arg-type]


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_when_creating_two_roots_managing_the_same_container() -> None:
    c = Container()
    create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_root(c)
    assert any("already been passed to createRoot" in str(w.message) for w in rec)


def test_does_not_warn_when_creating_second_root_after_first_one_is_unmounted() -> None:
    c = Container()
    r = create_root(c)
    r.unmount()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_root(c)
    assert not any("already been passed to createRoot" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_if_creating_a_root_on_the_document_body() -> None:
    c = Container()
    c._is_document_body = True  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        create_root(c)
    assert any("document.body" in str(w.message) for w in rec)


def test_warns_if_updating_a_root_that_has_had_its_contents_removed() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    c.root.children.clear()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", None, "Hi"))
    assert not rec


def test_should_render_different_components_in_same_root() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None))
    assert _host(c).tag == "div"
    r.render(create_element("span", None))
    assert _host(c).tag == "span"


def test_should_not_warn_if_mounting_into_non_empty_node() -> None:
    c = Container()
    c.root.children = [TextNode(text=" ")]
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(create_element("div", None))
    assert not any("non-empty" in str(w.message) for w in rec)


def test_should_reuse_markup_if_rendering_to_the_same_target_twice() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "a"))
    first = c.root.children[0]
    r.render(create_element("div", None, "a"))
    assert c.root.children[0] is first


def test_should_unmount_and_remount_if_the_key_changes() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", {"key": "orange"}, "orange"))
    first_id = id(_host(c))
    assert _host(c).children[0].text == "orange"  # type: ignore[union-attr]
    r.render(create_element("div", {"key": "green"}, "green"))
    second_id = id(_host(c))
    assert second_id != first_id
    assert _host(c).children[0].text == "green"  # type: ignore[union-attr]
    r.render(create_element("div", {"key": "green"}, "blue"))
    assert id(_host(c)) == second_id
    assert _host(c).children[0].text == "blue"  # type: ignore[union-attr]


def test_throws_if_unmounting_a_root_that_has_had_its_contents_removed() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    c.root.children.clear()
    with pytest.raises(RuntimeError, match="not a child of this node"):
        r.unmount()


def test_unmount_is_synchronous() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    assert c.text_content == "Hi"
    r.unmount()
    assert c.text_content == ""


def test_throws_if_an_unmounted_root_is_updated() -> None:
    c = Container()
    r = create_root(c)
    r.render(create_element("div", None, "Hi"))
    r.unmount()
    with pytest.raises(RuntimeError, match="Cannot update an unmounted root"):
        r.render(create_element("div", None, "back"))


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_if_root_is_unmounted_inside_an_effect() -> None:
    c2 = Container()
    r2 = create_root(c2)

    class _UnmountDuringRender(Component):
        def render(self) -> object:
            r2.unmount()
            return create_element("div", None, "Hi")

    c1 = Container()
    r1 = create_root(c1)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r1.render(create_element(_UnmountDuringRender, None))
    assert any("synchronously unmount a root while React was already rendering" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="comment containers are not supported in ryact-dom")
def test_errors_if_container_is_a_comment_node() -> None:
    pytest.skip("ryact-dom Container model does not support comment-node mounts")


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warn_if_no_children_passed_to_hydrate_root() -> None:
    c = Container()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        hydrate_root(c)
    assert any("Must provide initial children" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warn_if_jsx_passed_to_create_root() -> None:
    c = Container()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        with pytest.raises(TypeError, match="Target container is not a DOM element"):
            create_root(create_element("div", None, "Child"))  # type: ignore[arg-type]
    assert any("passed a JSX element to createRoot" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_when_given_a_function() -> None:
    def component() -> object:
        return create_element("div", None)

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(component)  # type: ignore[arg-type]
    assert any("Functions are not valid as a React child" in str(w.message) for w in rec)


@pytest.mark.skipif(not is_dev(), reason="createRoot DEV warnings")
def test_warns_when_given_a_symbol() -> None:
    class _Sym:
        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"Symbol({self.name})"

    c = Container()
    r = create_root(c)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        r.render(_Sym("foo"))  # type: ignore[arg-type]
    assert any("Symbols are not valid as a React child" in str(w.message) for w in rec)


def test_hydrate_and_render_to_string_smoke() -> None:
    html = render_to_string(create_element("div", {"id": "x"}, "y"))
    assert html == '<div id="x">y</div>'
