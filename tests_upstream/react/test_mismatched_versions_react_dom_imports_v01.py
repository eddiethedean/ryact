from __future__ import annotations

import importlib
import sys

import pytest


def _import_fresh(name: str) -> None:
    sys.modules.pop(name, None)
    importlib.import_module(name)


@pytest.mark.parametrize(
    "mod",
    [
        "ryact_dom.client",
        "ryact_dom.server",
        "ryact_dom.server_browser",
        "ryact_dom.server_bun",
        "ryact_dom.server_edge",
        "ryact_dom.server_node",
        "ryact_dom.static",
        "ryact_dom.static_browser",
        "ryact_dom.static_edge",
        "ryact_dom.static_node",
    ],
)
def test_ryact_dom_entrypoints_throw_on_version_mismatch(mod: str) -> None:
    import ryact

    prev = ryact.__version__
    ryact.__version__ = "0.0.0"
    try:
        with pytest.raises(RuntimeError, match="Version mismatch"):
            _import_fresh(mod)
    finally:
        ryact.__version__ = prev

