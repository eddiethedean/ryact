"""
``SchedulerPostTask.js``-aligned harness for ``SchedulerPostTask-test.js`` parity.

Drives :class:`schedulyr.post_task_runtime.PostTaskMockRuntime` (``scheduler.postTask`` /
``scheduler.yield``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .post_task_runtime import PostTaskMockRuntime, TaskController
from .scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
)


def _priority_to_post_task_label(priority_level: int) -> str:
    if priority_level in (IMMEDIATE_PRIORITY, USER_BLOCKING_PRIORITY):
        return "user-blocking"
    if priority_level in (LOW_PRIORITY, NORMAL_PRIORITY):
        return "user-visible"
    if priority_level == IDLE_PRIORITY:
        return "background"
    return "user-visible"


@dataclass
class PostTaskCallbackNode:
    _controller: TaskController


class PostTaskSchedulerHarness:
    """Subset of ``unstable_*`` API from ``SchedulerPostTask.js``."""

    def __init__(self, runtime: PostTaskMockRuntime) -> None:
        self._rt = runtime
        self._yield_interval = 5.0
        self._deadline = 0.0

    def unstable_now(self) -> float:
        return float(self._rt.performance.now())

    def unstable_should_yield(self) -> bool:
        return self.unstable_now() >= self._deadline

    def unstable_request_paint(self) -> None:
        pass

    def unstable_schedule_callback(
        self,
        priority_level: int,
        callback: Callable[[bool], Any],
        options: Optional[dict[str, Any]] = None,
    ) -> PostTaskCallbackNode:
        post_label = _priority_to_post_task_label(priority_level)
        controller = TaskController(priority=post_label)
        delay = 0
        if isinstance(options, dict) and options.get("delay") is not None:
            delay = int(options["delay"])
        post_options = {"delay": delay, "signal": controller.signal}
        node = PostTaskCallbackNode(_controller=controller)
        self._rt.scheduler.postTask(
            lambda d=False: self._run_task(
                priority_level,
                post_label,
                controller,
                callback,
                d,
            ),
            post_options,
        ).catch(lambda _e: None)
        return node

    def _run_task(
        self,
        priority_level: int,
        post_label: str,
        controller: TaskController,
        callback: Callable[[bool], Any],
        did_timeout: bool,
    ) -> None:
        self._deadline = self.unstable_now() + self._yield_interval
        try:
            result = callback(did_timeout)
            if callable(result):
                continuation: Callable[[bool], Any] = result
                cont_opts = {"signal": controller.signal}
                sched = self._rt.scheduler
                if hasattr(sched, "yield"):
                    yield_fn = getattr(sched, "yield")

                    def chain() -> None:
                        self._run_task(
                            priority_level,
                            post_label,
                            controller,
                            continuation,
                            False,
                        )

                    yield_fn(cont_opts).then(chain).catch(lambda _e: None)
                else:
                    self._rt.scheduler.postTask(
                        lambda d=False: self._run_task(
                            priority_level,
                            post_label,
                            controller,
                            continuation,
                            d,
                        ),
                        cont_opts,
                    ).catch(lambda _e: None)
        except BaseException as exc:
            def raise_later(e: BaseException = exc) -> None:
                self._raise(e)

            self._rt.set_timeout(raise_later)

    @staticmethod
    def _raise(e: BaseException) -> None:
        raise e

    def unstable_cancel_callback(self, node: PostTaskCallbackNode) -> None:
        node._controller.abort()
        self._rt._task_queue.pop(id(node._controller), None)


unstable_NormalPriority = NORMAL_PRIORITY
unstable_UserBlockingPriority = USER_BLOCKING_PRIORITY
unstable_ImmediatePriority = IMMEDIATE_PRIORITY
unstable_LowPriority = LOW_PRIORITY
unstable_IdlePriority = IDLE_PRIORITY
