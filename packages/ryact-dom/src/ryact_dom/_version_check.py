from __future__ import annotations

import importlib


def check_versions() -> None:
    """
    ReactMismatchedVersions parity: importing react-dom entrypoints should throw if the
    react-dom version does not match the React version.

    We model this as a strict equality check between `ryact.__version__` and
    `ryact_dom.__version__`.
    """
    ryact = importlib.import_module("ryact")
    ryact_dom = importlib.import_module("ryact_dom")
    rv = getattr(ryact, "__version__", None)
    dv = getattr(ryact_dom, "__version__", None)
    if rv is None or dv is None:
        return
    if str(rv) != str(dv):
        raise RuntimeError(f"Version mismatch: ryact={rv} ryact-dom={dv}")

