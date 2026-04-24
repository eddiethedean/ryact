from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from ryact import create_element

from tests_parity.apps.counter_list_py import make_counter_list_app
from tests_parity.helpers import (
    NoopSession,
    assert_equivalent,
    compile_tsx_to_module,
    eval_render_module,
    render_noop_sessioned,
)


def test_parity_counter_and_keyed_list_reorder(tmp_path: Path) -> None:
    # Python lane tree
    py_sink: dict[str, object] = {}
    PyApp = make_counter_list_app(sink=py_sink)
    py_element = create_element(PyApp, None)

    # JSX lane tree: TSX uses <App /> and resolves App from scope.
    jsx_sink: dict[str, object] = {}
    JsxApp = make_counter_list_app(sink=jsx_sink)
    tsx = Path(__file__).parent / "apps" / "counter_list.tsx"
    mod = compile_tsx_to_module(tmp_path, entry=tsx)
    jsx_element = eval_render_module(mod, scope={"App": JsxApp})

    # Initial render equivalence
    py_session = NoopSession.create()
    jsx_session = NoopSession.create()

    py_initial = render_noop_sessioned(py_session, py_element)
    jsx_initial = render_noop_sessioned(jsx_session, jsx_element)
    assert_equivalent(py_initial, jsx_initial)

    # Drive identical updates using captured setters
    set_count = cast(Callable[[Any], None], py_sink["set_count"])
    set_order = cast(Callable[[Any], None], py_sink["set_order"])
    jsx_set_count = cast(Callable[[Any], None], jsx_sink["set_count"])
    jsx_set_order = cast(Callable[[Any], None], jsx_sink["set_order"])

    set_count(1)
    set_order(["c", "b", "a"])
    jsx_set_count(1)
    jsx_set_order(["c", "b", "a"])

    py_session.clear_ops()
    jsx_session.clear_ops()

    py_after = render_noop_sessioned(py_session, py_element)
    jsx_after = render_noop_sessioned(jsx_session, eval_render_module(mod, scope={"App": JsxApp}))
    assert_equivalent(py_after, jsx_after)
