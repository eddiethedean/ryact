from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, cast

from ryact.dev import is_dev
from ryact.devtools import component_stack_from_fiber
from ryact.element import Element
from ryact.hooks import _TransitionHook
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    create_root,
    perform_work,
    render_to_noop_work,
    schedule_update_on_root,
)
from schedulyr import Scheduler

from .interop import InteropRunner
from ryact.act import is_act_environment_enabled, is_in_act_scope
from .warnings import emit_warning


@dataclass
class NoopContainer:
    """
    Deterministic in-memory host target for reconciler-focused tests.

    The reconciler commits a *payload* into this container via the root's commit callback.
    Tests can assert on:

    - `commits` / `last_committed` (snapshots)
    - `ops` (deterministic host mutation log: insert/move/delete/updateProps/text)
    """

    commits: list[Any] = field(default_factory=list)
    last_committed: Any | None = None
    ops: list[dict[str, Any]] = field(default_factory=list)
    host_root: Any | None = None
    interop_runner: InteropRunner | None = None
    # Test hook for error reporting; called when an error is captured by a boundary.
    captured_error_reporter: Callable[[BaseException], None] | None = None
    # Test hook for error reporting; called when an error escapes the root.
    uncaught_error_reporter: Callable[[BaseException], None] | None = None


@dataclass
class NoopRoot:
    container: NoopContainer
    _reconciler_root: Any

    def get_ops(self) -> list[dict[str, Any]]:
        """Return the current deterministic host-op log."""
        return list(self.container.ops)

    def clear_ops(self) -> None:
        """Clear the deterministic host-op log."""
        self.container.ops.clear()

    def get_children_snapshot(self) -> Any:
        """Return the last committed snapshot payload (for quick sanity checks)."""
        return self.container.last_committed

    def find_instance(self, inst: object) -> Any | None:
        """
        Noop equivalent of ReactNoop.findInstance():
        returns the nearest committed host instance for a component instance,
        or None if the instance is not mounted/committed.
        """
        root_fiber = getattr(self._reconciler_root, "current", None)
        host_root = self.container.host_root
        if root_fiber is None or host_root is None:
            return None

        target: Any | None = None
        for f in _iter_fibers(root_fiber):
            if getattr(f, "state_node", None) is inst:
                target = f
                break
        if target is None:
            return None

        host_fiber = _find_first_host_fiber(target)
        if host_fiber is None:
            return None
        return _find_host_node_for_fiber(root_fiber, cast(dict[str, Any], host_root), host_fiber)

    def render(
        self,
        element: Element | None,
        *,
        lane: Lane = DEFAULT_LANE,
        callback: Callable[[], None] | None = None,
    ) -> None:
        if is_act_environment_enabled() and not is_in_act_scope():
            emit_warning(
                "An update to the root was not wrapped in act(...).",
                category=RuntimeWarning,
                stacklevel=3,
            )
        reporting = False

        def _default_report(err: BaseException) -> None:
            if not is_dev():
                return
            # React suppresses the generic "add an error boundary" warning when inside
            # a real act() scope.
            if is_in_act_scope():
                return
            emit_warning(
                (
                    "An error occurred in the component.\n\n"
                    "Consider adding an error boundary to your tree to customize error handling "
                    "behavior."
                ),
                category=RuntimeWarning,
                stacklevel=4,
            )

        def _report_uncaught(err: BaseException) -> None:
            nonlocal reporting
            if reporting:
                return
            reporting = True
            try:
                reporter = getattr(self.container, "uncaught_error_reporter", None)
                if callable(reporter):
                    reporter(err)
                else:
                    _default_report(err)
            finally:
                reporting = False

        def commit(payload: Any) -> None:
            prev_tree = getattr(self._reconciler_root, "current", None)
            # Root-level retry: if rendering throws and then succeeds on retry,
            # treat it as a recoverable error and commit the retried work.
            try:
                work = render_to_noop_work(self._reconciler_root, payload)
            except BaseException as err:
                if bool(getattr(err, "_ryact_no_root_retry", False)):
                    raise
                try:
                    work = render_to_noop_work(self._reconciler_root, payload)
                except BaseException as err2:
                    _report_uncaught(err2)
                    raise
                else:
                    if is_dev():
                        emit_warning(
                            "There was an error during rendering but Ryact recovered by "
                            "synchronously retrying the entire root.",
                            category=RuntimeWarning,
                            stacklevel=4,
                        )
            # Commit phase:
            # - update host instance tree + ops log (for reconciliation assertions)
            # - publish snapshot
            # - run effects deterministically
            if self.container.host_root is None:
                self.container.host_root = {"type": "__root__", "children": []}
            _apply_snapshot_to_host(
                cast(dict[str, Any], self.container.host_root),
                {"children": [work.snapshot]} if work.snapshot is not None else {"children": []},
                self.container.ops,
                path=[],
            )
            self.container.last_committed = work.snapshot
            self.container.commits.append(work.snapshot)
            # Offscreen/Activity: disconnect effects when a subtree becomes hidden.
            _disconnect_hidden_offscreen(prev_tree, work.finished_work)

            # Snapshot committed instance state *before* running commit callbacks so that
            # unmount after a failed update can restore last-committed state.
            if work.finished_work is not None:
                for f in _iter_fibers(work.finished_work):
                    inst = getattr(f, "state_node", None)
                    if inst is None:
                        continue
                    st = getattr(inst, "_state", None)
                    if isinstance(st, dict):
                        f._committed_state_snapshot = dict(st)  # type: ignore[attr-defined]

            for run in work.insertion_effects:
                run()
            for run in work.layout_effects:
                run()
            for run in work.passive_effects:
                run()
            # DEV StrictMode: replay newly mounted/reappearing effects once.
            for run in getattr(work, "strict_layout_effects", []):
                run()
            for run in getattr(work, "strict_passive_effects", []):
                run()
            for run in work.commit_callbacks:
                try:
                    run()
                except BaseException as err:
                    _report_uncaught(err)
                    raise
            if callback is not None:
                try:
                    callback()
                except BaseException as err:
                    _report_uncaught(err)
                    raise
            # Install finished fiber tree for next render.
            if work.finished_work is not None:
                self._reconciler_root.current = work.finished_work
                _detach_all_refs(prev_tree)
                _attach_all_refs(work.finished_work, self.container.host_root)
                _run_unmount_callbacks(prev_tree, work.finished_work)
                # Commit-ish: clear transition pending flags after commit.
                cleared = False
                stack: list[Any] = [work.finished_work]
                while stack:
                    f = stack.pop()
                    for h in getattr(f, "hooks", []):
                        if isinstance(h, _TransitionHook):
                            if h.pending:
                                cleared = True
                            h.pending = False
                    sib = getattr(f, "sibling", None)
                    if sib is not None:
                        stack.append(sib)
                    child = getattr(f, "child", None)
                    if child is not None:
                        stack.append(child)
                if cleared:
                    schedule_update_on_root(rr, Update(lane=DEFAULT_LANE, payload=rr._last_element))

        rr = self._reconciler_root
        bind_commit(rr, commit)
        schedule_update_on_root(rr, Update(lane=lane, payload=element))
        if rr.scheduler is None:
            # Sync roots normally flush immediately; however, batched_updates() should
            # allow multiple updates to accumulate until an explicit flush.
            if bool(getattr(rr, "_is_batching_updates", False)):
                return
            try:
                perform_work(rr, commit)
            except BaseException as err:
                # Best-effort reporting for errors that escape commit.
                if bool(getattr(err, "_ryact_no_root_retry", False)):
                    raise
                _report_uncaught(err)
                raise

    def batched_updates(self, fn: Callable[[], None]) -> None:
        rr = self._reconciler_root
        prev = getattr(rr, "_is_batching_updates", False)
        rr._is_batching_updates = True  # type: ignore[attr-defined]
        try:
            fn()
        finally:
            rr._is_batching_updates = prev  # type: ignore[attr-defined]

    def flush_sync(self, fn: Callable[[], None]) -> None:
        rr = self._reconciler_root
        prev = getattr(rr, "_force_sync_updates", False)
        rr._force_sync_updates = True  # type: ignore[attr-defined]
        try:
            fn()
        finally:
            rr._force_sync_updates = prev  # type: ignore[attr-defined]
        # Flush immediately, even for scheduler-backed roots.
        commit = getattr(rr, "_commit_fn", None)
        if callable(commit):
            perform_work(rr, commit)

    def flush(self) -> None:
        rr = self._reconciler_root
        fn = rr._commit_fn
        if fn is not None:
            perform_work(rr, fn)


def create_noop_root(
    *,
    scheduler: Optional[Scheduler] = None,
    interop_runner: InteropRunner | None = None,
) -> NoopRoot:
    container = NoopContainer()
    container.interop_runner = interop_runner
    rr = create_root(container, scheduler=scheduler)
    return NoopRoot(container=container, _reconciler_root=rr)


def _iter_fibers(root: Any) -> list[Any]:
    if root is None:
        return []
    out: list[Any] = []
    stack: list[Any] = [root]
    while stack:
        f = stack.pop()
        out.append(f)
        sib = getattr(f, "sibling", None)
        if sib is not None:
            stack.append(sib)
        child = getattr(f, "child", None)
        if child is not None:
            stack.append(child)
    return out


def _find_first_host_fiber(f: Any) -> Any | None:
    stack: list[Any] = []
    c = getattr(f, "child", None)
    if c is not None:
        stack.append(c)
    while stack:
        x = stack.pop()
        t = getattr(x, "type", None)
        if isinstance(t, str) and t not in (
            "__root__",
            "__fragment__",
            "__strict_mode__",
            "__suspense__",
            "__offscreen__",
        ):
            return x
        sib = getattr(x, "sibling", None)
        if sib is not None:
            stack.append(sib)
        child = getattr(x, "child", None)
        if child is not None:
            stack.append(child)
    return None


def _find_host_node_for_fiber(
    root_fiber: Any, host_root: dict[str, Any], target: Any
) -> Any | None:
    from ryact.wrappers import ForwardRefType, MemoType

    def host_children(host: Any) -> list[Any]:
        if isinstance(host, dict):
            return list(host.get("children", []))
        return []

    def walk(fiber: Any, host: Any) -> Any | None:
        if fiber is None:
            return None
        if fiber is target:
            return host
        f_type = getattr(fiber, "type", None)
        is_transparent_wrapper = isinstance(f_type, (MemoType, ForwardRefType))

        if isinstance(f_type, str) and f_type not in (
            "__root__",
            "__fragment__",
            "__strict_mode__",
            "__suspense__",
        ):
            # Host fiber: `host` corresponds to this fiber's instance.
            kids = host_children(host)
            i = 0
            c = getattr(fiber, "child", None)
            while c is not None:
                next_host = kids[i] if i < len(kids) else None
                res = walk(c, next_host)
                if res is not None:
                    return res
                c = getattr(c, "sibling", None)
                i += 1
            return None

        # Composite components: their child tree represents the rendered output rooted at `host`.
        if not isinstance(f_type, str):
            c = getattr(fiber, "child", None)
            while c is not None:
                res = walk(c, host)
                if res is not None:
                    return res
                c = getattr(c, "sibling", None)
            return None

        # Wrappers + composite components: map their children into host children by index,
        # except for transparent wrappers (memo/forwardRef) which reuse the same host node.
        f_children: list[Any] = []
        c = getattr(fiber, "child", None)
        while c is not None:
            f_children.append(c)
            c = getattr(c, "sibling", None)
        if is_transparent_wrapper:
            for f_child in f_children:
                res = walk(f_child, host)
                if res is not None:
                    return res
            return None

        kids = host_children(host)
        for i, f_child in enumerate(f_children):
            next_host = kids[i] if i < len(kids) else None
            res = walk(f_child, next_host)
            if res is not None:
                return res
        return None

    return walk(root_fiber, host_root)


def _fiber_identity(f: Any) -> tuple[Any, Any]:
    return (getattr(f, "type", None), getattr(f, "key", None))


def _offscreen_mode(f: Any) -> str | None:
    props = getattr(f, "memoized_props", None) or getattr(f, "pending_props", None) or {}
    if isinstance(props, dict):
        m = props.get("mode")
        if isinstance(m, str):
            return m
    return None


def _disconnect_hidden_offscreen(prev_tree: Any, next_tree: Any) -> None:
    """
    Minimal Offscreen/Activity effect disconnection:
    if an Offscreen fiber transitions visible -> hidden, run effect cleanups in its subtree
    and reset effect deps so they remount on reveal.
    """
    if prev_tree is None or next_tree is None:
        return
    prev_by_id = {_fiber_identity(f): f for f in _iter_fibers(prev_tree)}
    for f2 in _iter_fibers(next_tree):
        if getattr(f2, "type", None) != "__offscreen__":
            continue
        if _offscreen_mode(f2) != "hidden":
            continue
        prev = prev_by_id.get(_fiber_identity(f2))
        if prev is None:
            continue
        if _offscreen_mode(prev) == "hidden":
            continue

        # Traverse the *previous* visible subtree and run cleanups.
        stack: list[Any] = []
        c = getattr(prev, "child", None)
        if c is not None:
            stack.append(c)
        while stack:
            fib = stack.pop()
            hooks = getattr(fib, "hooks", None) or []
            for i, slot in enumerate(list(hooks)):
                if not isinstance(slot, tuple) or len(slot) not in (2, 3):
                    continue
                cleanup, _deps = slot[0], slot[1]
                if callable(cleanup):
                    cleanup()
                kind = slot[2] if len(slot) == 3 else None
                hooks[i] = (None, None, kind) if kind is not None else (None, None)
            sib = getattr(fib, "sibling", None)
            if sib is not None:
                stack.append(sib)
            child = getattr(fib, "child", None)
            if child is not None:
                stack.append(child)


def _fiber_depth_up(f: Any) -> int:
    d = 0
    x = f
    while getattr(x, "parent", None) is not None:
        d += 1
        x = x.parent
    return d


def _run_unmount_callbacks(prev_tree: Any, next_tree: Any) -> None:
    prev = {_fiber_identity(f): f for f in _iter_fibers(prev_tree)}
    nxt = {_fiber_identity(f): f for f in _iter_fibers(next_tree)}
    removed = [prev[k] for k in prev.keys() - nxt.keys()]
    # Shallow ancestors before deeper descendants (matches upstream unmount ordering in slices).
    removed.sort(key=_fiber_depth_up)

    def _run_hook_cleanups(kind: str) -> None:
        for f in removed:
            hooks = getattr(f, "hooks", None) or []
            for i, slot in enumerate(list(hooks)):
                if not isinstance(slot, tuple) or len(slot) not in (2, 3):
                    continue
                cleanup, deps = slot[0], slot[1]
                slot_kind = slot[2] if len(slot) == 3 else None
                if slot_kind != kind:
                    continue
                if callable(cleanup):
                    cleanup()
                hooks[i] = (None, deps, kind)

    # Match React ordering: layout destroy effects run before passive destroy effects.
    _run_hook_cleanups("layout")
    _run_hook_cleanups("passive")

    for f in removed:
        inst = getattr(f, "state_node", None)
        snap = getattr(f, "_committed_state_snapshot", None)
        if inst is not None and isinstance(snap, dict) and hasattr(inst, "_state"):
            inst._state = dict(snap)  # type: ignore[attr-defined]
        cb = getattr(inst, "componentWillUnmount", None)
        if callable(cb):
            cb()


def _detach_all_refs(tree: Any) -> None:
    for f in _iter_fibers(tree):
        if getattr(f, "type", None) is None or not isinstance(getattr(f, "type", None), str):
            continue
        props = getattr(f, "pending_props", None) or getattr(f, "memoized_props", None) or {}
        ref = props.get("__ref__") if isinstance(props, dict) else None
        if ref is None:
            continue
        try:
            if callable(ref):
                ref(None)
            elif hasattr(ref, "current"):
                ref.current = None
        except Exception:
            # Upstream: detaching a ref must not abort the rest of unmount teardown.
            pass


def _attach_all_refs(tree: Any, host_root: Any) -> None:
    if host_root is None:
        return
    from ryact.wrappers import ForwardRefType, MemoType

    def walk(fiber: Any, host: Any) -> None:
        if fiber is None or host is None:
            return
        f_type = getattr(fiber, "type", None)
        is_transparent_wrapper = isinstance(f_type, (MemoType, ForwardRefType))
        if f_type in ("__root__", "__fragment__", "__strict_mode__", "__suspense__") or isinstance(
            f_type, (MemoType, ForwardRefType)
        ):
            # Wrapper fibers do not correspond to host instances.
            pass
        elif isinstance(f_type, str) and isinstance(host, dict) and host.get("type") != "#text":
            props = (
                getattr(fiber, "pending_props", None)
                or getattr(fiber, "memoized_props", None)
                or {}
            )
            ref = props.get("__ref__") if isinstance(props, dict) else None
            if ref is not None:
                if callable(ref):
                    ref(host)
                elif hasattr(ref, "current"):
                    ref.current = host
                else:
                    stack = component_stack_from_fiber(fiber)
                    msg = (
                        "Invalid ref object provided; expected a callable ref or an object "
                        "with `current`."
                    )
                    if stack:
                        msg = msg + "\n\n" + stack
                    emit_warning(msg, category=RuntimeWarning, stacklevel=3)
        # Recurse children in order.
        f_children: list[Any] = []
        c = getattr(fiber, "child", None)
        while c is not None:
            f_children.append(c)
            c = getattr(c, "sibling", None)
        if is_transparent_wrapper:
            # Transparent wrappers (memo/forwardRef) map their child fibers to the same host node.
            for f_child in f_children:
                walk(f_child, host)
            return

        # Component fibers: a single host child reuses this host snapshot (host "children"
        # are that element's subtree slots, not the component's returned root).
        if (
            len(f_children) == 1
            and isinstance(host, dict)
            and host.get("type") not in (None, "#text")
            and isinstance(host.get("type"), str)
            and getattr(f_children[0], "type", None) == host.get("type")
        ):
            walk(f_children[0], host)
            return

        h_children = host.get("children", []) if isinstance(host, dict) else []
        hi = 0
        for f_child in f_children:
            # Wrapper fibers don't consume a host child slot.
            if getattr(f_child, "type", None) in (
                "__fragment__",
                "__strict_mode__",
                "__suspense__",
            ) or isinstance(getattr(f_child, "type", None), (MemoType, ForwardRefType)):
                walk(f_child, host)
                continue
            h_child = h_children[hi] if hi < len(h_children) else None
            hi += 1
            walk(f_child, h_child)

    # Root fiber corresponds to host_root itself (synthetic root).
    root_child = getattr(tree, "child", None)
    host_children = host_root.get("children", []) if isinstance(host_root, dict) else []
    if root_child is None:
        return
    # Root fiber's child is the committed element; host_root children[0] matches.
    walk(root_child, host_children[0] if host_children else None)


def _apply_snapshot_to_host(
    host_parent: dict[str, Any],
    snap: dict[str, Any] | None,
    ops: list[dict[str, Any]],
    *,
    path: list[int],
) -> None:
    """
    Apply a snapshot dict to an in-memory host tree and emit deterministic ops.

    This is a minimal key-first child reconciliation for the noop host.
    """
    new_children = [] if snap is None else list(snap.get("children", []))
    old_children = list(host_parent.get("children", []))

    def key_of(s: Any, i: int) -> str:
        if isinstance(s, dict) and s.get("key") is not None:
            return f"k:{s['key']}"
        return f"i:{i}"

    old_by_key = {key_of(c, i): (i, c) for i, c in enumerate(old_children)}
    next_children: list[Any] = []
    used_old: set[str] = set()

    for new_i, child_snap in enumerate(new_children):
        k = key_of(child_snap, new_i)
        if k in old_by_key and k not in used_old:
            old_i, inst = old_by_key[k]
            used_old.add(k)
            if old_i != new_i:
                ops.append({"op": "move", "from": path + [old_i], "to": path + [new_i]})
            # If the element type changed for the same key/index, replace the host instance.
            if (
                isinstance(inst, dict)
                and isinstance(child_snap, dict)
                and inst.get("type") != child_snap.get("type")
            ):
                new_inst = _instantiate(child_snap)
                ops.append(
                    {
                        "op": "replace",
                        "path": path + [new_i],
                        "type": new_inst.get("type") if isinstance(new_inst, dict) else None,
                        "key": new_inst.get("key") if isinstance(new_inst, dict) else None,
                    }
                )
                next_children.append(new_inst)
            else:
                _patch_instance(inst, child_snap, ops, path=path + [new_i])
                next_children.append(inst)
        else:
            inst = _instantiate(child_snap)
            ops.append(
                {
                    "op": "insert",
                    "path": path + [new_i],
                    "type": inst.get("type"),
                    "key": inst.get("key"),
                }
            )
            next_children.append(inst)

    for old_i, old_child in enumerate(old_children):
        k = key_of(old_child, old_i)
        if k not in used_old:
            ops.append({"op": "delete", "path": path + [old_i]})

    host_parent["children"] = next_children


def _instantiate(snap: Any) -> Any:
    if snap is None:
        return None
    if isinstance(snap, str):
        return {"type": "#text", "text": snap}
    if isinstance(snap, dict):
        return {
            "type": snap.get("type"),
            "key": snap.get("key"),
            "props": dict(snap.get("props", {})),
            "children": [_instantiate(c) for c in snap.get("children", [])],
        }
    return {"type": "#text", "text": str(snap)}


def _patch_instance(inst: Any, snap: Any, ops: list[dict[str, Any]], *, path: list[int]) -> None:
    if isinstance(inst, dict) and inst.get("type") == "#text":
        new_text = snap if isinstance(snap, str) else str(snap)
        if inst.get("text") != new_text:
            inst["text"] = new_text
            ops.append({"op": "text", "path": path, "value": new_text})
        return
    if not isinstance(inst, dict) or not isinstance(snap, dict):
        return
    # Update props
    new_props = dict(snap.get("props", {}))
    if inst.get("props") != new_props:
        inst["props"] = new_props
        ops.append({"op": "updateProps", "path": path, "props": new_props})
    # Reconcile children recursively
    _apply_snapshot_to_host(inst, snap, ops, path=path)
