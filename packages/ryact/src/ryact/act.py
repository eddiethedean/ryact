from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

_act_environment_enabled = False
_in_act_scope = False


def set_act_environment_enabled(value: bool) -> None:
    global _act_environment_enabled
    _act_environment_enabled = bool(value)


def is_act_environment_enabled() -> bool:
    return _act_environment_enabled


def is_in_act_scope() -> bool:
    return _in_act_scope


@contextmanager
def act_scope() -> Generator[None, None, None]:
    global _in_act_scope
    prev = _in_act_scope
    _in_act_scope = True
    try:
        yield
    finally:
        _in_act_scope = prev
