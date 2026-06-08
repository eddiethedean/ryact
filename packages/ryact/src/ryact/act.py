from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

_act_environment_enabled: ContextVar[bool] = ContextVar("ryact_act_environment_enabled", default=False)
_in_act_scope: ContextVar[bool] = ContextVar("ryact_in_act_scope", default=False)


def set_act_environment_enabled(value: bool) -> None:
    _act_environment_enabled.set(bool(value))


def is_act_environment_enabled() -> bool:
    return _act_environment_enabled.get()


def is_in_act_scope() -> bool:
    return _in_act_scope.get()


@contextmanager
def act_scope() -> Generator[None, None, None]:
    tok = _in_act_scope.set(True)
    try:
        yield
    finally:
        _in_act_scope.reset(tok)
