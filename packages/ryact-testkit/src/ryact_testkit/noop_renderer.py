from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, cast

from ryact.act import is_act_environment_enabled, is_in_act_scope
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

    def set_yield_after_nodes(self, n: int | None) -> None:
        """
        Configure an internal yield budget for the next flushes.

        This is a coarse test harness knob (not a public ryact runtime API) used to model
        partial rendering where the reconciler pauses work and resumes on subsequent flushes.
        """
        rr = self._reconciler_root
        if n is None:
            with_yield = 0
        else:
            with_yield = int(n)
            if with_yield < 0:
                raise ValueError("yield_after_nodes must be non-negative")
        rr._yield_after_nodes = with_yield  # type: ignore[attr-defined]

    def flush_scheduled(self, *, time_slice_ms: int | None = None, max_tasks: int | None = None) -> None:
        """
        Run scheduled work for scheduler-backed roots.

        For roots created with ``create_noop_root(scheduler=...)``, updates are coalesced into
        a scheduled flush task. This helper runs the underlying scheduler until idle.
        """
        rr = self._reconciler_root
        sched = getattr(rr, "scheduler", None)
        if sched is None:
            return
        sched.run_until_idle(time_slice_ms=time_slice_ms, max_tasks=max_tasks)

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
                if bool(getattr(err, "_ryact_boundary_rethrow", False)):
                    _report_uncaught(err)
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
            # Host context hooks (minimal internal test surface).
            get_ctx = getattr(self.container, "get_root_host_context", None)
            host_ctx = get_ctx() if callable(get_ctx) else None
            prep = getattr(self.container, "prepareForCommit", None)
            if callable(prep):
                prep(host_ctx)
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
            # After host snapshot, run unmounts/effects, but always point root.current at the
            # new finished tree even if a lifecycle throws (e.g. componentWillUnmount) so
            # the next commit does not re-unmount the same subtrees. Re-raise after.
            _commit_phase_err: BaseException | None = None
            try:
                def _run_effects_phased(effects: list[Callable[[], None]]) -> None:
                    destroys = [
                        e for e in effects if getattr(e, "_ryact_effect_phase", None) == "destroy"
                    ]
                    creates = [
                        e for e in effects if getattr(e, "_ryact_effect_phase", None) != "destroy"
                    ]
                    first_err: BaseException | None = None
                    for fn in destroys:
                        try:
                            fn()
                        except BaseException as err:
                            if first_err is None:
                                first_err = err
                    if first_err is not None:
                        raise first_err
                    for fn in creates:
                        fn()

                def _run_strict_effects_cross_sibling(
                    layout_effs: list[Callable[[], None]],
                    passive_effs: list[Callable[[], None]],
                ) -> None:
                    # When class components participate in strict replay, React runs all layout
                    # teardowns (incl. componentWillUnmount + hook layout cleanups), then all
                    # passive teardowns, then layout remounts, then passive remounts.
                    destr_l = [
                        e
                        for e in layout_effs
                        if getattr(e, "_ryact_effect_phase", None) == "destroy"
                    ]
                    creat_l = [
                        e
                        for e in layout_effs
                        if getattr(e, "_ryact_effect_phase", None) != "destroy"
                    ]
                    destr_p = [
                        e
                        for e in passive_effs
                        if getattr(e, "_ryact_effect_phase", None) == "destroy"
                    ]
                    creat_p = [
                        e
                        for e in passive_effs
                        if getattr(e, "_ryact_effect_phase", None) != "destroy"
                    ]
                    for fn in destr_l:
                        fn()
                    for fn in destr_p:
                        fn()
                    for fn in creat_l:
                        fn()
                    for fn in creat_p:
                        fn()

                # Offscreen/Activity: disconnect effects when a subtree becomes hidden.
                _disconnect_hidden_offscreen(prev_tree, work.finished_work)
                # Deletions must run destroy cleanups before create effects in the same commit.
                _run_unmount_callbacks(prev_tree, work.finished_work)

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

                _run_effects_phased(work.insertion_effects)
                _run_effects_phased(work.layout_effects)
                _run_effects_phased(work.passive_effects)
                for run in work.commit_callbacks:
                    try:
                        run()
                    except BaseException as err:
                        _report_uncaught(err)
                        raise
                # DEV StrictMode: replay newly mounted/reappearing effects once.
                # Run after commit callbacks so initial mount lifecycles (e.g. componentDidMount)
                # occur before the strict replay unmount/mount cycle.
                strict_layout = getattr(work, "strict_layout_effects", [])
                strict_passive = getattr(work, "strict_passive_effects", [])
                if any(getattr(e, "_ryact_strict_class_unmount", False) for e in strict_layout):
                    _run_strict_effects_cross_sibling(strict_layout, strict_passive)
                else:
                    _run_effects_phased(strict_layout)
                    _run_effects_phased(strict_passive)
                if callback is not None:
                    try:
                        callback()
                    except BaseException as err:
                        _report_uncaught(err)
                        raise
            except BaseException as e:
                _commit_phase_err = e
            finally:
                if work.finished_work is not None:
                    self._reconciler_root.current = work.finished_work
                    _detach_all_refs(prev_tree)
                    _attach_all_refs(work.finished_work, self.container.host_root)
            if _commit_phase_err is not None:
                raise _commit_phase_err
            reset = getattr(self.container, "resetAfterCommit", None)
            if callable(reset):
                reset(host_ctx)
            # Commit-ish: clear transition pending after commit, even if the host container
            # does not implement resetAfterCommit (NoopContainer).
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
        # Upstream flushSync should not flush previously batched work (sync roots).
        # For scheduler-backed roots, the test harness expects the last committed
        # payload to win, so we avoid reordering/dropping behavior here.
        stashed: list[Any] = []
        if getattr(rr, "scheduler", None) is None:
            stashed = list(getattr(rr, "pending_updates", []))
            try:
                getattr(rr, "pending_updates", []).clear()
            except Exception:
                stashed = []
        try:
            fn()
        finally:
            rr._force_sync_updates = prev  # type: ignore[attr-defined]
        # Flush immediately, even for scheduler-backed roots.
        commit = getattr(rr, "_commit_fn", None)
        if callable(commit):
            perform_work(rr, commit)
        # Restore stashed batched work (preserve insertion order).
        if stashed and getattr(rr, "scheduler", None) is None:
            try:
                getattr(rr, "pending_updates", []).extend(stashed)
            except Exception:
                pass

    def flush(self) -> None:
        rr = self._reconciler_root
        fn = rr._commit_fn
        if fn is not None:
            perform_work(rr, fn)

    def flush_steps(self, steps: int) -> None:
        """Call ``flush()`` repeatedly (useful with yielding roots)."""
        if steps < 0:
            raise ValueError("steps must be non-negative")
        for _ in range(steps):
            self.flush()

    def wait_for(self, predicate: Callable[[], bool], *, max_flushes: int = 50) -> None:
        """
        Flush repeatedly until ``predicate()`` returns True.

        This is a small deterministic analog of upstream test harness ``waitFor`` helpers.
        """
        if max_flushes < 0:
            raise ValueError("max_flushes must be non-negative")
        for _ in range(max_flushes + 1):
            if predicate():
                return
            self.flush()
        raise AssertionError("wait_for: predicate did not become true within max_flushes")


def create_noop_root(
    *,
    scheduler: Optional[Scheduler] = None,
    interop_runner: InteropRunner | None = None,
    yield_after_nodes: int | None = None,
    legacy: bool = False,
) -> NoopRoot:
    container = NoopContainer()
    container.interop_runner = interop_runner
    rr = create_root(container, scheduler=scheduler)
    rr._legacy_mode = bool(legacy)  # type: ignore[attr-defined]
    if yield_after_nodes is not None:
        rr._yield_after_nodes = int(yield_after_nodes)  # type: ignore[attr-defined]
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
            "__context_provider__",
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
            "__context_provider__",
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


def _fiber_identity(f: Any) -> tuple[Any, Any, Any]:
    # Prefer an explicit identity path when available (stable across reorders).
    ident = getattr(f, "_identity_path", None)
    if ident is not None:
        return ("_idpath_", ident, None)
    return (getattr(f, "type", None), getattr(f, "key", None), getattr(f, "index", None))


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
    if prev_tree is None:
        return
    nxt = _iter_fibers(next_tree) if next_tree is not None else []
    # Old `removed` = prev_keys - nxt_keys by _fiber_identity() is unsafe: the same
    # logical slot can re-use _identity_path "0" for a replaced class → host (or two
    # "div" hosts at index 0), so dict keys collide and the deleted class never appears
    # in `removed` (e.g. componentWillUnmount on the replaced component is skipped).
    # Match reconciliation: a prior fiber is kept iff some next-tree fiber has
    # `alternate` pointing to it.
    reused_old: set[int] = set()
    for f in nxt:
        alt = getattr(f, "alternate", None)
        if alt is not None:
            reused_old.add(id(alt))
    removed = [f for f in _iter_fibers(prev_tree) if id(f) not in reused_old]
    # Ancestors before descendants (shallow to deep): useLayoutEffect/useEffect destroy
    # and componentWillUnmount ordering matches ReactEffectOrdering and incremental
    # error unmount tests.
    removed.sort(key=lambda f: (_fiber_depth_up(f), str(getattr(f, "_identity_path", ""))))

    def _run_hook_cleanups_on_fiber(f: Any, kind: str) -> None:
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

    # Per fiber (parent before child): componentWillUnmount, then that fiber's layout
    # cleanups; then a second pass runs passive cleanups (still parent before child).
    for f in removed:
        inst = getattr(f, "state_node", None)
        snap = getattr(f, "_committed_state_snapshot", None)
        if inst is not None and isinstance(snap, dict) and hasattr(inst, "_state"):
            inst._state = dict(snap)  # type: ignore[attr-defined]
        cb = getattr(inst, "componentWillUnmount", None)
        if callable(cb):
            cb()
        _run_hook_cleanups_on_fiber(f, "layout")

    for f in removed:
        _run_hook_cleanups_on_fiber(f, "passive")


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
        if f_type in (
            "__root__",
            "__fragment__",
            "__strict_mode__",
            "__suspense__",
            "__context_provider__",
        ) or isinstance(
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
                elif isinstance(ref, str):
                    # Upstream: string refs are legacy and should warn with a codemod hint.
                    stack = component_stack_from_fiber(fiber)
                    msg = (
                        "Function components cannot have string refs. "
                        "We recommend using useRef() instead. "
                        "Learn more about using refs safely here: "
                        "https://react.dev/link/strict-mode-string-ref"
                    )
                    if stack:
                        msg = msg + "\n\n" + stack
                    emit_warning(msg, category=RuntimeWarning, stacklevel=3)
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
                "__context_provider__",
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
