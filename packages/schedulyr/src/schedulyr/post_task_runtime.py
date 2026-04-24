"""
Mock ``global.scheduler`` + ``TaskController`` for ``SchedulerPostTask-test.js`` parity.

Mirrors the inline ``installMockBrowserRuntime`` in upstream
``packages/scheduler/src/__tests__/SchedulerPostTask-test.js``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional


@dataclass
class PostTaskMockRuntime:
    """Virtual time, event log, ``postTask`` / ``yield`` queue, and ``setTimeout`` error sink."""

    _event_log: list[str] = field(default_factory=list)
    _current_time: float = 0.0
    _task_queue: dict[int, dict[str, Any]] = field(default_factory=dict)
    _id_counter: int = 0

    def __post_init__(self) -> None:
        self.performance = SimpleNamespace(now=self._performance_now)
        self.window = SimpleNamespace(performance=self.performance)
        self.scheduler = SimpleNamespace()
        self.scheduler.postTask = self._post_task
        setattr(self.scheduler, "yield", self._scheduler_yield)
        self._yield_impl: Optional[Callable[[dict[str, Any]], Any]] = self._scheduler_yield

    def _performance_now(self) -> float:
        return self._current_time

    def advance_time(self, ms: float) -> None:
        self._current_time += ms

    def log(self, val: str) -> None:
        self._event_log.append(val)

    def is_log_empty(self) -> bool:
        return len(self._event_log) == 0

    def assert_log(self, expected: list[str]) -> None:
        actual = self._event_log
        self._event_log = []
        assert actual == expected, f"expected {expected!r} got {actual!r}"

    def _ensure_log_empty(self) -> None:
        if self._event_log:
            raise RuntimeError("Log is not empty. Call assertLog before continuing.")

    def flush_tasks(self) -> None:
        self._ensure_log_empty()
        prev = self._task_queue
        self._task_queue = {}
        for entry in prev.values():
            ctrl = entry["controller"]
            if getattr(ctrl, "_aborted", False):
                continue
            tid = entry["id"]
            cb = entry["callback"]
            resolve = entry["resolve"]
            self.log(f"Task {tid} Fired")
            cb(False)
            resolve()

    def set_timeout(self, cb: Callable[[], None]) -> None:
        try:
            cb()
        except BaseException as e:
            self.log(f"Error: {e}")

    def remove_yield(self) -> None:
        """Match upstream ``delete global.scheduler.yield`` (nested describe)."""
        if hasattr(self.scheduler, "yield"):
            delattr(self.scheduler, "yield")

    def wire_default_yield(self) -> None:
        """Restore ``scheduler.yield`` (top-level ``SchedulerPostTask`` describe)."""
        setattr(self.scheduler, "yield", self._scheduler_yield)

    def _post_task(
        self,
        callback: Callable[[bool], Any],
        options: dict[str, Any],
    ) -> _PostTaskPromise:
        signal = options.get("signal")
        priority = signal.get("priority") if isinstance(signal, dict) else None
        bracket = " " if priority is None else str(priority)
        tid = self._id_counter
        self._id_counter += 1
        self.log(f"Post Task {tid} [{bracket}]")
        ctrl = signal["_controller"] if isinstance(signal, dict) else None
        assert ctrl is not None
        if getattr(ctrl, "_aborted", False):
            return _PostTaskPromise()

        def resolve() -> None:
            pass

        def reject(_e: BaseException) -> None:
            pass

        self._task_queue[id(ctrl)] = {
            "id": tid,
            "callback": callback,
            "resolve": resolve,
            "reject": reject,
            "controller": ctrl,
        }
        return _PostTaskPromise()

    def _scheduler_yield(self, options: dict[str, Any]) -> _YieldThenable:
        signal = options.get("signal", {})
        priority = signal.get("priority") if isinstance(signal, dict) else None
        bracket = " " if priority is None else str(priority)
        yid = self._id_counter
        self._id_counter += 1
        self.log(f"Yield {yid} [{bracket}]")
        return _YieldThenable(self, signal, yid)


class TaskController:
    """Minimal ``TaskController`` matching upstream tests."""

    def __init__(self, priority: Optional[str] = None) -> None:
        self.signal: dict[str, Any] = {"_controller": self, "priority": priority}
        self._aborted = False

    def abort(self) -> None:
        self._aborted = True


class _YieldThenable:
    """Return value of ``scheduler.yield`` — supports ``.then(cb)``."""

    def __init__(self, rt: PostTaskMockRuntime, signal: dict[str, Any], yid: int) -> None:
        self._rt = rt
        self._signal = signal
        self._yid = yid

    def then(self, on_fulfilled: Callable[[], Any]) -> _PostTaskPromise:
        rt = self._rt
        ctrl = self._signal["_controller"]
        rt._task_queue[id(ctrl)] = {
            "id": self._yid,
            "callback": lambda _d: on_fulfilled(),
            "resolve": lambda: None,
            "reject": lambda _e: None,
            "controller": ctrl,
        }
        return _PostTaskPromise()


class _PostTaskPromise:
    def catch(self, _handler: Callable[[Any], Any]) -> _PostTaskPromise:
        return self
