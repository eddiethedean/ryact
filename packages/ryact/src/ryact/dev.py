from __future__ import annotations

_DEV = True


def is_dev() -> bool:
    return _DEV


def set_dev(value: bool) -> None:
    global _DEV
    _DEV = bool(value)
