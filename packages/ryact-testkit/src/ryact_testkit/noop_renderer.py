from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, cast

from ryact.element import Element
from ryact.hooks import _TransitionHook
from ryact.reconciler import (
    DEFAULT_LANE,
    Lane,
    Update,
    bind_commit,
    create_root,
    perform_work,
    reconcile_key_first_indices,
    render_to_noop_work,
    schedule_update_on_root,
)
from schedulyr import Scheduler


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
            work = render_to_noop_work(self._reconciler_root, payload)
            # Commit phase:
            # - update host instance tree + ops log (for reconciliation assertions)
            # - publish snapshot
            # - run effects deterministically
            if self.container.host_root is None:
                self.container.host_root = {"type": "__root__", "children": []}
            _apply_snapshot_to_host(
                cast(dict[str, Any], self.container.host_root),
                cast(dict[str, Any] | None, work.snapshot),
                self.container.ops,
                path=[],
            )
            self.container.last_committed = work.snapshot
            self.container.commits.append(work.snapshot)
            for run in work.insertion_effects:
                run()
            for run in work.layout_effects:
                run()
            for run in work.passive_effects:
                run()
            # Install finished fiber tree for next render.
            if work.finished_work is not None:
                self._reconciler_root.current = work.finished_work
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


def create_noop_root(*, scheduler: Optional[Scheduler] = None) -> NoopRoot:
    container = NoopContainer()
    rr = create_root(container, scheduler=scheduler)
    return NoopRoot(container=container, _reconciler_root=rr)


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

    old_keys = [key_of(c, i) for i, c in enumerate(old_children)]
    new_keys = [key_of(c, i) for i, c in enumerate(new_children)]

    key_ops = reconcile_key_first_indices(old_keys, new_keys)
    next_children: list[Any] = []
    used_old: set[str] = set()

    for k_op in key_ops:
        if k_op["op"] == "move":
            old_i = cast(int, k_op["from"])
            new_i = cast(int, k_op["to"])
            inst = old_children[old_i]
            child_snap = new_children[new_i]
            used_old.add(old_keys[old_i])
            ops.append({"op": "move", "from": path + [old_i], "to": path + [new_i]})
            _patch_instance(inst, child_snap, ops, path=path + [new_i])
            next_children.append(inst)
        elif k_op["op"] == "insert":
            new_i = cast(int, k_op["to"])
            child_snap = new_children[new_i]
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
        elif k_op["op"] == "delete":
            old_i = cast(int, k_op["from"])
            used_old.add(old_keys[old_i])
            ops.append({"op": "delete", "path": path + [old_i]})

    # key_ops can interleave deletes; build final children list in order.
    # Any reused old nodes not already appended (due to stable index) are appended now.
    if len(next_children) != len(new_children):
        next_children = []
        old_by_key = {old_keys[i]: old_children[i] for i in range(len(old_children))}
        for new_i, child_snap in enumerate(new_children):
            k = new_keys[new_i]
            if k in old_by_key and k in used_old:
                inst = old_by_key[k]
                _patch_instance(inst, child_snap, ops, path=path + [new_i])
                next_children.append(inst)
            else:
                next_children.append(_instantiate(child_snap))

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
