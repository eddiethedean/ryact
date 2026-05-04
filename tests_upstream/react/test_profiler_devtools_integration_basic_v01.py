from __future__ import annotations

from ryact.devtools import get_devtools_hook, install_devtools_hook


def test_devtools_hook_install_and_detect() -> None:
    hook = object()
    install_devtools_hook(hook)
    try:
        assert get_devtools_hook() is hook
    finally:
        install_devtools_hook(None)

