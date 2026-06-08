"""DOM console/window error reporting (ReactDOMConsoleErrorReporting parity subset)."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ryact.dev import is_dev

LEGACY_RENDER_DEPRECATION = (
    "ReactDOM.render has not been supported since React 18. Use createRoot instead. "
    "Until you switch to the new API, your app will behave as if it's running React 17."
)


@dataclass
class _DomAggregateError(RuntimeError):
    errors: list[BaseException]

    def __init__(self, label: str, errors: list[BaseException]) -> None:
        super().__init__(label)
        self.errors = errors


def _is_legacy_container(container: Any) -> bool:
    from .legacy_mount import _CONTAINER_MOUNT_MODE

    return _CONTAINER_MOUNT_MODE.get(id(container)) == "legacy"


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


def log_console_error_message(container: Any, message: str) -> None:
    console_error_log(container).append(message)


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
    if _is_legacy_container(container) and not in_event_handler:
        report_uncaught_legacy_error(container, err)
        return
    log_console_error(container, err)
    log_window_error(container, err)
    if not in_event_handler:
        warn_missing_error_boundary()


def report_uncaught_legacy_error(container: Any, err: BaseException) -> None:
    log_window_error(container, err)
    warn_missing_error_boundary()


def report_event_handler_error(container: Any, err: BaseException) -> None:
    if _is_legacy_container(container):
        log_window_error(container, err)
        raise err
    report_uncaught_error(container, err, in_event_handler=True)


def log_legacy_render_deprecation(container: Any) -> None:
    if is_dev():
        log_console_error_message(container, LEGACY_RENDER_DEPRECATION)


def run_effects_phased(effects: list[Callable[[], None]], *, container: Any) -> None:
    destroys = [e for e in effects if getattr(e, "_ryact_effect_phase", None) == "destroy"]
    creates = [e for e in effects if getattr(e, "_ryact_effect_phase", None) != "destroy"]
    for fn in destroys + creates:
        try:
            fn()
        except BaseException as err:
            from .root import _dom_catch_effect_error

            if _dom_catch_effect_error(container, fn, err):
                return
            boundary_names = getattr(fn, "_ryact_dom_boundary_names", None)
            if isinstance(boundary_names, list) and boundary_names:
                log_boundary_component_error(
                    container,
                    err,
                    boundary_name=str(boundary_names[-1]),
                )
            elif _is_legacy_container(container):
                report_uncaught_legacy_error(container, err)
                raise
            else:
                report_uncaught_error(container, err)
            return
