from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from ryact import create_element
from ryact.concurrent import Thenable

from tests_parity.apps.transitions_suspense_py import make_transitions_suspense_app
from tests_parity.helpers import (
    NoopSession,
    assert_equivalent,
    compile_tsx_to_module,
    eval_render_module,
    render_noop_sessioned,
)


def test_parity_transitions_and_suspense(tmp_path: Path) -> None:
    py_thenable = Thenable()
    py_log: list[str] = []
    py_sink: dict[str, object] = {}
    PyApp = make_transitions_suspense_app(sink=py_sink, thenable=py_thenable, log=py_log)

    py_element = create_element(PyApp, None)

    tsx = Path(__file__).parent / "apps" / "transitions_suspense.tsx"
    mod = compile_tsx_to_module(tmp_path, entry=tsx)
    jsx_thenable = Thenable()
    jsx_log: list[str] = []
    jsx_sink: dict[str, object] = {}
    JsxApp = make_transitions_suspense_app(sink=jsx_sink, thenable=jsx_thenable, log=jsx_log)
    jsx_element = eval_render_module(mod, scope={"App": JsxApp})

    py_session = NoopSession.create()
    jsx_session = NoopSession.create()

    py_initial = render_noop_sessioned(py_session, py_element)
    jsx_initial = render_noop_sessioned(jsx_session, jsx_element)
    assert_equivalent(py_initial, jsx_initial)

    start = cast(Callable[[Callable[[], None]], None], py_sink["start"])
    set_value = cast(Callable[[Any], None], py_sink["set_value"])
    jsx_start = cast(Callable[[Callable[[], None]], None], jsx_sink["start"])
    jsx_set_value = cast(Callable[[Any], None], jsx_sink["set_value"])

    def do_transition() -> None:
        set_value("SUSPEND")

    start(do_transition)
    jsx_start(lambda: jsx_set_value("SUSPEND"))

    py_session.clear_ops()
    jsx_session.clear_ops()

    # Should show fallback due to suspend
    py_fb = render_noop_sessioned(py_session, py_element)
    jsx_fb = render_noop_sessioned(jsx_session, eval_render_module(mod, scope={"App": JsxApp}))
    assert_equivalent(py_fb, jsx_fb)

    py_thenable.resolve()
    set_value("B")
    jsx_thenable.resolve()
    jsx_set_value("B")

    py_session.clear_ops()
    jsx_session.clear_ops()

    py_done = render_noop_sessioned(py_session, py_element)
    jsx_done = render_noop_sessioned(jsx_session, eval_render_module(mod, scope={"App": JsxApp}))
    assert_equivalent(py_done, jsx_done)
