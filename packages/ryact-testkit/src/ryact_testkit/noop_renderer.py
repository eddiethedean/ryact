from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, cast

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

    def render(self, element: Element | None, *, lane: Lane = DEFAULT_LANE) -> None:
        def commit(payload: Any) -> None:
            prev_tree = getattr(self._reconciler_root, "current", None)
            work = render_to_noop_work(self._reconciler_root, payload)
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
                run()
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
                if not isinstance(slot, tuple) or len(slot) != 2:
                    continue
                cleanup, _deps = slot
                if callable(cleanup):
                    cleanup()
                hooks[i] = (None, None)
            sib = getattr(fib, "sibling", None)
            if sib is not None:
                stack.append(sib)
            child = getattr(fib, "child", None)
            if child is not None:
                stack.append(child)


def _run_unmount_callbacks(prev_tree: Any, next_tree: Any) -> None:
    prev = {_fiber_identity(f): f for f in _iter_fibers(prev_tree)}
    nxt = {_fiber_identity(f): f for f in _iter_fibers(next_tree)}
    removed = [prev[k] for k in prev.keys() - nxt.keys()]
    for f in removed:
        inst = getattr(f, "state_node", None)
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
