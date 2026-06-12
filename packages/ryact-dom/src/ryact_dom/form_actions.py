from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any, cast

from ryact.concurrent import Thenable, start_transition
from ryact.dev import is_dev
from ryact.hooks import FormStatusSnapshot
from ryact.reconciler import TRANSITION_LANE, Update, perform_work, schedule_update_on_root

from .dom import Container, ElementNode, SyntheticEvent
from .form_data import RyactFormData, build_form_data, coerce_form_action_value

RYACT_ACTION_FN_KEY = "__ryact_action_fn__"
RYACT_FORM_ACTION_FN_KEY = "__ryact_form_action_fn__"

_REACT_MANAGED_FORMS: set[int] = set()
_PENDING_FORM_RESETS: list[tuple[Container, ElementNode]] = []


def reset_form_action_state() -> None:
    _REACT_MANAGED_FORMS.clear()
    _PENDING_FORM_RESETS.clear()


def attach_action_fns_to_props(props: dict[str, Any], *, tag: str) -> None:
    """Preserve callable ``action`` / ``formAction`` for host commit (stripped from DOM attrs)."""

    tl = tag.lower()
    if tl == "form":
        fn = coerce_form_action_value(props.get("action"))
        if callable(fn):
            props[RYACT_ACTION_FN_KEY] = fn
    if tl in ("button", "input"):
        raw = props.get("formAction")
        if raw is None:
            raw = props.get("formaction")
        fn = coerce_form_action_value(raw)
        if callable(fn):
            props[RYACT_FORM_ACTION_FN_KEY] = fn


def sync_form_host_flags(node: ElementNode) -> None:
    """Mark React-managed forms that block native submission."""

    tl = node.tag.lower()
    if tl == "form":
        fn = getattr(node, "_form_action_fn", None)
        has_fn_child = _descendant_has_function_form_action(node)
        managed = callable(fn) or has_fn_child
        node._native_blocks_submission = managed
        if managed:
            _REACT_MANAGED_FORMS.add(id(node))
        else:
            _REACT_MANAGED_FORMS.discard(id(node))
    if tl in ("button", "input"):
        fn = getattr(node, "_form_action_fn", None)
        if callable(fn):
            name = node.props.get("name")
            if name is not None and is_dev():
                warnings.warn(
                    'Cannot specify a "name" prop for a button that specifies a function as a '
                    "formAction. React needs it to encode which action should be invoked. "
                    "It will get overridden.\n"
                    "    in input",
                    UserWarning,
                    stacklevel=2,
                )


def _descendant_has_function_form_action(form: ElementNode) -> bool:
    for ch in form.children:
        if isinstance(ch, ElementNode):
            if callable(getattr(ch, "_form_action_fn", None)):
                return True
            if _descendant_has_function_form_action(ch):
                return True
    return False


def apply_action_fn_fields_from_props(node: ElementNode) -> None:
    fn = node.props.pop(RYACT_ACTION_FN_KEY, None)
    if callable(fn):
        node._form_action_fn = fn
    fa = node.props.pop(RYACT_FORM_ACTION_FN_KEY, None)
    if callable(fa):
        node._form_action_fn = fa
    sync_form_host_flags(node)


def find_owning_form(node: ElementNode) -> ElementNode | None:
    cur: ElementNode | None = node
    while cur is not None:
        if cur.tag.lower() == "form":
            return cur
        cur = cur.parent
    return None


def resolve_form_action(
    form: ElementNode, submitter: ElementNode | None
) -> Callable[[RyactFormData], Any] | str | None:
    if submitter is not None:
        sub_fn = getattr(submitter, "_form_action_fn", None)
        if callable(sub_fn):
            return cast(Callable[[RyactFormData], Any], sub_fn)
        raw = submitter.props.get("formAction") or submitter.props.get("formaction")
        coerced = coerce_form_action_value(raw)
        if isinstance(coerced, str):
            return coerced
    form_fn = getattr(form, "_form_action_fn", None)
    if callable(form_fn):
        return cast(Callable[[RyactFormData], Any], form_fn)
    raw_action = form.props.get("action")
    coerced = coerce_form_action_value(raw_action)
    if isinstance(coerced, str):
        return coerced
    return None


def _navigate_to(url: str) -> None:
    raise RuntimeError(f"Navigate to: {url}")


def _schedule_render(container: Container, *, lane: Any = TRANSITION_LANE) -> None:
    dom_root = container._ryact_dom_root
    if dom_root is None:
        return
    rr = dom_root._reconciler_root
    commit = getattr(rr, "_commit_fn", None)
    if commit is None:
        return
    payload = getattr(dom_root, "_last_rendered_element", None)
    schedule_update_on_root(rr, Update(lane=lane, payload=payload))
    if rr.scheduler is None:
        perform_work(rr, commit)


def _run_form_reset(form: ElementNode) -> None:
    form.reset()
    ev = SyntheticEvent(type="reset", target=form)
    form._current_dispatch_event = ev
    try:
        from .event_listener import dispatch_host_event

        dispatch_host_event(form, "reset")
    finally:
        form._current_dispatch_event = None


def flush_pending_form_resets() -> None:
    pending = list(_PENDING_FORM_RESETS)
    _PENDING_FORM_RESETS.clear()
    for _container, form in pending:
        _run_form_reset(form)


def request_form_reset(form: ElementNode) -> None:
    """Schedule a form reset after the current transition/action (React 19 subset)."""

    if form.tag.lower() != "form":
        raise ValueError("Invalid form element.")
    if id(form) not in _REACT_MANAGED_FORMS:
        raise ValueError("Invalid form element.")
    container = form._event_container
    if container is None:
        raise ValueError("Invalid form element.")
    from ryact.concurrent import is_in_transition

    if is_dev() and not is_in_transition():
        warnings.warn(
            "requestFormReset was called outside a transition or action. "
            "To fix, move to an action, or wrap with startTransition.",
            RuntimeWarning,
            stacklevel=2,
        )
        _run_form_reset(form)
        return
    _PENDING_FORM_RESETS.append((container, form))


def _after_action_complete(container: Container, form: ElementNode) -> None:
    container._form_status_snapshot = None
    flush_pending_form_resets()
    _schedule_render(container)


def invoke_form_action(
    form: ElementNode,
    *,
    submitter: ElementNode | None = None,
    container: Container | None = None,
) -> None:
    container = container or form._event_container
    if container is None:
        return
    resolved = resolve_form_action(form, submitter)
    if resolved is None:
        method = str(form.props.get("method", "get")).lower()
        url = str(form.props.get("action", "") or "")
        if url:
            _navigate_to(url if "://" in url else f"http://localhost/{url.lstrip('/')}")
        return
    if isinstance(resolved, str):
        _navigate_to(resolved)
        return

    fd = build_form_data(form, submitter=submitter)
    action_fn = resolved
    method = str(form.props.get("method", "get"))
    snap = FormStatusSnapshot(pending=True, data=fd, method=method, action=action_fn)
    container._form_status_snapshot = snap

    def run() -> None:
        try:
            result = action_fn(fd)
        except BaseException:
            container._form_status_snapshot = None
            _schedule_render(container)
            raise
        if isinstance(result, Thenable):

            def done() -> None:
                if result.status == "rejected":
                    container._form_status_snapshot = None
                    _schedule_render(container)
                    if result.error is not None:
                        raise result.error
                    return
                _after_action_complete(container, form)

            result.then(done)
        else:
            _after_action_complete(container, form)

    start_transition(run)
    _schedule_render(container)


def maybe_invoke_form_action_after_submit(event: SyntheticEvent) -> None:
    if event.type != "submit" or event.default_prevented:
        return
    target = event.target
    if target.tag.lower() != "form":
        return
    submitter = getattr(event, "submitter", None)
    invoke_form_action(target, submitter=submitter, container=target._event_container)


def handle_native_form_submit(form: ElementNode) -> None:
    """``requestSubmit`` / implicit submit: dispatch ``submit`` then maybe run the action."""

    event = SyntheticEvent(type="submit", target=form)
    event.submitter = None  # type: ignore[attr-defined]
    form._current_dispatch_event = event
    try:
        from .event_listener import dispatch_host_event

        def after() -> None:
            maybe_invoke_form_action_after_submit(event)

        dispatch_host_event(form, "submit", after_listeners=after)
    finally:
        form._current_dispatch_event = None


def handle_react_form_submit(form: ElementNode, submitter: ElementNode | None = None) -> None:
    event = SyntheticEvent(type="submit", target=form)
    event.submitter = submitter  # type: ignore[attr-defined]
    form._current_dispatch_event = event
    try:
        from .event_listener import dispatch_host_event

        def after() -> None:
            maybe_invoke_form_action_after_submit(event)

        dispatch_host_event(form, "submit", after_listeners=after)
    finally:
        form._current_dispatch_event = None


def trigger_submit_from_control(control: ElementNode) -> None:
    form = find_owning_form(control)
    if form is None:
        return
    handle_react_form_submit(form, submitter=control)


def unexpected_manual_submit_error() -> RuntimeError:
    return RuntimeError(
        "A React form was unexpectedly submitted. If you called form.submit() "
        "on a form, use form.requestSubmit() instead. If you're trying to use "
        'a button to submit the form, set type="submit" on the button.'
    )
