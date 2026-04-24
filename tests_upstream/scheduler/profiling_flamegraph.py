"""
Decode profiling ``Int32Array`` / bytes into the ASCII flamegraph string from
``SchedulerProfiling-test.js`` ``stopProfilingAndPrintFlamegraph``.
"""

from __future__ import annotations

import struct
from typing import Any, Optional

from schedulyr.scheduler import (
    IDLE_PRIORITY,
    IMMEDIATE_PRIORITY,
    LOW_PRIORITY,
    NORMAL_PRIORITY,
    USER_BLOCKING_PRIORITY,
)
from schedulyr.scheduler_profiling_buffer import (
    SCHEDULER_RESUME_EVENT,
    SCHEDULER_SUSPEND_EVENT,
    TASK_CANCEL_EVENT,
    TASK_COMPLETE_EVENT,
    TASK_ERROR_EVENT,
    TASK_RUN_EVENT,
    TASK_START_EVENT,
    TASK_YIELD_EVENT,
)


def _priority_level_to_string(priority_level: int) -> Optional[str]:
    if priority_level == IMMEDIATE_PRIORITY:
        return "Immediate"
    if priority_level == USER_BLOCKING_PRIORITY:
        return "User-blocking"
    if priority_level == NORMAL_PRIORITY:
        return "Normal"
    if priority_level == LOW_PRIORITY:
        return "Low"
    if priority_level == IDLE_PRIORITY:
        return "Idle"
    return None


def stop_profiling_and_print_flamegraph(event_bytes: Optional[bytes]) -> str:
    """Mirror upstream ``stopProfilingAndPrintFlamegraph`` (minus ``(empty profile)`` branch)."""
    if event_bytes is None:
        return "(empty profile)"
    # Upstream ``Int32Array`` buffer is zero-filled; an empty write still yields a leading 0 opcode.
    if len(event_bytes) == 0:
        event_bytes = struct.pack("<i", 0)

    event_log = struct.unpack(f"<{len(event_bytes) // 4}i", event_bytes)
    tasks: dict[int, dict[str, Any]] = {}
    main_thread_runs: list[int] = []
    is_suspended = True
    i = 0
    n = len(event_log)

    while i < n:
        instruction = event_log[i]
        if instruction == 0:
            break
        time = event_log[i + 1]
        if instruction == TASK_START_EVENT:
            task_id = event_log[i + 2]
            priority_level = event_log[i + 3]
            tasks[task_id] = {
                "id": task_id,
                "priorityLevel": priority_level,
                "label": None,
                "start": time,
                "end": -1,
                "exitStatus": None,
                "runs": [],
            }
            i += 4
        elif instruction == TASK_COMPLETE_EVENT:
            if is_suspended:
                raise RuntimeError("Task cannot Complete outside the work loop.")
            task_id = event_log[i + 2]
            task = tasks.get(task_id)
            if task is None:
                raise RuntimeError("Task does not exist.")
            task["end"] = time
            task["exitStatus"] = "completed"
            i += 3
        elif instruction == TASK_ERROR_EVENT:
            if is_suspended:
                raise RuntimeError("Task cannot Error outside the work loop.")
            task_id = event_log[i + 2]
            task = tasks.get(task_id)
            if task is None:
                raise RuntimeError("Task does not exist.")
            task["end"] = time
            task["exitStatus"] = "errored"
            i += 3
        elif instruction == TASK_CANCEL_EVENT:
            task_id = event_log[i + 2]
            task = tasks.get(task_id)
            if task is None:
                raise RuntimeError("Task does not exist.")
            task["end"] = time
            task["exitStatus"] = "canceled"
            i += 3
        elif instruction in (TASK_RUN_EVENT, TASK_YIELD_EVENT):
            if is_suspended:
                raise RuntimeError("Task cannot Run or Yield outside the work loop.")
            task_id = event_log[i + 2]
            task = tasks.get(task_id)
            if task is None:
                raise RuntimeError("Task does not exist.")
            task["runs"].append(time)
            i += 4
        elif instruction == SCHEDULER_SUSPEND_EVENT:
            if is_suspended:
                raise RuntimeError("Scheduler cannot Suspend outside the work loop.")
            is_suspended = True
            main_thread_runs.append(time)
            i += 3
        elif instruction == SCHEDULER_RESUME_EVENT:
            if not is_suspended:
                raise RuntimeError("Scheduler cannot Resume inside the work loop.")
            is_suspended = False
            main_thread_runs.append(time)
            i += 3
        else:
            raise RuntimeError(f"Unknown instruction type: {instruction}")

    label_column_width = 30
    microseconds_per_char = 50000

    result = ""
    main_base = "!!! Main thread "
    main_thread_label_column = main_base + " " * (
        label_column_width - len(main_base) - 1
    )
    main_thread_timeline_column = ""
    is_main_thread_busy = True
    for t in main_thread_runs:
        index = int(t / microseconds_per_char)
        nfill = max(0, index - len(main_thread_timeline_column))
        main_thread_timeline_column += ("█" if is_main_thread_busy else "░") * nfill
        is_main_thread_busy = not is_main_thread_busy
    result += f"{main_thread_label_column}│{main_thread_timeline_column}\n"

    tasks_by_priority = sorted(tasks.values(), key=lambda t1: t1["priorityLevel"])
    for task in tasks_by_priority:
        label = task["label"]
        if label is None:
            label = "Task"
        pls = _priority_level_to_string(task["priorityLevel"])
        label_column = f"Task {task['id']} [{pls}]"
        label_column += " " * (label_column_width - len(label_column) - 1)

        timeline_column = " " * int(task["start"] / microseconds_per_char)
        is_running = False
        for rt in task["runs"]:
            index = int(rt / microseconds_per_char)
            nfill = max(0, index - len(timeline_column))
            timeline_column += ("█" if is_running else "░") * nfill
            is_running = not is_running

        end_index = int(task["end"] / microseconds_per_char)
        nfill = max(0, end_index - len(timeline_column))
        timeline_column += ("█" if is_running else "░") * nfill

        if task["exitStatus"] != "completed":
            timeline_column += f"🡐 {task['exitStatus']}"

        result += f"{label_column}│{timeline_column}\n"

    return "\n" + result
