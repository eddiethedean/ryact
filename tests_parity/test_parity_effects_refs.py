from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from ryact import create_element

from tests_parity.apps.effects_refs_py import make_effects_refs_app
from tests_parity.helpers import (
    NoopSession,
    assert_equivalent,
    compile_tsx_to_module,
    eval_render_module,
    render_noop_sessioned,
)


def test_parity_effects_and_refs_mount_update_unmount(tmp_path: Path) -> None:
    py_log: list[str] = []
    py_sink: dict[str, object] = {}
    PyApp = make_effects_refs_app(sink=py_sink, log=py_log)

    py_element = create_element(PyApp, None)

    tsx = Path(__file__).parent / "apps" / "effects_refs.tsx"
    mod = compile_tsx_to_module(tmp_path, entry=tsx)
    jsx_log: list[str] = []
    jsx_sink: dict[str, object] = {}
    JsxApp = make_effects_refs_app(sink=jsx_sink, log=jsx_log)
    jsx_element = eval_render_module(mod, scope={"App": JsxApp})

    py_session = NoopSession.create()
    jsx_session = NoopSession.create()

    py_initial = render_noop_sessioned(py_session, py_element)
    jsx_initial = render_noop_sessioned(jsx_session, jsx_element)
    assert_equivalent(py_initial, jsx_initial)

    # Drive update: turn off child (unmount)
    set_on = cast(Callable[[Any], None], py_sink["set_on"])
    jsx_set_on = cast(Callable[[Any], None], jsx_sink["set_on"])
    set_on(False)
    jsx_set_on(False)

    py_session.clear_ops()
    jsx_session.clear_ops()

    py_after = render_noop_sessioned(py_session, py_element)
    jsx_after = render_noop_sessioned(jsx_session, eval_render_module(mod, scope={"App": JsxApp}))
    assert_equivalent(py_after, jsx_after)

    assert "effect:mount" in py_log
    # Cleanup ordering is still evolving; parity is enforced by snapshot/ops equality above.
    assert "effect:mount" in jsx_log
    assert any(s.startswith("cb_ref:") for s in py_log)
    assert any(s.startswith("cb_ref:") for s in jsx_log)
