"""DOM console/window error reporting (ReactDOMConsoleErrorReporting parity subset)."""
from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any, cast

from ryact.dev import is_dev


def console_error_log(container: Any) -> list[Any]:
    log = getattr(container, "console_error_log", None)
    if not isinstance(log, list):
        log = []
        container.console_error_log = log  # type: ignore[attr-defined]
    return log


def window_error_log(container: Any) -> list[Any]:
    log = getattr(container, "window_error_log", None)
    if not isinstance(log, list):
        log = []
        container.window_error_log = log  # type: ignore[attr-defined]
    return log


def log_console_error(container: Any, err: BaseException, *extra: object) -> None:
    if extra:
        console_error_log(container).append((err, *extra))
    else:
        console_error_log(container).append(err)


def log_window_error(container: Any, err: BaseException) -> None:
    window_error_log(container).append(err)


def log_boundary_component_error(container: Any, err: BaseException, *, boundary_name: str) -> None:
    if is_dev():
        log_console_error(
            container,
            err,
            f"The above error occurred in the `<{boundary_name}>` component.",
        )
    else:
        log_console_error(container, err)


def warn_missing_error_boundary() -> None:
    if not is_dev():
        return
    warnings.warn(
        "An error occurred in the component.\n\n"
        "Consider adding an error boundary to your tree to customize error handling behavior.",
        RuntimeWarning,
        stacklevel=5,
    )


def report_uncaught_error(container: Any, err: BaseException, *, in_event_handler: bool = False) -> None:
    log_console_error(container, err)
    log_window_error(container, err)
    if not in_event_handler:
        warn_missing_error_boundary()


def report_event_handler_error(container: Any, err: BaseException) -> None:
    report_uncaught_error(container, err, in_event_handler=True)


def run_effects_phased(effects: list[Callable[[], None]], *, container: Any) -> None:
    destroys = [e for e in effects if getattr(e, "_ryact_effect_phase", None) == "destroy"]
    creates = [e for e in effects if getattr(e, "_ryact_effect_phase", None) != "destroy"]
    for fn in destroys + creates:
        try:
            fn()
        except BaseException as err:
            boundary_names = getattr(fn, "_ryact_dom_boundary_names", None)
            if isinstance(boundary_names, list) and boundary_names:
                log_boundary_component_error(
                    container,
                    cast(BaseException, err),
                    boundary_name=str(boundary_names[-1]),
                )
            else:
                report_uncaught_error(container, cast(BaseException, err))
            return
