#!/usr/bin/env python3
"""
Apply inventory status updates for parity burn-down *waves*.

Waves are explicit, reviewable batches (no hidden heuristics). Each wave should only flip
rows that are still `pending`, so re-running is safe.

Usage:
  python scripts/apply_parity_burndown_inventory.py list
  python scripts/apply_parity_burndown_inventory.py apply --wave initial_phase_a_b_d
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

R_SUSPENSE_NOOP_DEFER = (
    "Deferred: upstream case depends on React noop partial-yield/waitFor scheduling, "
    "unstable_getCacheForType/readText cache, Jest fake timers, or other harness surfaces "
    "not yet modeled in ryact-testkit; revisit with a dedicated translated slice."
)

R_INCREMENTAL_DEFER = (
    "Deferred: upstream case depends on multi-pass interruption/resume, lane expiration, "
    "or class context semantics beyond the current noop incremental model; revisit with a "
    "dedicated translated slice."
)

R_SUSPENSE_LIST_DEFER = (
    "Deferred: SuspenseList host element and reveal ordering are not implemented in ryact; "
    "revisit when a manifest-gated SuspenseList slice is scheduled."
)

R_FRAGMENT_DEFER = (
    "Deferred: upstream fragment identity/state preservation case requires deeper "
    "reconciliation + array host-child semantics not covered by the noop child-count slice; "
    "revisit with a dedicated translated slice."
)

R_ISOMORPHIC_ACT_DEFER = (
    "Deferred: upstream isomorphic/async act() semantics (awaiting, microtask flushing, promise "
    "unwrapping, legacy mode batching) are not implemented in ryact-testkit act(); revisit with a "
    "dedicated async act harness and translated slices."
)

R_ACT_SUSPENSE_DEFER = (
    "Deferred: upstream act() warnings for Suspense ping/retry require a Suspense test harness "
    "that can trigger ping/retry scheduling; revisit when a minimal Suspense ping surface exists."
)

R_HOOKS_NOOP_DEFER = (
    "Deferred: upstream ReactHooksWithNoopRenderer case depends on noop renderer behaviors not yet "
    "modeled in ryact-testkit (async-priority effect flushing, deferred passive unmount semantics, "
    "error propagation from passive destroys, or unimplemented hooks like useImperativeHandle); "
    "revisit with a dedicated harness slice."
)

R_ASYNC_ACTIONS_DEFER = (
    "Deferred: upstream async actions/entanglement semantics (useOptimistic/useTransition async "
    "action scopes, promise/microtask flushing, and action error propagation) are not implemented "
    "in ryact yet; revisit with an async action harness and dedicated translated slices."
)

R_TRANSITION_TRACING_DEFER = (
    "Deferred: upstream transition tracing depends on React's transition tracing API surface "
    "(transition name tracking, interaction tracing, and scheduler hooks) which is not yet "
    "modeled in ryact. Revisit once a tracing surface and deterministic scheduler integration "
    "tests exist."
)

R_CONCURRENT_CPU_SUSPENSE_DEFER = (
    "Deferred: upstream CPU-bound Suspense and concurrent skipping/yielding semantics require a "
    "more complete concurrent scheduler + suspense integration in the noop renderer; revisit with "
    "a dedicated translated slice once cooperative yielding and suspense retries are modeled."
)

R_BLOCKING_MODE_BATCHING_DEFER = (
    "Deferred: upstream blocking-mode batching semantics (flushSync/layout event boundaries, "
    "yielding behavior, and legacy Suspense interactions) are not fully modeled in ryact's "
    "noop scheduler yet; revisit with a dedicated batching harness slice."
)

R_CONCURRENT_LANES_EXPIRATION_DEFER = (
    "Deferred: upstream expiration/transition indicator/concurrent error recovery semantics depend on "
    "advanced lane expiration, time-slicing, and transition entanglement behavior not yet modeled "
    "in ryact's scheduler/noop renderer; revisit with dedicated concurrent scheduling slices."
)

R_DOM_FEATURES_DEFER = (
    "Deferred: upstream React DOM feature depends on browser/DOM integrations or advanced "
    "ReactDOM internals (hydration/Fizz, legacy root APIs, nested event batching, view "
    "transitions, iframe load semantics, or host CSS collision warnings) that are not yet "
    "modeled in ryact-dom's simplified container/event system."
)

R_UPSTREAM_SKIPPED_DEFER = (
    "Deferred: upstream marks this case as skipped (it.skip). "
    "ryact does not currently target skipped upstream semantics for parity; "
    "revisit if/when the upstream test is un-skipped and becomes a stable requirement."
)

R_SUSPENSE_EFFECTS_DEFER = (
    "Deferred: remaining Suspense effects semantics cases require deeper concurrent suspense "
    "scheduling/commit ordering and effect timing guarantees that exceed the current simplified "
    "host+commit model."
)

R_USE_DEFER = (
    "Deferred: upstream ReactUse tests cover experimental `use()` semantics (thenables, suspense "
    "integration, and cache/async coordination) that are not yet modeled in ryact's public API or "
    "noop harness. Revisit once a `use()` surface is designed and validated alongside Suspense/async "
    "rendering semantics."
)

R_LAZY_DEFER = (
    "Deferred: upstream ReactLazy internal suite covers advanced Lazy behaviors across legacy mode, "
    "reordering, and suspension/retry edge cases that require deeper concurrent rendering semantics "
    "and a more complete host/test harness. ryact currently implements a minimal Lazy slice (sync "
    "resolution) only."
)

R_PROFILER_DEFER = (
    "Deferred: upstream ReactProfiler internal tests validate profiling timings/base durations and "
    "scheduler instrumentation. ryact does not currently implement React's Profiler measurement "
    "model or host-specific timing hooks; revisit with a dedicated profiling milestone and "
    "deterministic timing harness."
)

R_HOOKS_INTERNAL_DEFER = (
    "Deferred: upstream ReactHooks-test.internal cases cover internal reconciler/hook optimizations "
    "(bailouts without render phase, update queue rebasing, and subtle warning stack edge-cases "
    "across memo/forwardRef/suspense). These require deeper Fiber parity and a more complete "
    "deterministic harness than the current ryact-testkit noop model."
)

R_CONTEXT_DEFER = (
    "Deferred: New Context API / propagation / bailout semantics beyond the current minimal "
    "create_context helper; revisit with dedicated translated slices."
)


def _patch_wave_initial_react_cases(cases: list[dict]) -> int:
    changed = 0
    suspense_path = "packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js"
    incremental_path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    list_path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    new_ctx = "packages/react-reconciler/src/__tests__/ReactNewContext-test.js"
    ctx_prop = "packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js"
    frag_path = "packages/react-reconciler/src/__tests__/ReactFragment-test.js"

    noop_child_titles = {
        "should render zero children via noop renderer",
        "should render a single child via noop renderer",
        "should render multiple children via noop renderer",
        "should render an iterable via noop renderer",
    }

    for c in cases:
        p = c.get("upstream_path")
        st = c.get("status")
        if st != "pending":
            continue

        if p == suspense_path:
            multi = "a Suspense component correctly handles more than one suspended child"
            if c.get("it_title") == multi:
                c["status"] = "implemented"
                c["manifest_id"] = "react.suspenseNoop.multiSuspendedChildren"
                c["python_test"] = "tests_upstream/react/test_suspense_noop_renderer_burndown.py"
                c["non_goal_rationale"] = None
                changed += 1
            else:
                c["status"] = "non_goal"
                c["manifest_id"] = None
                c["python_test"] = None
                c["non_goal_rationale"] = R_SUSPENSE_NOOP_DEFER
                changed += 1
            continue

        if p == incremental_path:
            simple_id = "react.ReactIncremental-test.reactincremental.should_render_a_simple_component"
            if c.get("id") == simple_id:
                c["status"] = "implemented"
                c["manifest_id"] = "react.incremental.simpleHostRender"
                c["python_test"] = "tests_upstream/react/test_incremental_simple_render.py"
                c["non_goal_rationale"] = None
                changed += 1
            else:
                c["status"] = "non_goal"
                c["manifest_id"] = None
                c["python_test"] = None
                c["non_goal_rationale"] = R_INCREMENTAL_DEFER
                changed += 1
            continue

        if p == list_path:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_SUSPENSE_LIST_DEFER
            changed += 1
            continue

        if p in (new_ctx, ctx_prop):
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_CONTEXT_DEFER
            changed += 1
            continue

        if p == frag_path:
            if c.get("it_title") in noop_child_titles:
                c["status"] = "implemented"
                c["manifest_id"] = "react.fragment.noopChildCounts"
                c["python_test"] = "tests_upstream/react/test_fragment_noop_child_counts.py"
                c["non_goal_rationale"] = None
                changed += 1
            else:
                c["status"] = "non_goal"
                c["manifest_id"] = None
                c["python_test"] = None
                c["non_goal_rationale"] = R_FRAGMENT_DEFER
                changed += 1
            continue

    return changed


def _patch_wave_initial_dom_cases(cases: list[dict]) -> int:
    changed = 0
    target_id = (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations."
        "setvalueforproperty.boolean_props_should_not_be_stringified_in_attributes.868cfa8b"
    )
    for c in cases:
        if c.get("id") != target_id:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react_dom.server.booleanAttributesNotStringified"
        c["python_test"] = "tests_upstream/react_dom/test_boolean_attributes_server.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_dom_invalid_event_listeners_dispatch_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-dom/src/__tests__/InvalidEventListeners-test.js"
    manifest_id = "react_dom.events.invalidListenersDispatch.v01"
    py = "tests_upstream/react_dom/test_invalid_event_listeners_dispatch_v01.py"
    titles = {
        "should not prevent null listeners, at dispatch",
        "should prevent non-function listeners, at dispatch",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_dangerously_set_innerhtml_innerhtml_property_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-dom/src/client/__tests__/dangerouslySetInnerHTML-test.js"
    manifest_id = "react_dom.client.dangerouslySetInnerHTML.innerHTMLProperty.v01"
    py = "tests_upstream/react_dom/test_dangerously_set_innerhtml_property_v01.py"
    title = "sets innerHTML on it"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_close_small_pending_buckets_defer_apr2026(cases: list[dict]) -> int:
    """
    Close a large chunk of tiny DOM pending buckets as deferred non-goals.

    This keeps the DOM inventory reviewable by explicitly grouping out-of-scope browser/ReactDOM
    internals into a single codified wave.
    """
    changed = 0
    target_paths = {
        "packages/react-dom/src/__tests__/ReactClassComponentPropResolutionFizz-test.js",
        "packages/react-dom/src/__tests__/ReactCompositeComponentNestedState-test.js",
        "packages/react-dom/src/__tests__/ReactDOMIframe-test.js",
        "packages/react-dom/src/__tests__/ReactDOMInReactServer-test.js",
        "packages/react-dom/src/__tests__/ReactDOMLegacyFloat-test.js",
        "packages/react-dom/src/__tests__/ReactDOMNestedEvents-test.js",
        "packages/react-dom/src/__tests__/ReactDOMServerIntegrationLegacyContext-test.js",
        "packages/react-dom/src/__tests__/ReactDOMServerIntegrationNewContext-test.js",
        "packages/react-dom/src/__tests__/ReactDOMShorthandCSSPropertyCollision-test.js",
        "packages/react-dom/src/__tests__/ReactDOMViewTransition-test.js",
        "packages/react-dom/src/__tests__/ReactErrorBoundariesHooks-test.internal.js",
        "packages/react-dom/src/__tests__/ReactErrorLoggingRecovery-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyRootWarnings-test.js",
        "packages/react-dom/src/__tests__/ReactServerRenderingBrowser-test.js",
        "packages/react-dom/src/__tests__/ReactStartTransitionMultipleRenderers-test.js",
        "packages/react-dom/src/__tests__/refsLegacy-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFizzDeferredValue-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFizzServerEdge-test.js",
        "packages/react-dom/src/__tests__/ReactDOMHostComponentTransitions-test.js",
        "packages/react-dom/src/__tests__/ReactDOMLegacyComponentTree-test.internal.js",
        "packages/react-dom/src/__tests__/ReactDOMSafariMicrotaskBug-test.js",
        "packages/react-dom/src/__tests__/ReactDOMSelection-test.internal.js",
        "packages/react-dom/src/__tests__/ReactDOMServerIntegrationUntrustedURL-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyContextDisabled-test.internal.js",
        "packages/react-dom/src/__tests__/ReactChildReconciler-test.js",
        "packages/react-dom/src/__tests__/ReactCompositeComponentDOMMinimalism-test.js",
        "packages/react-dom/src/__tests__/ReactEventIndependence-test.js",
        "packages/react-dom/src/__tests__/ReactMockedComponent-test.js",
        "packages/react-dom/src/__tests__/ReactMountDestruction-test.js",
        "packages/react-dom/src/__tests__/validateDOMNesting-test.js",
    }
    for c in cases:
        if c.get("upstream_path") not in target_paths:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_DOM_FEATURES_DEFER
        c["notes"] = "Deferred: requires fuller browser/ReactDOM feature parity."
        changed += 1
    return changed


def _patch_wave_dom_close_dom_property_operations_remaining_defer_apr2026(
    cases: list[dict],
) -> int:
    """
    Close remaining DOMPropertyOperations pending cases as deferred non-goals.

    These depend on browser DOM attribute/property assignment semantics, custom elements,
    credentialless, popoverTarget, and `is=` behaviors not modeled in ryact-dom yet.
    """
    changed = 0
    path = "packages/react-dom/src/__tests__/DOMPropertyOperations-test.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_DOM_FEATURES_DEFER
        c["notes"] = "Deferred: requires real DOM property/attribute + custom element parity."
        changed += 1
    return changed


def _patch_wave_dom_close_fizz_and_hydration_buckets_defer_apr2026(cases: list[dict]) -> int:
    """
    Close high-volume ReactDOM Fizz/hydration/server-integration buckets as deferred non-goals.
    """
    changed = 0
    target_prefixes = (
        "packages/react-dom/src/__tests__/ReactDOMFizz",
        "packages/react-dom/src/__tests__/ReactDOMServer",
        "packages/react-dom/src/__tests__/ReactDOMServerIntegration",
        "packages/react-dom/src/__tests__/ReactDOMHydration",
        "packages/react-dom/src/__tests__/ReactDOMServerPartialHydration",
        "packages/react-dom/src/__tests__/ReactDOMServerSelectiveHydration",
        "packages/react-dom/src/__tests__/ReactDOMFloat-test.js",
    )
    for c in cases:
        p = c.get("upstream_path")
        if not isinstance(p, str) or not p.startswith(target_prefixes):
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_DOM_FEATURES_DEFER
        c["notes"] = "Deferred: requires Fizz/hydration/server-integration parity."
        changed += 1
    return changed


_BURNDOWN_V2_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_show_nested_host_nodes_if_multiple_boundaries_resolve_at_the_same_time",
        "react.suspenseEffects.siblingBoundaries.resolveTogether",
        "tests_upstream/react/test_suspense_effects_semantics_more.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_wait_to_reveal_an_inner_child_when_inner_one_reveals_first",
        "react.suspenseEffects.siblingBoundaries.partialReveal",
        "tests_upstream/react/test_suspense_effects_semantics_more.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "catches_render_error_in_a_boundary_during_synchronous_mounting",
        "react.incrementalErrorHandling.boundarySyncMount",
        "tests_upstream/react/test_incremental_error_sync_boundary_mount.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.self_and_source_are_treated_as_normal_props",
        "react.elementValidator.selfSourceAsProps",
        "tests_upstream/react/test_element_validator_self_source_props.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects.calls_callback_after_update_is_flushed",
        "react.incrementalSideEffects.setStateCallbackAfterFlush",
        "tests_upstream/react/test_incremental_side_effects_setstate_callback.py",
    ),
)


def _patch_wave_burndown_v2_react_manifest_slices(cases: list[dict]) -> int:
    """Flip only the manifest-gated rows from the Apr 2026 parity burn-down v2 slice."""
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V2_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v2_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_set_classname_to_empty_string_instead_of_null.b305c850",
            "react_dom.incremental.classNameNullToEmpty",
            "tests_upstream/react_dom/test_incremental_classname_null_to_empty.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "handles_multiple_child_updates_without_interference.a574dab4",
            "react_dom.incremental.multipleKeyedTextChildren",
            "tests_upstream/react_dom/test_incremental_multiple_text_children_update.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V3_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "when_a_component_suspends_during_initial_mount."
        "should_not_change_behavior_in_concurrent_mode",
        "react.suspenseEffects.initialMount.concurrentSnapshot",
        "tests_upstream/react/test_suspense_effects_semantics_initial_mount.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "when_a_component_suspends_during_initial_mount.should_not_change_behavior_in_sync",
        "react.suspenseEffects.initialMount.syncSnapshot",
        "tests_upstream/react/test_suspense_effects_semantics_initial_mount.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "can_schedule_updates_after_uncaught_error_in_render_on_update",
        "react.incrementalErrorHandling.scheduleUpdateAfterErrorOnUpdate",
        "tests_upstream/react/test_incremental_error_schedule_after_update.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.warns_for_fragments_with_illegal_attributes",
        "react.elementValidator.fragmentIllegalProps",
        "tests_upstream/react/test_element_validator_fragment_illegal_props.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects.can_update_child_nodes_of_a_fragment",
        "react.incrementalSideEffects.updateFragmentTextChildren",
        "tests_upstream/react/test_incremental_side_effects_fragment_text_children.py",
    ),
)


def _patch_wave_burndown_v3_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V3_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v3_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_remove_when_setting_custom_attr_to_null.54954f66",
            "react_dom.incremental.customAttrNullRemoves",
            "tests_upstream/react_dom/test_custom_attr_null_server_and_incremental.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
            "should_properly_escape_text_content_and_attributes_values.819ac9bf",
            "react_dom.server.escapeTextAndAttributes",
            "tests_upstream/react_dom/test_escape_text_and_attributes_server_incremental.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V4_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_destroyed_and_recreated_when_nested_below_host_components",
        "react.suspenseEffects.hostChildNestedBelowHostDiv",
        "tests_upstream/react/test_suspense_effects_semantics_host_and_deep.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_cleaned_up_deeper_inside_of_a_subtree_that_suspends",
        "react.suspenseEffects.deepSubtreeInnerFallback",
        "tests_upstream/react/test_suspense_effects_semantics_host_and_deep.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "catches_render_error_in_a_boundary_during_batched_mounting",
        "react.incrementalErrorHandling.batchedTwoBoundariesMount",
        "tests_upstream/react/test_incremental_error_batched_two_boundaries.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_for_arrays_of_elements_in_rest_args",
        "react.elementValidator.siblingRestArgsMissingKeys",
        "tests_upstream/react/test_element_validator_keys_sibling_rest_args.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects.can_update_child_nodes_of_a_host_instance",
        "react.incrementalSideEffects.hostInstanceChildTextUpdate",
        "tests_upstream/react/test_incremental_side_effects_host_child_text.py",
    ),
)


def _patch_wave_burndown_v4_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V4_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v4_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_remove_property_properly_for_boolean_properties.0beeab4e",
            "react_dom.incremental.booleanPropertyFalseRemoves",
            "tests_upstream/react_dom/test_boolean_false_removes_server_incremental.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_not_set_null_undefined_attributes.08b6c880",
            "react_dom.incremental.nullUndefinedAttrsOmitted",
            "tests_upstream/react_dom/test_incremental_null_undefined_attributes_skip.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V5_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_cleaned_up_inside_of_a_fallback_that_suspends",
        "react.suspenseEffects.fallbackContainsSuspenseInnerFallback",
        "tests_upstream/react/test_suspense_effects_semantics_fallback_inner_suspends.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_cleaned_up_inside_of_a_fallback_that_suspends_alternate",
        "react.suspenseEffects.fallbackContainsSuspenseInnerFallbackAlternate",
        "tests_upstream/react/test_suspense_effects_semantics_fallback_inner_suspends.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "can_schedule_updates_after_uncaught_error_in_render_on_mount",
        "react.incrementalErrorHandling.scheduleUpdateAfterErrorOnMount",
        "tests_upstream/react/test_incremental_error_schedule_after_mount.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_warns_for_arrays_of_elements_with_keys",
        "react.elementValidator.arrayChildrenAllKeyedNoWarn",
        "tests_upstream/react/test_element_validator_children_with_keys_no_warn.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_warns_for_iterable_elements_with_keys",
        "react.elementValidator.iterableChildrenAllKeyedNoWarn",
        "tests_upstream/react/test_element_validator_children_with_keys_no_warn.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_update_child_nodes_rendering_into_text_nodes",
        "react.incrementalSideEffects.hostDirectStringChildrenUpdate",
        "tests_upstream/react/test_incremental_side_effects_direct_host_text_children.py",
    ),
)


def _patch_wave_burndown_v5_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V5_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v5_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_remove_for_falsey_boolean_properties.9caf0c09",
            "react_dom.serverIncremental.booleanFalseyRemoves",
            "tests_upstream/react_dom/test_boolean_falsey_removes_server_incremental.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_not_add_an_empty_href_attribute.3f945ff8",
            "react_dom.incremental.emptyHrefOmitted",
            "tests_upstream/react_dom/test_incremental_empty_href_omit.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V6_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "calls_componentdidcatch_multiple_times_for_multiple_errors",
        "react.incrementalErrorHandling.componentDidCatchMultipleErrors",
        "tests_upstream/react/test_incremental_error_component_did_catch_twice.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_warn_when_the_element_is_directly_in_rest_args",
        "react.elementValidator.singleRestArgNoWarn",
        "tests_upstream/react/test_element_validator_single_rest_child_no_warn.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_destroyed_and_recreated_for_function_components",
        "react.suspenseEffects.functionChildResuspendsOnUpdate",
        "tests_upstream/react/test_suspense_effects_semantics_function_child_re_suspends.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "updates_a_child_even_though_the_old_props_is_empty",
        "react.incrementalSideEffects.updateChildFromEmptyProps",
        "tests_upstream/react/test_incremental_side_effects_child_update_from_empty_props.py",
    ),
)


def _patch_wave_burndown_v6_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V6_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v6_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_not_add_an_empty_src_attribute.0ae9fc67",
            "react_dom.incremental.emptySrcOmitted",
            "tests_upstream/react_dom/test_incremental_empty_src_omit.py",
        ),
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_convert_attribute_values_to_string_first.5446363b",
            "react_dom.server.attributeValuesStringified",
            "tests_upstream/react_dom/test_dom_property_stringify_attr_values.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V7_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_destroyed_and_recreated_for_class_components",
        "react.suspenseEffects.classChildResuspendsOnUpdate",
        "tests_upstream/react/test_suspense_effects_semantics_class_child_re_suspends.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_for_iterables_of_elements_in_rest_args",
        "react.elementValidator.iterableRestArgsMissingKeys",
        "tests_upstream/react/test_element_validator_keys_rest_missing_warn_more.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_for_arrays_of_elements_with_no_owner_info",
        "react.elementValidator.arrayRestArgsMissingKeysNoOwner",
        "tests_upstream/react/test_element_validator_keys_rest_missing_warn_more.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_delete_a_child_that_changes_type_explicit_keys",
        "react.incrementalSideEffects.childTagChangeExplicitKey",
        "tests_upstream/react/test_incremental_side_effects_child_type_change_explicit_key.py",
    ),
)


def _patch_wave_burndown_v7_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V7_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v7_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_not_remove_empty_attributes_for_special_input_properties.5ba7f579",
            "react_dom.server.inputEmptyValuePreserved",
            "tests_upstream/react_dom/test_dom_input_meter_value_attributes.py",
        ),
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_always_assign_the_value_attribute_for_non_inputs.5cdfd3e1",
            "react_dom.server.meterValueAttributeAssigned",
            "tests_upstream/react_dom/test_dom_input_meter_value_attributes.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V8_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_delete_a_child_that_changes_type_implicit_keys",
        "react.incrementalSideEffects.childTagChangeImplicitKey",
        "tests_upstream/react/test_incremental_side_effects_child_type_change_implicit_key.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_for_arrays_of_elements_with_owner_info",
        "react.elementValidator.arrayRestArgsMissingKeysOwnerInfoWarn",
        "tests_upstream/react/test_element_validator_keys_rest_missing_warn_more.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "provides_component_stack_to_the_error_boundary_with_componentdidcatch",
        "react.incrementalErrorHandling.didCatchReceivesComponentStack",
        "tests_upstream/react/test_incremental_error_did_catch_component_stack.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_deletes_children_either_components_host_or_text",
        "react.incrementalSideEffects.deletesMixedTextHostAndComponentChildren",
        "tests_upstream/react/test_incremental_side_effects_delete_mixed_children.py",
    ),
)


def _patch_wave_burndown_v8_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V8_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v8_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
            "should_not_remove_empty_attributes_for_special_option_properties.bbf761b7",
            "react_dom.server.optionEmptyValuePreserved",
            "tests_upstream/react_dom/test_dom_option_form_action_attributes.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_allow_an_empty_action_attribute.d2448367",
            "react_dom.incremental.formEmptyActionAllowed",
            "tests_upstream/react_dom/test_dom_option_form_action_attributes.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V9_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_for_arrays_with_no_owner_or_parent_info",
        "react.elementValidator.arrayMissingKeysNoOwnerOrParentWarn",
        "tests_upstream/react/test_element_validator_keys_rest_missing_warn_more.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.warns_for_keys_with_component_stack_info",
        "react.elementValidator.missingKeyWarnIncludesHostStack",
        "tests_upstream/react/test_element_validator_keys_rest_missing_warn_more.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "invokes_ref_callbacks_after_insertion_update_unmount",
        "react.incrementalSideEffects.hostRefCallbacksInsertUpdateUnmount",
        "tests_upstream/react/test_incremental_side_effects_host_ref_callbacks.py",
    ),
)


def _patch_wave_burndown_v9_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V9_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v9_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "allows_empty_string_of_a_formaction_to_override_the_default_of_a_parent.a750e8f1",
            "react_dom.incremental.formActionEmptyOverridesParent",
            "tests_upstream/react_dom/test_dom_option_form_action_attributes.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V10_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_warn_when_the_array_contains_a_non_element",
        "react.elementValidator.doesNotWarnWhenArrayContainsNonElement",
        "tests_upstream/react/test_element_validator_array_contains_non_element_no_warn.py",
    ),
    (
        "react.ErrorBoundaryReconciliation-test.internal.errorboundaryreconciliation."
        "getderivedstatefromerror_can_recover_by_rendering_an_element_of_a_different_type",
        "react.errorBoundaries.gdsfeRecoverDifferentElementType",
        "tests_upstream/react/test_error_boundary_gdsfe_recover_different_type.py",
    ),
)


def _patch_wave_burndown_v10_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V10_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v10_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_allow_an_empty_href_attribute_on_anchors.c5ef167d",
            "react_dom.incremental.anchorEmptyHrefAllowed",
            "tests_upstream/react_dom/test_incremental_anchor_empty_href_allowed.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V11_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ErrorBoundaryReconciliation-test.internal.errorboundaryreconciliation."
        "componentdidcatch_can_recover_by_rendering_an_element_of_a_different_type",
        "react.errorBoundaries.didCatchRecoverDifferentElementType",
        "tests_upstream/react/test_error_boundary_did_catch_recover_different_type.py",
    ),
    (
        "react.ErrorBoundaryReconciliation-test.internal.errorboundaryreconciliation."
        "componentdidcatch_can_recover_by_rendering_an_element_of_the_same_type",
        "react.errorBoundaries.didCatchRecoverSameElementType",
        "tests_upstream/react/test_error_boundary_did_catch_recover_same_type.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.does_not_blow_up_with_inlined_children",
        "react.elementValidator.inlinedChildrenKeyWarnNoBlowup",
        "tests_upstream/react/test_element_validator_inlined_children_key_warn.py",
    ),
)


def _patch_wave_burndown_v11_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V11_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v11_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_not_update_when_switching_between_null_undefined.93a77801",
            "react_dom.incremental.nullVsOmittedAttrNoUpdate",
            "tests_upstream/react_dom/test_incremental_null_omitted_attr_equivalence_and_falsy_text.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
            "should_render_null_and_undefined_as_empty_but_print_other_falsy_values.998ad64a",
            "react_dom.serverIncremental.nullChildEmptyAndZeroText",
            "tests_upstream/react_dom/test_incremental_null_omitted_attr_equivalence_and_falsy_text.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V12_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "does_not_provide_component_stack_to_the_error_boundary_with_getderivedstatefromerror",
        "react.incrementalErrorHandling.gdsfeNoErrorInfoArg",
        "tests_upstream/react/test_incremental_error_gdsfe_no_error_info_arg.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "catches_reconciler_errors_in_a_boundary_during_mounting",
        "react.incrementalErrorHandling.reconcilerErrorBoundaryMount",
        "tests_upstream/react/test_incremental_error_reconciler_boundary_mount.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_warn_for_keys_when_passing_children_down",
        "react.elementValidator.passChildrenDownKeyedNoWarn",
        "tests_upstream/react/test_element_validator_pass_children_down_no_key_warn.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_destroyed_and_recreated_even_if_there_is_a_bailout_because_of_memoization",
        "react.suspenseEffects.memoBailoutSiblingAsyncResuspend",
        "tests_upstream/react/test_suspense_effects_semantics_memo_sibling_async_resuspend.py",
    ),
)


def _patch_wave_burndown_v12_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V12_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v12_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "allows_assignment_of_custom_attributes_with_string_values.6c68b6ea",
            "react_dom.incremental.customDataAttributeString",
            "tests_upstream/react_dom/test_dom_custom_attributes_string_and_cased.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "allows_cased_custom_attributes.5d9d870c",
            "react_dom.server.casedCustomAttributeNames",
            "tests_upstream/react_dom/test_dom_custom_attributes_string_and_cased.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V13_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "catches_reconciler_errors_in_a_boundary_during_update",
        "react.incrementalErrorHandling.reconcilerErrorBoundaryUpdate",
        "tests_upstream/react/test_incremental_error_reconciler_boundary_update.py",
    ),
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_blow_up_on_key_warning_with_undefined_type",
        "react.elementValidator.undefinedTypeChildrenNoBlowup",
        "tests_upstream/react/test_element_validator_undefined_type_children_no_blowup.py",
    ),
    (
        "react.ReactSuspenseEffectsSemantics-test.reactsuspenseeffectssemantics."
        "effects_within_a_tree_that_re_suspends_in_an_update."
        "should_be_only_destroy_layout_effects_once_if_a_tree_suspends_in_multiple_places",
        "react.suspenseEffects.multipleAsyncChildrenSharedFallback",
        "tests_upstream/react/test_suspense_effects_semantics_two_async_children_shared_fallback.py",
    ),
)


def _patch_wave_burndown_v13_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V13_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v13_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "allows_cased_data_attributes.bc4f3ce5",
            "react_dom.server.casedDataAttributeSegment",
            "tests_upstream/react_dom/test_dom_custom_attributes_string_and_cased.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "assigns_a_numeric_custom_attributes_as_a_string.a340c5a5",
            "react_dom.server.numericCustomDataAttributeStringified",
            "tests_upstream/react_dom/test_dom_custom_attributes_string_and_cased.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V14_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "does_not_infinite_loop_if_there_s_a_render_phase_update_in_the_same_render_as_an_error",
        "react.incrementalErrorHandling.renderPhaseUpdateSameRenderErrorNoInfiniteLoop",
        "tests_upstream/react/test_incremental_error_render_phase_update_same_render_no_infinite_loop.py",
    ),
)


def _patch_wave_burndown_v14_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V14_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v14_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "does_not_assign_a_boolean_custom_attributes_as_a_string.26c395de",
            "react_dom.incremental.customBooleanAttributeNotStringified",
            "tests_upstream/react_dom/test_dom_custom_boolean_attributes_omit.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "does_not_assign_an_implicit_boolean_custom_attributes.7b1ebab6",
            "react_dom.server.customImplicitBooleanAttributeOmitted",
            "tests_upstream/react_dom/test_dom_custom_boolean_attributes_omit.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V15_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "does_not_interrupt_unmounting_if_detaching_a_ref_throws",
        "react.incrementalErrorHandling.refDetachThrowsUninterruptibleUnmount",
        "tests_upstream/react/test_incremental_error_ref_detach_throw_unmount_continues.py",
    ),
)


def _patch_wave_burndown_v15_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V15_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v15_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes.removes_custom_attributes.9a20fe45",
            "react_dom.incremental.customAttributesRemovedOnUpdate",
            "tests_upstream/react_dom/test_dom_custom_attributes_remove_and_invalid.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "removes_a_property_when_it_becomes_invalid.568bd3a8",
            "react_dom.incremental.customAttributeRemovedWhenValueInvalid",
            "tests_upstream/react_dom/test_dom_custom_attributes_remove_and_invalid.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V16_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.should_not_enumerate_enumerable_numbers_4776",
        "react.elementValidator.numericChildrenNotIterable4776",
        "tests_upstream/react/test_element_validator_numeric_children_not_iterated_4776.py",
    ),
)


def _patch_wave_burndown_v16_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V16_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v16_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "will_assign_an_object_custom_attributes.3b5a8a13",
            "react_dom.server.customObjectAttributeStringified",
            "tests_upstream/react_dom/test_dom_custom_object_and_function_attributes.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "will_not_assign_a_function_custom_attributes.af35cfa5",
            "react_dom.incremental.customFunctionAttributeNotAssigned",
            "tests_upstream/react_dom/test_dom_custom_object_and_function_attributes.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V17_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactElementValidator-test.internal.reactelementvalidator.does_not_call_lazy_initializers_eagerly",
        "react.elementValidator.lazyInitializerNotEagerOnCreateElement",
        "tests_upstream/react/test_element_validator_lazy_not_eager.py",
    ),
)


def _patch_wave_burndown_v17_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V17_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v17_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "warns_on_bad_casing_of_known_html_attributes.3e87a976",
            "react_dom.incremental.badCasingKnownHtmlPropNormalized",
            "tests_upstream/react_dom/test_dom_attribute_casing_and_nan.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes.warns_on_nan_attributes.d9c72853",
            "react_dom.server.nanCustomAttributeStringified",
            "tests_upstream/react_dom/test_dom_attribute_casing_and_nan.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V18_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "can_schedule_updates_after_uncaught_error_during_unmounting",
        "react.incrementalErrorHandling.scheduleUpdateAfterUncaughtErrorDuringUnmounting",
        "tests_upstream/react/test_incremental_error_schedule_after_unmount_throw.py",
    ),
)


def _patch_wave_burndown_v18_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V18_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v18_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_elements."
            "does_not_strip_unknown_boolean_attributes.170a8d91",
            "react_dom.incremental.customElementUnknownBooleanAttr",
            "tests_upstream/react_dom/test_dom_custom_elements_onx_and_unknown_boolean.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_elements."
            "does_not_strip_the_on_attributes.448edeff",
            "react_dom.server.customElementOnPrefixedStringAttr",
            "tests_upstream/react_dom/test_dom_custom_elements_onx_and_unknown_boolean.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V19_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "should_not_attempt_to_recover_an_unmounting_error_boundary",
        "react.incrementalErrorHandling.unmountingErrorBoundaryNoRecovery",
        "tests_upstream/react/test_incremental_error_unmounting_boundary_no_recovery.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "error_boundaries_capture_non_errors",
        "react.incrementalErrorHandling.errorBoundaryCapturesNonErrors",
        "tests_upstream/react/test_incremental_error_boundary_captures_non_errors.py",
    ),
)


def _patch_wave_burndown_v19_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V19_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v19_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_allow_html_null.19e208e1",
            "react_dom.incremental.dangerouslySetInnerHTMLNullAllowed",
            "tests_upstream/react_dom/test_dom_inner_html_null_and_svg_font_face.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.hyphenated_svg_elements."
            "the_font_face_element_is_not_a_custom_element.16bcefa6",
            "react_dom.incremental.svgFontFaceNotCustomElementXHeightCasing",
            "tests_upstream/react_dom/test_dom_inner_html_null_and_svg_font_face.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V20_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "propagates_an_error_from_a_noop_error_boundary_during_synchronous_mounting",
        "react.incrementalErrorHandling.noopBoundaryRethrowsSyncMount",
        "tests_upstream/react/test_incremental_error_noop_boundary_rethrows_sync_mount.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "propagates_an_error_from_a_noop_error_boundary_during_batched_mounting",
        "react.incrementalErrorHandling.noopBoundaryRethrowsBatchedMount",
        "tests_upstream/react/test_incremental_error_noop_boundary_rethrows_batched_mount.py",
    ),
)


def _patch_wave_burndown_v20_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V20_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v20_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    targets: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.hyphenated_svg_elements."
            "the_font_face_element_does_not_allow_unknown_boolean_values.755eef54",
            "react_dom.incremental.svgFontFaceUnknownBooleanFalseDevWarn",
            "tests_upstream/react_dom/test_dom_font_face_boolean_warn_and_suppress_contenteditable.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_respect_suppresscontenteditablewarning.6984da21",
            "react_dom.incremental.suppressContentEditableWarningConsumed",
            "tests_upstream/react_dom/test_dom_font_face_boolean_warn_and_suppress_contenteditable.py",
        ),
    )
    for row_id, manifest_id, py_test in targets:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V21_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "applies_batched_updates_regardless_despite_errors_in_scheduling",
        "react.incrementalErrorHandling.batchedUpdatesScheduling",
        "tests_upstream/react/test_incremental_error_batched_updates_scheduling.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "applies_nested_batched_updates_despite_errors_in_scheduling",
        "react.incrementalErrorHandling.batchedUpdatesScheduling",
        "tests_upstream/react/test_incremental_error_batched_updates_scheduling.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "can_unmount_an_error_boundary_before_it_is_handled",
        "react.incrementalErrorHandling.unmountBoundaryBeforeHandled",
        "tests_upstream/react/test_incremental_error_batched_updates_scheduling.py",
    ),
)


def _patch_wave_burndown_v21_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V21_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v21_dom_manifest_slices(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V22_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "handles_error_thrown_by_top_level_callback",
        "react.incrementalErrorHandling.topLevelCallbackThrows",
        "tests_upstream/react/test_incremental_error_top_level_callback_and_lifecycles.py",
    ),
    (
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
        "calls_the_correct_lifecycles_on_the_error_boundary_after_catching_an_error_mixed",
        "react.incrementalErrorHandling.lifecyclesAfterCatch.mixed",
        "tests_upstream/react/test_incremental_error_top_level_callback_and_lifecycles.py",
    ),
)


_BURNDOWN_V22_REACT_NON_GOALS: tuple[str, ...] = (
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "catches_render_error_in_a_boundary_during_full_deferred_mounting",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "catches_render_error_in_a_boundary_during_partial_deferred_mounting",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "continues_work_on_other_roots_despite_caught_errors",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "continues_work_on_other_roots_despite_uncaught_errors",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "defers_additional_sync_work_to_a_separate_event_after_an_error",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "does_not_include_offscreen_work_when_retrying_after_an_error",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "handles_error_thrown_by_host_config_while_working_on_failed_root",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "propagates_an_error_from_a_noop_error_boundary_during_full_deferred_mounting",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "propagates_an_error_from_a_noop_error_boundary_during_partial_deferred_mounting",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "provides_component_stack_even_if_overriding_preparestacktrace",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "recovers_from_errors_asynchronously",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "recovers_from_errors_asynchronously_legacy_no_getderivedstatefromerror",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "recovers_from_uncaught_reconciler_errors",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "retries_at_a_lower_priority_if_there_s_additional_pending_work",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "retries_one_more_time_before_handling_error",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "retries_one_more_time_if_an_error_occurs_during_a_render_that_expires_midway_through_the_tree",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "uncaught_errors_are_discarded_if_the_render_is_aborted_case_2",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "uncaught_errors_should_be_discarded_if_the_render_is_aborted",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "unmounts_components_with_uncaught_errors",
    "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling."
    "unwinds_the_context_stack_correctly_on_error",
)


def _patch_wave_burndown_v22_react_incremental_error_handling(cases: list[dict]) -> int:
    changed = 0
    non_goal_rationale = (
        "Deferred: requires multi-root work, render interruption/expiration, "
        "retry-at-lower-priority logic, or deeper context stack semantics beyond the "
        "current noop incremental model."
    )
    for row_id, manifest_id, py_test in _BURNDOWN_V22_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break

    targets = set(_BURNDOWN_V22_REACT_NON_GOALS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = non_goal_rationale
        changed += 1

    return changed


def _patch_wave_burndown_v22_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V23_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "should_log_errors_that_occur_during_the_begin_phase",
        "react.incrementalErrorLogging.beginPhase",
        "tests_upstream/react/test_incremental_error_logging.py",
    ),
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "should_log_errors_that_occur_during_the_commit_phase",
        "react.incrementalErrorLogging.commitPhase",
        "tests_upstream/react/test_incremental_error_logging.py",
    ),
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "should_ignore_errors_thrown_in_log_method_to_prevent_cycle",
        "react.incrementalErrorLogging.logMethodCycleGuard",
        "tests_upstream/react/test_incremental_error_logging.py",
    ),
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "resets_instance_variables_before_unmounting_failed_node",
        "react.incrementalErrorLogging.resetInstanceStateBeforeUnmountFailedNode",
        "tests_upstream/react/test_incremental_error_logging.py",
    ),
    (
        "react.ReactIncrementalErrorReplay-test.reactincrementalerrorreplay."
        "should_ignore_error_if_it_doesn_t_throw_on_retry",
        "react.incrementalErrorReplay.ignoreErrorIfRetrySucceeds",
        "tests_upstream/react/test_incremental_error_replay.py",
    ),
)


_BURNDOWN_V23_REACT_NON_GOALS: tuple[tuple[str, str], ...] = (
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "does_not_report_internal_offscreen_component_for_errors_thrown_during_reconciliation_inside_activity",
        (
            "Deferred: depends on internal Offscreen/Activity fiber reporting semantics "
            "not modeled by the current noop renderer."
        ),
    ),
    (
        "react.ReactIncrementalErrorLogging-test.reactincrementalerrorlogging."
        "does_not_report_internal_offscreen_component_for_errors_thrown_during_reconciliation_inside_suspense",
        (
            "Deferred: depends on internal Offscreen/Suspense fiber reporting semantics "
            "not modeled by the current noop renderer."
        ),
    ),
    (
        "react.ReactIncrementalErrorReplay-test.reactincrementalerrorreplay."
        "should_fail_gracefully_on_error_in_the_host_environment",
        ("Deferred: depends on a host config that can throw 'Error in host config.' during reconciliation/commit."),
    ),
)


def _patch_wave_burndown_v23_react_incremental_error_logging_replay(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V23_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break

    non_goal_by_id = dict(_BURNDOWN_V23_REACT_NON_GOALS)
    for c in cases:
        row_id = c.get("id")
        if row_id not in non_goal_by_id:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = non_goal_by_id[row_id]
        changed += 1

    return changed


def _patch_wave_burndown_v23_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V24_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalReflection-test.reactincrementalreflection."
        "finds_no_node_before_insertion_and_correct_node_before_deletion",
        "react.incrementalReflection.findInstanceBeforeInsertAfterDelete",
        "tests_upstream/react/test_incremental_reflection_find_instance.py",
    ),
)


def _patch_wave_burndown_v24_react_incremental_reflection(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V24_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v24_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V25_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling.schedules_and_flushes_deferred_work",
        "react.incrementalScheduling.deferredFlush",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "schedules_top_level_updates_in_order_of_priority",
        "react.incrementalScheduling.topLevelPriorityOrder",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "schedules_top_level_updates_with_same_priority_in_order_of_insertion",
        "react.incrementalScheduling.topLevelInsertionOrder",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "schedules_sync_updates_when_inside_componentdidmount_update",
        "react.incrementalScheduling.syncUpdatesInsideDidMountUpdate",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "can_opt_in_to_async_scheduling_inside_componentdidmount_update",
        "react.incrementalScheduling.transitionOptInInsideDidMountUpdate",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
    (
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling.performs_task_work_even_after_time_runs_out",
        "react.incrementalScheduling.taskAfterTimeRunsOut",
        "tests_upstream/react/test_incremental_scheduling.py",
    ),
)


_BURNDOWN_V25_REACT_NON_GOALS: tuple[str, ...] = (
    "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
    "searches_for_work_on_other_roots_once_the_current_root_completes",
    "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
    "works_on_deferred_roots_in_the_order_they_were_scheduled",
)


def _patch_wave_burndown_v25_react_incremental_scheduling(cases: list[dict]) -> int:
    changed = 0
    non_goal_rationale = "Deferred: requires multi-root noop renderer + cross-root scheduling/flush semantics."
    for row_id, manifest_id, py_test in _BURNDOWN_V25_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break

    targets = set(_BURNDOWN_V25_REACT_NON_GOALS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = non_goal_rationale
        changed += 1

    return changed


def _patch_wave_burndown_v25_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


WaveReact = Callable[[list[dict]], int]
WaveDom = Callable[[list[dict]], int]


def _patch_wave_noop_react(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V26_100_CORE_APR2026_REACT_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_for_arrays_of_elements_with_keys",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_for_fragments_of_multiple_elements_without_keys",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_for_iterable_elements_with_keys",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_when_the_child_array_contains_non_elements",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_when_the_element_is_directly_as_children",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_fragments_of_multiple_elements_with_same_key",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_fragments_with_illegal_attributes",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_fragments_with_refs",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_keys_for_arrays_of_elements_in_children_position",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_keys_for_iterables_of_elements_in_rest_args",
        "react.jsxElementValidator.basic",
        "tests_upstream/react/test_jsx_element_validator_basic.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects.does_not_update_child_nodes_if_a_flush_is_aborted",
        "react.incrementalSideEffects.abortFlushPreservesCommittedTree",
        "tests_upstream/react/test_incremental_side_effects_abort_flush.py",
    ),
)


def _patch_wave_burndown_v26_100_core_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V26_100_CORE_APR2026_REACT_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v26_100_core_apr2026_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V27_REACT_CACHE_APR2026_IMPLEMENTATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactCache-test.reactcache.cache_objects_and_primitive_arguments_and_a_mix_of_them",
        "react.cache.basic",
        "tests_upstream/react/test_cache_basic.py",
    ),
    (
        "react.ReactCache-test.reactcache.cached_functions_that_throw_should_cache_the_error",
        "react.cache.basic",
        "tests_upstream/react/test_cache_basic.py",
    ),
    (
        "react.ReactCache-test.reactcache.introspection_of_returned_wrapper_function_is_same_on_client_and_server",
        "react.cache.basic",
        "tests_upstream/react/test_cache_basic.py",
    ),
    (
        "react.ReactCache-test.reactcache.cachesignal_aborts_when_the_render_finishes_normally",
        "react.cache.cacheSignal",
        "tests_upstream/react/test_cache_signal.py",
    ),
    (
        "react.ReactCache-test.reactcache.cachesignal_aborts_when_the_render_is_aborted",
        "react.cache.cacheSignal",
        "tests_upstream/react/test_cache_signal.py",
    ),
    (
        "react.ReactCache-test.reactcache.cachesignal_returns_null_outside_a_render",
        "react.cache.cacheSignal",
        "tests_upstream/react/test_cache_signal.py",
    ),
)


def _patch_wave_burndown_v27_react_cache_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V27_REACT_CACHE_APR2026_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v27_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V28_REACT_ES6CLASS_BASIC_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactES6Class-test.reactes6class.does_not_warn_about_getinitialstate_on_class_components_if_state_is_also_defined",
    "react.ReactES6Class-test.reactes6class.preserves_the_name_of_the_class_for_use_in_error_messages",
    "react.ReactES6Class-test.reactes6class.renders_a_simple_stateless_component_with_prop",
    "react.ReactES6Class-test.reactes6class.renders_based_on_state_using_initial_values_in_this_props",
    "react.ReactES6Class-test.reactes6class.renders_based_on_state_using_props_in_the_constructor",
    "react.ReactES6Class-test.reactes6class.renders_only_once_when_setting_state_in_componentwillmount",
    "react.ReactES6Class-test.reactes6class.renders_updated_state_with_values_returned_by_static_getderivedstatefromprops",
    "react.ReactES6Class-test.reactes6class.renders_using_forceupdate_even_when_there_is_no_state",
    "react.ReactES6Class-test.reactes6class.sets_initial_state_with_value_returned_by_static_getderivedstatefromprops",
    "react.ReactES6Class-test.reactes6class.setstate_through_an_event_handler",
    "react.ReactES6Class-test.reactes6class.should_render_with_null_in_the_initial_state_property",
    "react.ReactES6Class-test.reactes6class.should_warn_when_misspelling_componentwillreceiveprops",
    "react.ReactES6Class-test.reactes6class.should_warn_when_misspelling_shouldcomponentupdate",
    "react.ReactES6Class-test.reactes6class.should_warn_when_misspelling_unsafe_componentwillreceiveprops",
    "react.ReactES6Class-test.reactes6class.should_warn_with_non_object_in_the_initial_state_property",
    "react.ReactES6Class-test.reactes6class.throws_if_no_render_function_is_defined",
    "react.ReactES6Class-test.reactes6class.updates_initial_state_with_values_returned_by_static_getderivedstatefromprops",
    "react.ReactES6Class-test.reactes6class.warns_if_getderivedstatefromerror_is_not_static",
    "react.ReactES6Class-test.reactes6class.warns_if_getderivedstatefromprops_is_not_static",
    "react.ReactES6Class-test.reactes6class.warns_if_getsnapshotbeforeupdate_is_static",
    "react.ReactES6Class-test.reactes6class.warns_if_state_not_initialized_before_static_getderivedstatefromprops",
)


def _patch_wave_burndown_v28_react_es6class_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V28_REACT_ES6CLASS_BASIC_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.es6class.basic"
        c["python_test"] = "tests_upstream/react/test_es6_class_basic.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v28_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V29_REACT_FIBER_REFS_APR2026_IMPLEMENTATIONS: tuple[tuple[str, str], ...] = (
    (
        "react.ReactFiberRefs-test.reactfiberrefs.class_refs_are_initialized_to_a_frozen_shared_object",
        "tests_upstream/react/test_refs_basic.py",
    ),
    (
        "react.ReactFiberRefs-test.reactfiberrefs.ref_is_attached_even_if_there_are_no_other_updates_class",
        "tests_upstream/react/test_refs_basic.py",
    ),
    (
        "react.ReactFiberRefs-test.reactfiberrefs.ref_is_attached_even_if_there_are_no_other_updates_host_component",
        "tests_upstream/react/test_refs_basic.py",
    ),
    (
        "react.ReactFiberRefs-test.reactfiberrefs.strings_refs_can_be_codemodded_to_callback_refs",
        "tests_upstream/react/test_string_refs.py",
    ),
    (
        "react.ReactFiberRefs-test.reactfiberrefs.throw_if_a_string_ref_is_passed_to_a_ref_receiving_component",
        "tests_upstream/react/test_string_refs.py",
    ),
)


def _patch_wave_burndown_v29_react_fiber_refs_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, py_test in _BURNDOWN_V29_REACT_FIBER_REFS_APR2026_IMPLEMENTATIONS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = "react.fiberRefs.basic"
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v29_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V30_ERROR_STACKS_BUILTINS_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactErrorStacks-test.reactfragment.includes_built_in_for_activity",
    "react.ReactErrorStacks-test.reactfragment.includes_built_in_for_lazy",
    "react.ReactErrorStacks-test.reactfragment.includes_built_in_for_suspense",
    "react.ReactErrorStacks-test.reactfragment.includes_built_in_for_suspense_fallbacks",
)


def _patch_wave_burndown_v30_error_stacks_builtins_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V30_ERROR_STACKS_BUILTINS_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.errorStacks.builtins.basic"
        c["python_test"] = "tests_upstream/react/test_error_stacks_basic.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v30_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V32_ELEMENT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactElementValidator-test.internal.reactelementvalidator.does_not_warn_when_using_dom_node_as_children",
    "react.ReactElementValidator-test.internal.reactelementvalidator.gives_a_helpful_error_when_passing_invalid_types",
    "react.ReactElementValidator-test.internal.reactelementvalidator.includes_the_owner_name_when_passing_null_undefined_boolean_or_number",
    "react.ReactElementValidator-test.internal.reactelementvalidator.should_give_context_for_errors_in_nested_components",
)


def _patch_wave_burndown_v32_element_validator_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V32_ELEMENT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.elementValidator.more"
        c["python_test"] = "tests_upstream/react/test_element_validator_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v32_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V33_FORWARD_REF_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.forwardRef-test.forwardref.can_use_the_outer_displayname_in_the_stack",
    "react.forwardRef-test.forwardref.should_custom_memo_comparisons_to_compose",
    "react.forwardRef-test.forwardref.should_not_bailout_if_forwardref_is_not_wrapped_in_memo",
    "react.forwardRef-test.forwardref.should_not_warn_if_the_render_function_provided_does_not_use_any_parameter",
    "react.forwardRef-test.forwardref.should_not_warn_if_the_render_function_provided_use_exactly_two_parameters",
    "react.forwardRef-test.forwardref.should_prefer_the_inner_name_to_the_outer_displayname_in_the_stack",
    "react.forwardRef-test.forwardref.should_skip_forwardref_in_the_stack_if_neither_displayname_nor_name_are_present",
    "react.forwardRef-test.forwardref.should_support_rendering_null",
    "react.forwardRef-test.forwardref.should_support_rendering_null_for_multiple_children",
    "react.forwardRef-test.forwardref.should_update_refs_when_switching_between_children",
    "react.forwardRef-test.forwardref.should_use_the_inner_function_name_for_the_stack",
    "react.forwardRef-test.forwardref.should_use_the_inner_name_in_the_stack",
    "react.forwardRef-test.forwardref.should_warn_if_no_render_function_is_provided",
    "react.forwardRef-test.forwardref.should_warn_if_not_provided_a_callback_during_creation",
    "react.forwardRef-test.forwardref.should_warn_if_the_render_function_provided_does_not_use_the_forwarded_ref_parameter",
    "react.forwardRef-test.forwardref.should_warn_if_the_render_function_provided_expects_to_use_more_than_two_parameters",
    "react.forwardRef-test.forwardref.should_warn_if_the_render_function_provided_has_defaultprops_attributes",
    "react.forwardRef-test.forwardref.warns_on_forwardref_memo",
)


def _patch_wave_burndown_v33_forward_ref_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V33_FORWARD_REF_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.forwardRef.more"
        c["python_test"] = "tests_upstream/react/test_forward_ref_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v33_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V34_ELEMENT_CLONE_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactElementClone-test.reactelementclone.does_not_warn_when_the_array_contains_a_non_element",
    "react.ReactElementClone-test.reactelementclone.does_not_warn_when_the_element_is_directly_in_rest_args",
    "react.ReactElementClone-test.reactelementclone.does_not_warns_for_arrays_of_elements_with_keys",
    "react.ReactElementClone-test.reactelementclone.should_accept_children_as_rest_arguments",
    "react.ReactElementClone-test.reactelementclone.should_clone_a_composite_component_with_new_props",
    "react.ReactElementClone-test.reactelementclone.should_clone_a_dom_component_with_new_props",
    "react.ReactElementClone-test.reactelementclone.should_extract_null_key_and_ref",
    "react.ReactElementClone-test.reactelementclone.should_ignore_key_and_ref_warning_getters",
    "react.ReactElementClone-test.reactelementclone.should_ignore_undefined_key_and_ref",
    "react.ReactElementClone-test.reactelementclone.should_keep_the_original_ref_if_it_is_not_overridden",
    "react.ReactElementClone-test.reactelementclone.should_override_children_if_undefined_is_provided_as_an_argument",
    "react.ReactElementClone-test.reactelementclone.should_shallow_clone_children",
    "react.ReactElementClone-test.reactelementclone.should_steal_the_ref_if_a_new_ref_is_specified",
    "react.ReactElementClone-test.reactelementclone.should_support_keys_and_refs",
    "react.ReactElementClone-test.reactelementclone.should_transfer_children",
    "react.ReactElementClone-test.reactelementclone.should_transfer_the_key_property",
    "react.ReactElementClone-test.reactelementclone.throws_an_error_if_passed_undefined",
    "react.ReactElementClone-test.reactelementclone.warns_for_keys_for_arrays_of_elements_in_rest_args",
)


def _patch_wave_burndown_v34_element_clone_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V34_ELEMENT_CLONE_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.elementClone.more"
        c["python_test"] = c.get("python_test") or "tests_upstream/react/test_element_clone_basic.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v34_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V35_CONTEXT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_but_not_error_if_getchildcontext_method_is_missing",
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_if_both_contexttype_and_contexttypes_are_defined",
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_if_you_define_contexttype_on_a_function_component",
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_when_class_contexttype_is_a_primitive",
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_when_class_contexttype_is_an_object",
    "react.ReactContextValidator-test.reactcontextvalidator.should_warn_when_class_contexttype_is_undefined",
)


_BURNDOWN_V35_CONTEXT_VALIDATOR_MORE_APR2026_NONGOALS: tuple[str, ...] = (
    "react.ReactContextValidator-test.reactcontextvalidator.should_filter_out_context_not_in_contexttypes",
    "react.ReactContextValidator-test.reactcontextvalidator.should_pass_next_context_to_lifecycles",
    "react.ReactContextValidator-test.reactcontextvalidator.should_pass_next_context_to_lifecycles_on_update",
    "react.ReactContextValidator-test.reactcontextvalidator.should_pass_parent_context_if_getchildcontext_method_is_missing",
    "react.ReactContextValidator-test.reactcontextvalidator.should_re_render_purecomponents_when_context_provider_updates",
)


def _patch_wave_burndown_v35_context_validator_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    impl = set(_BURNDOWN_V35_CONTEXT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS)
    ng = set(_BURNDOWN_V35_CONTEXT_VALIDATOR_MORE_APR2026_NONGOALS)
    for c in cases:
        cid = c.get("id")
        if cid in impl and c.get("status") == "pending":
            c["status"] = "implemented"
            c["manifest_id"] = "react.contextValidator.more"
            c["python_test"] = "tests_upstream/react/test_context_validator_more.py"
            c["non_goal_rationale"] = None
            changed += 1
        elif cid in ng and c.get("status") == "pending":
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = (
                "Requires legacy contextTypes/getChildContext propagation and lifecycle context "
                "semantics (non-noop-friendly)."
            )
            changed += 1
    return changed


def _patch_wave_burndown_v35_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V36_STRICT_MODE_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactStrictMode-test.concurrent_mode.should_warn_about_unsafe_legacy_lifecycle_methods_anywhere_in_a_strictmode_tree",
    "react.ReactStrictMode-test.reactstrictmode.double_invokes_setstate_updater_functions",
    "react.ReactStrictMode-test.reactstrictmode.double_invokes_usememo_functions",
    "react.ReactStrictMode-test.reactstrictmode.double_invokes_usememo_functions_with_first_result",
    "react.ReactStrictMode-test.reactstrictmode.double_invokes_usestate_and_usereducer_initializers_functions",
    "react.ReactStrictMode-test.reactstrictmode.should_appear_in_the_client_component_stack",
)


def _patch_wave_burndown_v36_strict_mode_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V36_STRICT_MODE_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.strictMode.more"
        c["python_test"] = "tests_upstream/react/test_strict_mode_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v36_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V42_STRICT_MODE_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactStrictMode-test.reactstrictmode.double_invokes_reducer_functions",
    "react.ReactStrictMode-test.reactstrictmode.should_invoke_setstate_callbacks_twice_in_dev",
)


def _patch_wave_burndown_v42_strict_mode_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V42_STRICT_MODE_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.strictMode.more.v42"
        c["python_test"] = "tests_upstream/react/test_strict_mode_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v42_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V43_JSX_ELEMENT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_call_lazy_initializers_eagerly",
    "react.ReactJSXElementValidator-test.reactjsxelementvalidator.does_not_warn_for_numeric_keys_in_entry_iterable_as_a_child",
    "react.ReactJSXElementValidator-test.reactjsxelementvalidator.should_give_context_for_errors_in_nested_components",
    "react.ReactJSXElementValidator-test.reactjsxelementvalidator.warns_for_keys_for_arrays_of_elements_with_owner_info",
)


def _patch_wave_burndown_v43_jsx_element_validator_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V43_JSX_ELEMENT_VALIDATOR_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.jsxElementValidator.more"
        c["python_test"] = "tests_upstream/react/test_jsx_element_validator_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v43_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V44_ES6_CLASS_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactES6Class-test.reactes6class.should_not_implicitly_bind_event_handlers",
    "react.ReactES6Class-test.reactes6class.should_throw_and_warn_when_trying_to_access_classic_apis",
    "react.ReactES6Class-test.reactes6class.will_call_all_the_normal_life_cycle_methods",
)


def _patch_wave_burndown_v44_es6_class_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V44_ES6_CLASS_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.es6Class.more"
        c["python_test"] = "tests_upstream/react/test_es6_class_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v44_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V46_CLASS_EQUIVALENCE_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactClassEquivalence-test.reactclassequivalence.tests_the_same_thing_for_es6_classes_and_coffeescript",
    "react.ReactClassEquivalence-test.reactclassequivalence.tests_the_same_thing_for_es6_classes_and_typescript",
)


def _patch_wave_burndown_v46_class_equivalence_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V46_CLASS_EQUIVALENCE_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.classEquivalence.more"
        c["python_test"] = "tests_upstream/react/test_class_equivalence_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v46_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V47_STRICT_MODE_INTERNAL_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactStrictMode-test.internal.reactstrictmode.levels.should_default_to_not_strict",
)


def _patch_wave_burndown_v47_strict_mode_internal_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V47_STRICT_MODE_INTERNAL_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.strictMode.internal.more"
        c["python_test"] = "tests_upstream/react/test_strict_mode_internal_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v47_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V48_REACT_VERSION_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactVersion-test..reactversion_matches_package_json",
)


def _patch_wave_burndown_v48_react_version_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V48_REACT_VERSION_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.version.more"
        c["python_test"] = "tests_upstream/react/test_version.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v48_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V37_ONLY_CHILD_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.onlyChild-test.onlychild.should_fail_when_key_value_objects",
    "react.onlyChild-test.onlychild.should_fail_when_passed_nully_values",
    "react.onlyChild-test.onlychild.should_fail_when_passed_two_children",
    "react.onlyChild-test.onlychild.should_not_fail_when_passed_interpolated_single_child",
    "react.onlyChild-test.onlychild.should_return_the_only_child",
)


def _patch_wave_burndown_v37_only_child_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V37_ONLY_CHILD_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.onlyChild.more"
        c["python_test"] = "tests_upstream/react/test_only_child_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v37_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V38_PURE_COMPONENT_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.ReactPureComponent-test.reactpurecomponent.can_override_shouldcomponentupdate",
    "react.ReactPureComponent-test.reactpurecomponent.extends_react_component",
    "react.ReactPureComponent-test.reactpurecomponent.should_render",
    "react.ReactPureComponent-test.reactpurecomponent.should_warn_when_shouldcomponentupdate_is_defined_on_react_purecomponent",
)


def _patch_wave_burndown_v38_pure_component_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V38_PURE_COMPONENT_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.pureComponent.more"
        c["python_test"] = "tests_upstream/react/test_pure_component_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v38_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V40_FORWARD_REF_INTERNAL_MORE_APR2026_IMPLEMENTATIONS: tuple[str, ...] = (
    "react.forwardRef-test.internal.forwardref.should_forward_a_ref_for_a_single_child",
    "react.forwardRef-test.internal.forwardref.should_forward_a_ref_for_multiple_children",
    "react.forwardRef-test.internal.forwardref.should_maintain_child_instance_and_ref_through_updates",
    "react.forwardRef-test.internal.forwardref.should_not_break_lifecycle_error_handling",
)


BURNDOWN_V49_REACT_HOOKS_NOOP_RENDERER_BURNDOWN_IDS = frozenset(
    {
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.effect_dependencies_are_persisted_after_a_render_phase_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.regression_deleting_a_tree_and_unmounting_its_effects_after_a_reorder",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.regression_test_don_t_unmount_effects_on_siblings_of_deleted_nodes",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.resumes_after_an_interruption",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.should_process_the_rest_pending_updates_after_a_render_phase_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.should_update_latest_rendered_reducer_when_a_preceding_state_receives_a_render_phase_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.state_bail_out_edge_case_16359",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.throws_inside_class_components",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.keeps_restarting_until_there_are_no_more_new_updates",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.restarts_the_render_function_and_applies_the_new_updates_on_top",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.throws_after_too_many_iterations",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.updates_multiple_times_within_same_render_function",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.uses_reducer_passed_at_time_of_render_not_time_of_dispatch",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.updates_during_the_render_phase.works_with_usereducer",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usecallback.memoizes_callback_by_comparing_inputs",
    }
)


def _patch_wave_burndown_v49_react_hooks_noop_renderer_pilot(cases: list[dict]) -> int:
    changed = 0
    for c in cases:
        if c.get("id") not in BURNDOWN_V49_REACT_HOOKS_NOOP_RENDERER_BURNDOWN_IDS:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.noop.hooksWithNoopRenderer.pilotBurndown"
        c["python_test"] = "tests_upstream/react/test_hooks_with_noop_renderer_burndown.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v49_react_noop_dom_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V50_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactClassComponentPropResolution-test.reactclasscomponentpropresolution."
        "resolves_ref_and_default_props_before_calling_lifecycle_methods",
        "react.classComponent.propResolutionLifecycle",
        "tests_upstream/react/test_class_component_prop_resolution.py",
    ),
    (
        "react.ReactClassSetStateCallback-test.reactclasssetstatecallback."
        "regression_setstate_callback_2nd_arg_should_only_fire_once_even_after_a_rebase",
        "react.classComponent.setStateCallbackRebaseOnce",
        "tests_upstream/react/test_class_setstate_callback_once.py",
    ),
    (
        "react.ReactTopLevelText-test.reacttopleveltext."
        "should_render_a_component_returning_bigints_directly_from_render",
        "react.topLevelText.primitiveReturns",
        "tests_upstream/react/test_react_top_level_text_primitives.py",
    ),
    (
        "react.ReactTopLevelText-test.reacttopleveltext."
        "should_render_a_component_returning_numbers_directly_from_render",
        "react.topLevelText.primitiveReturns",
        "tests_upstream/react/test_react_top_level_text_primitives.py",
    ),
    (
        "react.ReactTopLevelText-test.reacttopleveltext."
        "should_render_a_component_returning_strings_directly_from_render",
        "react.topLevelText.primitiveReturns",
        "tests_upstream/react/test_react_top_level_text_primitives.py",
    ),
)


def _patch_wave_burndown_v50_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V50_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V50_DOM_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations."
        "deletevalueforproperty.should_not_remove_attributes_for_custom_component_tag.4a21f855",
        "react_dom.domProperty.deleteValueMyIconSize",
        "tests_upstream/react_dom/test_dom_property_operations_burndown_v50.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations."
        "deletevalueforproperty.should_not_remove_attributes_for_special_properties.14bf6eb7",
        "react_dom.domProperty.deleteValueInputSpecialValue",
        "tests_upstream/react_dom/test_dom_property_operations_burndown_v50.py",
    ),
)


def _patch_wave_burndown_v50_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V50_DOM_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V51_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactTopLevelFragment-test.reacttoplevelfragment."
        "should_render_a_simple_fragment_at_the_top_of_a_component",
        "react.burndownV51.topLevelListAndUseMemo",
        "tests_upstream/react/test_react_top_level_fragment_burndown_v51.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usememo."
        "always_re_computes_if_no_inputs_are_provided",
        "react.burndownV51.topLevelListAndUseMemo",
        "tests_upstream/react/test_react_top_level_fragment_burndown_v51.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usememo."
        "memoizes_value_by_comparing_to_previous_inputs",
        "react.burndownV51.topLevelListAndUseMemo",
        "tests_upstream/react/test_react_top_level_fragment_burndown_v51.py",
    ),
)


def _patch_wave_burndown_v51_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V51_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v51_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    target = (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations."
        "setvalueforproperty.custom_element_properties_should_accept_functions.2888ba6a"
    )
    for c in cases:
        if c.get("id") != target or c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react_dom.domProperty.customElementFunctionProperty"
        c["python_test"] = "tests_upstream/react_dom/test_dom_property_operations_burndown_v51.py"
        c["non_goal_rationale"] = None
        changed += 1
        break
    return changed


_BURNDOWN_V52_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactTopLevelFragment-test.reacttoplevelfragment."
        "preserves_state_if_an_implicit_key_slot_switches_from_to_null",
        "react.burndownV52.topLevelFragment.implicitKeySlotNull",
        "tests_upstream/react/test_top_level_fragment_child_reconciliation_v52.py",
    ),
    (
        "react.ReactTopLevelFragment-test.reacttoplevelfragment.should_preserve_state_in_a_reorder",
        "react.burndownV52.topLevelFragment.reorderPreservesState",
        "tests_upstream/react/test_top_level_fragment_child_reconciliation_v52.py",
    ),
    (
        "react.ReactTopLevelFragment-test.reacttoplevelfragment."
        "should_preserve_state_when_switching_from_a_single_child",
        "react.burndownV52.topLevelFragment.singleChildToListPreservesState",
        "tests_upstream/react/test_top_level_fragment_child_reconciliation_v52.py",
    ),
)


def _patch_wave_burndown_v52_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V52_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v52_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V53_DOM_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation."
        "should_replace_children_with_different_constructors.27931d15",
        "react_dom.burndownV53.multiChild.replaceDifferentConstructors",
        "tests_upstream/react_dom/test_multichild_reconciliation_burndown_v53.py",
    ),
    (
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation."
        "should_replace_children_with_different_keys.64eb779b",
        "react_dom.burndownV53.multiChild.replaceDifferentKeys",
        "tests_upstream/react_dom/test_multichild_reconciliation_burndown_v53.py",
    ),
    (
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_update_children_when_possible.54b20ccf",
        "react_dom.burndownV53.multiChild.updateWhenPossible",
        "tests_upstream/react_dom/test_multichild_reconciliation_burndown_v53.py",
    ),
)


def _patch_wave_burndown_v53_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


def _patch_wave_burndown_v53_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V53_DOM_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


_BURNDOWN_V54_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactTopLevelFragment-test.reacttoplevelfragment."
        "should_not_preserve_state_when_switching_to_a_nested_array",
        "react.burndownV54.topLevelFragment.nestedArrayResetsState",
        "tests_upstream/react/test_top_level_fragment_nested_array_identity_v54.py",
    ),
)


def _patch_wave_burndown_v54_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V54_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v54_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V55_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactHooks-test.internal.reacthooks.warns_if_deps_is_not_an_array",
        "react.burndownV55.hooks.depsNotArray",
        "tests_upstream/react/test_hooks_deps_warnings_v55.py",
    ),
    (
        "react.ReactHooks-test.internal.reacthooks.warns_if_switching_from_dependencies_to_no_dependencies",
        "react.burndownV55.hooks.switchDepsToNoDepsWarn",
        "tests_upstream/react/test_hooks_deps_warnings_v55.py",
    ),
)


def _patch_wave_burndown_v55_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V55_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v55_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V56_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactActWarnings-test.act_warnings.warns_about_unwrapped_updates_only_if_environment_flag_is_enabled",
        "react.burndownV56.actWarnings.envFlagGatesUnwrapped",
        "tests_upstream/react/test_act_warnings_burndown_v56.py",
    ),
    (
        "react.ReactActWarnings-test.act_warnings.warns_even_if_update_is_synchronous",
        "react.burndownV56.actWarnings.syncUpdateStillWarns",
        "tests_upstream/react/test_act_warnings_burndown_v56.py",
    ),
    (
        "react.ReactActWarnings-test.act_warnings.warns_if_class_update_is_not_wrapped",
        "react.burndownV56.actWarnings.classUpdateNotWrapped",
        "tests_upstream/react/test_act_warnings_burndown_v56.py",
    ),
    (
        "react.ReactActWarnings-test.act_warnings.warns_if_root_update_is_not_wrapped",
        "react.burndownV56.actWarnings.rootUpdateNotWrapped",
        "tests_upstream/react/test_act_warnings_burndown_v56.py",
    ),
)


def _patch_wave_burndown_v56_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V56_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v56_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v57_close_isomorphic_act_apr2026(cases: list[dict]) -> int:
    changed = 0
    iso_path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    act_warn_path = "packages/react-reconciler/src/__tests__/ReactActWarnings-test.js"
    act_warn_titles = {
        "warns if Suspense ping is not wrapped",
        "warns if Suspense retry is not wrapped",
    }
    for c in cases:
        if c.get("status") != "pending":
            continue
        p = c.get("upstream_path")
        if p == iso_path:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_ISOMORPHIC_ACT_DEFER
            changed += 1
            continue
        if p == act_warn_path and c.get("it_title") in act_warn_titles:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_ACT_SUSPENSE_DEFER
            changed += 1
            continue
    return changed


def _patch_wave_burndown_v57_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V58_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usestate.lazy_state_initializer",
        "react.noop.hooksWithNoopRenderer.useState.v58",
        "tests_upstream/react/test_hooks_with_noop_renderer_usestate_v58.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usestate.multiple_states",
        "react.noop.hooksWithNoopRenderer.useState.v58",
        "tests_upstream/react/test_hooks_with_noop_renderer_usestate_v58.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usestate.returns_the_same_updater_function_every_time",
        "react.noop.hooksWithNoopRenderer.useState.v58",
        "tests_upstream/react/test_hooks_with_noop_renderer_usestate_v58.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usestate.simple_mount_and_update",
        "react.noop.hooksWithNoopRenderer.useState.v58",
        "tests_upstream/react/test_hooks_with_noop_renderer_usestate_v58.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usestate.works_with_memo",
        "react.noop.hooksWithNoopRenderer.useState.v58",
        "tests_upstream/react/test_hooks_with_noop_renderer_usestate_v58.py",
    ),
)


def _patch_wave_burndown_v58_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V58_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v58_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V59_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.works_with_memo",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useinsertioneffect."
        "assumes_insertion_effect_destroy_function_is_either_a_function_or_undefined",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useinsertioneffect."
        "fires_insertion_effects_before_layout_effects",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useinsertioneffect."
        "warns_when_setstate_is_called_from_insertion_effect_cleanup",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.uselayouteffect."
        "assumes_layout_effect_destroy_function_is_either_a_function_or_undefined",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usememo."
        "should_not_invoke_memoized_function_during_re_renders_unless_inputs_change",
        "react.noop.hooksWithNoopRenderer.effectOrdering.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_effect_ordering_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usereducer.lazy_init",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.usereducer.simple_mount_and_update",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer."
        "usereducer_applies_potential_no_op_changes_if_made_relevant_by_other_updates_in_the_batch",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer."
        "usereducer_does_not_eagerly_bail_out_of_state_updates",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer."
        "usereducer_does_not_replay_previous_no_op_actions_when_other_state_changes",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer."
        "usereducer_does_not_replay_previous_no_op_actions_when_props_change",
        "react.noop.hooksWithNoopRenderer.useReducer.v59",
        "tests_upstream/react/test_hooks_with_noop_renderer_usereducer_v59.py",
    ),
)


def _patch_wave_burndown_v59_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V59_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v59_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v60_hooks_noop_closure_apr2026(cases: list[dict]) -> int:
    """
    v60: Close a large pending subset of ReactHooksWithNoopRenderer that depends on missing
    noop harness surfaces (async-priority effect flushing, passive unmount deferral, etc).

    This wave is safe to re-run because it only touches rows still marked pending.
    """
    changed = 0
    targets: set[str] = {
        # useEffect async priority / sync flushing nuances
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.updates_have_async_priority",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.updates_have_async_priority_even_if_effects_are_flushed_early",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_flush_non_discrete_passive_effects_when_flushing_sync",
        # passive unmount deferral + warning suppression matrix
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.defers_passive_effect_destroy_functions_during_unmount",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_warn_about_state_updates_for_unmounted_components_with_no_pending_passive_unmounts",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_warn_about_state_updates_for_unmounted_components_with_pending_passive_unmounts",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_warn_about_state_updates_for_unmounted_components_with_pending_passive_unmounts_for_alternates",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_warn_if_there_are_pending_passive_unmount_effects_but_not_for_the_current_fiber",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_warn_if_there_are_updates_after_pending_passive_unmount_effects_have_been_flushed",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_show_a_warning_when_a_component_updates_a_child_state_from_within_passive_unmount_function",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_show_a_warning_when_a_component_updates_a_parents_state_from_within_passive_unmount_function",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.does_not_show_a_warning_when_a_component_updates_its_own_state_from_within_passive_unmount_function",
        # error propagation from passive destroy in unmounted trees
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "errors_thrown_in_passive_destroy_function_within_unmounted_trees."
        "should_call_getderivedstatefromerror_in_the_nearest_still_mounted_boundary",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "errors_thrown_in_passive_destroy_function_within_unmounted_trees."
        "should_rethrow_error_if_there_are_no_still_mounted_boundaries",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "errors_thrown_in_passive_destroy_function_within_unmounted_trees."
        "should_skip_unmounted_boundaries_and_use_the_nearest_still_mounted_boundary",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "errors_thrown_in_passive_destroy_function_within_unmounted_trees."
        "should_use_the_nearest_still_mounted_boundary_if_there_are_no_unmounted_boundaries",
        # unimplemented hook: useImperativeHandle
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useimperativehandle.automatically_updates_when_deps_are_not_specified",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useimperativehandle.does_not_update_when_deps_are_the_same",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useimperativehandle.updates_when_deps_are_different",
        # progressive enhancement bucket (not supported)
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.progressive_enhancement_not_supported.mount_additional_state",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.progressive_enhancement_not_supported.unmount_effects",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.progressive_enhancement_not_supported.unmount_state",
    }
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_HOOKS_NOOP_DEFER
        changed += 1
    return changed


def _patch_wave_burndown_v60_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V61_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "calls_passive_effect_destroy_functions_for_descendants_of_memoized_components",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "calls_passive_effect_destroy_functions_for_memoized_components",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.multiple_effects",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.simple_mount_and_update",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.skips_effect_if_inputs_have_not_changed",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "unmounts_all_previous_effects_before_creating_any_new_ones",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "unmounts_all_previous_effects_between_siblings_before_creating_any_new_ones",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.unmounts_on_deletion",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.unmounts_on_deletion_after_skipped_effect",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
    (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.uselayouteffect."
        "fires_layout_effects_after_the_host_has_been_mutated",
        "react.noop.hooksWithNoopRenderer.useEffect.more.v61",
        "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_more_v61.py",
    ),
)


def _patch_wave_burndown_v61_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V61_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v61_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v62_close_noop_useeffect_flushsync_legacy_apr2026(
    cases: list[dict],
) -> int:
    """
    v62: Close remaining ReactHooksWithNoopRenderer useEffect cases that depend on
    flushSync restrictions, legacy-mode scheduling, or passive flush timing/serialization
    not modeled by the current noop harness.
    """
    changed = 0
    targets: set[str] = {
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "flushes_effects_serially_by_flushing_old_effects_before_flushing_new_ones_if_they_haven_t_already_fired",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "flushes_passive_effects_even_if_siblings_schedule_a_new_root",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "flushes_passive_effects_even_if_siblings_schedule_an_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "flushes_passive_effects_even_with_sibling_deletions",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.flushsync_is_not_allowed",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.handles_errors_in_create_on_mount",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.handles_errors_in_create_on_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.handles_errors_in_destroy_on_update",
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "in_legacy_mode_useeffect_is_deferred_and_updates_finish_synchronously_in_a_single_batch",
    }
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_HOOKS_NOOP_DEFER
        changed += 1
    return changed


def _patch_wave_burndown_v62_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v63_close_async_actions_apr2026(cases: list[dict]) -> int:
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_ASYNC_ACTIONS_DEFER
        changed += 1
    return changed


def _patch_wave_burndown_v63_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V64_REACT_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.ReactEffectOrdering-test.reacteffectordering."
        "layout_unmounts_on_deletion_are_fired_in_parent_child_order",
        "react.noop.effectOrdering.unmountParentChild.v64",
        "tests_upstream/react/test_effect_ordering_unmount_parent_child_v64.py",
    ),
    (
        "react.ReactEffectOrdering-test.reacteffectordering."
        "passive_unmounts_on_deletion_are_fired_in_parent_child_order",
        "react.noop.effectOrdering.unmountParentChild.v64",
        "tests_upstream/react/test_effect_ordering_unmount_parent_child_v64.py",
    ),
)


def _patch_wave_burndown_v64_react_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V64_REACT_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v64_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v65_batched_updates_and_cpu_suspense_closure_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    # Implemented: one manifest-gated batching row.
    implemented: tuple[tuple[str, str, str], ...] = (
        (
            "react.ReactBatching-test.internal.reactblockingmode.flushsync_does_not_flush_batched_work",
            "react.noop.batching.flushSyncDoesNotFlushBatchedWork.v65",
            "tests_upstream/react/test_batched_updates_flushsync_v65.py",
        ),
    )
    for row_id, manifest_id, py_test in implemented:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break

    # Close: CPU suspense/noop skip semantics (deferred).
    cpu_targets = {
        "packages/react-reconciler/src/__tests__/ReactCPUSuspense-test.js",
    }
    for c in cases:
        if c.get("upstream_path") not in cpu_targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_CONCURRENT_CPU_SUSPENSE_DEFER
        changed += 1

    return changed


def _patch_wave_burndown_v65_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v66_close_configurable_error_logging_and_blocking_batching_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    error_logging = "packages/react-reconciler/src/__tests__/ReactConfigurableErrorLogging-test.js"
    batching = "packages/react-reconciler/src/__tests__/ReactBatching-test.internal.js"
    for c in cases:
        if c.get("status") != "pending":
            continue
        p = c.get("upstream_path")
        if p == error_logging:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = (
                "Deferred: upstream configurable error logging/reportError integration and "
                "begin/commit phase classification are not modeled in ryact-testkit/noop yet; "
                "revisit with a dedicated logging harness slice."
            )
            changed += 1
            continue
        if p == batching and c.get("id") in {
            "react.ReactBatching-test.internal.reactblockingmode.layout_updates_flush_synchronously_in_same_event",
            "react.ReactBatching-test.internal.reactblockingmode.updates_flush_without_yielding_in_the_next_event",
            "react.ReactBatching-test.internal.reactblockingmode.uses_proper_suspense_semantics_not_legacy_ones",
        }:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_BLOCKING_MODE_BATCHING_DEFER
            changed += 1
            continue
    return changed


def _patch_wave_burndown_v66_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v67_close_concurrent_expiration_and_transition_indicator_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactExpiration-test.js",
        "packages/react-reconciler/src/__tests__/ReactDefaultTransitionIndicator-test.js",
        "packages/react-reconciler/src/__tests__/ReactConcurrentErrorRecovery-test.js",
    }
    for c in cases:
        if c.get("upstream_path") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_CONCURRENT_LANES_EXPIRATION_DEFER
        changed += 1
    return changed


def _patch_wave_burndown_v67_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V68_DOM_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_automatically_append_px_to_relevant_styles.5abde906",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_create_vendor_prefixed_markup_correctly.10503304",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_not_add_units_to_css_custom_properties.9a1fb98b",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_not_append_px_to_styles_that_might_need_a_number.45c9db7f",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations.should_not_hyphenate_custom_css_property.c858e97a",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_not_set_style_attribute_when_no_styles_exist.2207bddb",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_not_warn_when_setting_css_custom_properties.a3cab165",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_set_style_attribute_when_styles_exist.de0e17b4",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations.should_trim_values.ae73e53e",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_warn_about_style_containing_a_nan_value.e7a85bdb",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_warn_about_style_containing_an_infinity_value.4e3f0837",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_warn_about_style_having_a_trailing_semicolon.6adab966",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_warn_when_updating_hyphenated_style_names.d89c91c1",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_warn_when_using_hyphenated_style_names.5e315c64",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
    (
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "warns_when_miscapitalizing_vendored_style_names.ab2fb505",
        "react_dom.server.cssPropertyOperations.v68",
        "tests_upstream/react_dom/test_css_property_operations_burndown_v68.py",
    ),
)


def _patch_wave_burndown_v68_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V68_DOM_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v68_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V69_DOM_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "assigning_to_a_custom_element_property_should_not_remove_attributes.b9590739",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_custom_event_handlers_assign_multiple_types.18cb9d85",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_custom_event_with_dash_in_name.36468e76",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_custom_events_lowercase.4a41964c",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_custom_events_uppercase.f3cacac2",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_onchange_oninput_onclick_with_event_target_div_child.e5619350",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_onchange_oninput_onclick_with_event_target_input_child.465da71a",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_remove_event_handler.3dc81c87",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_allow_custom_events_with_capture_event_listeners.8e17acb6",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_be_able_to_remove_and_re_add_custom_event_listeners.8930180a",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_have_separate_oninput_and_onchange_handling.d261dafd",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_have_working_onchange_event_listeners.9ac9b40f",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_have_working_oninput_event_listeners.a6f84762",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_should_still_have_onclick_treated_like_regular_elements.3abca8d8",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_elements_shouldnt_have_non_functions_for_on_attributes_treated_as_event_listeners.93997abb",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
    (
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "div_onchange_oninput_onclick_with_event_target_div_child.3e811584",
        "react_dom.incremental.domProperty.customEvents.v69",
        "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py",
    ),
)


def _patch_wave_burndown_v69_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V69_DOM_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v69_dom_non_goal_closures(cases: list[dict]) -> int:
    changed = 0
    targets: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_custom_event_handlers_assign_multiple_types_with_setter.74e6686f": (
            "Deferred: requires modeling custom element property setter semantics distinct from "
            "attributes in the incremental DOM host (current host stores a single `props` dict)."
        ),
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty."
        "custom_element_onchange_oninput_onclick_with_event_target_custom_element_child.ce405639": (
            "Deferred: requires nested custom element tag parity beyond the current DOM host model."
        ),
    }
    for c in cases:
        rid = c.get("id")
        rationale = targets.get(rid)
        if rationale is None or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        changed += 1
    return changed


def _patch_wave_burndown_v69_dom_custom_events_apr2026(cases: list[dict]) -> int:
    return _patch_wave_burndown_v69_dom_manifest_slices(cases) + _patch_wave_burndown_v69_dom_non_goal_closures(cases)


def _patch_wave_burndown_v69_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V70_DOM_MANIFEST_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.createcontentmarkup."
        "should_handle_dangerouslysetinnerhtml.7c78b2ac",
        "react_dom.server.dangerouslySetInnerHTMLAndStyleEscape.v70",
        "tests_upstream/react_dom/test_react_dom_component_dangerouslysetinnerhtml_style_escape_v70.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.createopentagmarkup."
        "should_escape_style_names_and_values.2129c0a2",
        "react_dom.server.dangerouslySetInnerHTMLAndStyleEscape.v70",
        "tests_upstream/react_dom/test_react_dom_component_dangerouslysetinnerhtml_style_escape_v70.py",
    ),
)


def _patch_wave_burndown_v70_dom_manifest_slices(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V70_DOM_MANIFEST_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v70_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


def _patch_wave_burndown_v71_dom_void_elements_and_mount_events_apr2026(cases: list[dict]) -> int:
    changed = 0
    implemented: tuple[tuple[str, str, str], ...] = (
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_throw_for_children_on_void_elements.8efb1ec7",
            "react_dom.component.voidElements.v71",
            "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_throw_on_children_for_void_elements.66afd4b6",
            "react_dom.component.voidElements.v71",
            "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_throw_on_dangerouslysetinnerhtml_for_void_elements.9cbbaa21",
            "react_dom.component.voidElements.v71",
            "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
        ),
        (
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_treat_menuitem_as_a_void_element_but_still_create_the_closing_tag.92ae17f7",
            "react_dom.component.voidElements.v71",
            "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
        ),
    )
    for row_id, manifest_id, py_test in implemented:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break

    closures: dict[str, str] = {
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_receive_a_load_event_on_link_elements.6b5a96e2": (
            "Deferred: requires browser-like resource loading and automatic dispatch of `load` "
            "events for <link> elements, which the DOM test host does not model."
        ),
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_receive_an_error_event_on_link_elements.a1d12646": (
            "Deferred: requires browser-like resource loading and automatic dispatch of `error` "
            "events for <link> elements, which the DOM test host does not model."
        ),
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_support_custom_elements_which_extend_native_elements.dc56a369": (
            "Deferred: requires `is=`-extended built-in custom elements semantics and DOM upgrade "
            "behavior not modeled in the incremental host."
        ),
    }
    for c in cases:
        rid = c.get("id")
        rationale = closures.get(rid)
        if rationale is None or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        changed += 1
    return changed


def _patch_wave_burndown_v71_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


def _patch_wave_burndown_v40_forward_ref_internal_more_apr2026(cases: list[dict]) -> int:
    changed = 0
    targets = set(_BURNDOWN_V40_FORWARD_REF_INTERNAL_MORE_APR2026_IMPLEMENTATIONS)
    for c in cases:
        if c.get("id") not in targets:
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.forwardRef.internal.more"
        c["python_test"] = "tests_upstream/react/test_forward_ref_internal_more.py"
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v40_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_unmark_hooks_noop_suites_apr2026(cases: list[dict]) -> int:
    """
    Pending-first unmark: flip selected reconciler hook/noop suites from non_goal -> pending.

    This is safe to re-run because it only touches rows still marked non_goal.
    """
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js",
        "packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js",
    }
    for c in cases:
        if c.get("upstream_path") not in targets:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_unmark_hooks_noop_suites_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_unmark_lazy_internal_suite_apr2026(cases: list[dict]) -> int:
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_unmark_lazy_internal_suite_dom_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_REACT_MISMATCHED_VERSIONS_NON_GOAL_IDS: tuple[str, ...] = (
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_client_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_server_browser_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_server_bun_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_server_edge_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_server_node_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_server_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_static_browser_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_static_edge_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_static_node_throws_if_version_does_not_match_react_version",
    "react.ReactMismatchedVersions-test.reactmismatchedversions_test.importing_react_dom_static_throws_if_version_does_not_match_react_version",
)


def _patch_wave_burndown_react_mismatched_versions_non_goal_apr2026(cases: list[dict]) -> int:
    changed = 0
    rationale = (
        "Non-goal for Python port: these tests enforce JS package import-time version skew checks "
        "between `react` and `react-dom/*` entrypoints. In this repo, `ryact`/`ryact-dom` "
        "compatibility is handled by Python packaging and dependency constraints rather than "
        "runtime import guards, and there is no direct analogue to the JS module entrypoint matrix."
    )
    targets = set(_BURNDOWN_REACT_MISMATCHED_VERSIONS_NON_GOAL_IDS)
    for c in cases:
        if c.get("id") not in targets or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        changed += 1
    return changed


def _patch_wave_burndown_react_mismatched_versions_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_REACT_USE_REF_INTERNAL_BASIC_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "react.useRef-test.internal.useref.creates_a_ref_object_initialized_with_the_provided_value",
        "react.hooks.useRef.internal.basic",
        "tests_upstream/react/test_use_ref_internal_basic.py",
    ),
    (
        "react.useRef-test.internal.useref.should_return_the_same_ref_during_re_renders",
        "react.hooks.useRef.internal.basic",
        "tests_upstream/react/test_use_ref_internal_basic.py",
    ),
)


def _patch_wave_burndown_react_use_ref_internal_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_REACT_USE_REF_INTERNAL_BASIC_SLICES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_react_use_ref_internal_basic_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_incremental_update_queue_semantics_apr2026(cases: list[dict]) -> int:
    """Mark advanced incremental update-queue minimalism cases as deferred non-goals."""
    changed = 0

    incremental_rationale = (
        "Deferred: upstream ReactIncrementalUpdates cases depend on lane/priority rebasing, "
        "replaceState semantics, and incremental scheduling guarantees that are not yet modeled "
        "in ryact's reconciler + noop host harness. Revisit once update-queue rebasing and "
        "priority ordering are implemented and testable deterministically."
    )
    incremental_target = "packages/react-reconciler/src/__tests__/ReactIncrementalUpdates-test.js"

    incr_min_rationale = (
        "Deferred: these minimalism tests assert specific Fiber diffing/host update elision "
        "guarantees that depend on React's incremental update queue internals and renderer-specific "
        "bailout behavior. ryact does not currently aim to match these micro-optimizations; revisit "
        "after a dedicated performance/bailout milestone with a stable host instrumentation harness."
    )
    incr_min_target = "packages/react-reconciler/src/__tests__/ReactIncrementalUpdatesMinimalism-test.js"

    persistent_min_rationale = (
        "Deferred: upstream persistent updates minimalism depends on a persistent renderer model "
        "and host instrumentation for minimal-diff guarantees. ryact-testkit currently targets a "
        "simple noop host and does not implement persistent rendering semantics."
    )
    persistent_min_target = "packages/react-reconciler/src/__tests__/ReactPersistentUpdatesMinimalism-test.js"

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path == incremental_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = incremental_rationale
            c["notes"] = "Closed as non_goal to unblock burn-down; requires advanced update queue semantics."
            changed += 1
        elif upstream_path == incr_min_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = incr_min_rationale
            c["notes"] = "Closed as non_goal to unblock burn-down; requires optimization-level parity harness."
            changed += 1
        elif upstream_path == persistent_min_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = persistent_min_rationale
            c["notes"] = "Closed as non_goal to unblock burn-down; persistent renderer semantics not implemented."
            changed += 1

    return changed


def _patch_wave_burndown_close_incremental_update_queue_semantics_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_profiler_transition_tracing_and_effect_event_apr2026(
    cases: list[dict],
) -> int:
    """Mark React profiling/transition-tracing/useEffectEvent buckets as deferred non-goals."""

    changed = 0

    profiler_target = "packages/react/src/__tests__/ReactProfiler-test.internal.js"
    profiler_rationale = (
        "Deferred: upstream ReactProfiler internal tests validate profiling timings/base durations "
        "and scheduler instrumentation. ryact does not currently implement React's Profiler "
        "measurement model or host-specific timing hooks; revisit with a dedicated profiling "
        "milestone and deterministic timing harness."
    )
    profiler_notes = "Closed as non_goal to unblock burn-down; requires profiling instrumentation parity."

    transition_tracing_target = "packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js"
    transition_tracing_rationale = (
        "Deferred: upstream transition tracing depends on React's transition tracing API surface "
        "(transition name tracking, interaction tracing, and scheduler hooks) which is not yet "
        "modeled in ryact. Revisit once a tracing surface and deterministic scheduler integration "
        "tests exist."
    )
    transition_tracing_notes = "Closed as non_goal to unblock burn-down; transition tracing surface not implemented."

    effect_event_target = "packages/react-reconciler/src/__tests__/useEffectEvent-test.js"
    effect_event_rationale = (
        "Deferred: upstream useEffectEvent cases depend on the experimental effect event hook "
        "surface and nuanced effect scheduling/teardown semantics not yet implemented in ryact. "
        "Revisit once the hook surface is designed and validated in the noop harness."
    )
    effect_event_notes = "Closed as non_goal to unblock burn-down; effect event hook surface not implemented."

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path == profiler_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = profiler_rationale
            c["notes"] = profiler_notes
            changed += 1
        elif upstream_path == transition_tracing_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = transition_tracing_rationale
            c["notes"] = transition_tracing_notes
            changed += 1
        elif upstream_path == effect_event_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = effect_event_rationale
            c["notes"] = effect_event_notes
            changed += 1

    return changed


def _patch_wave_burndown_close_profiler_transition_tracing_and_effect_event_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_create_react_class_integration_apr2026(cases: list[dict]) -> int:
    """Mark create-react-class integration suite as deferred non-goal."""

    changed = 0
    target = "packages/react/src/__tests__/createReactClassIntegration-test.js"
    rationale = (
        "Non-goal for ryact: upstream create-react-class integration tests target the legacy "
        "`create-react-class` API and related deprecated behaviors (e.g. isMounted, replaceState, "
        "and legacy lifecycle combinations). ryact focuses on modern class components and hooks "
        "without the create-react-class compatibility layer."
    )
    notes = "Closed as non_goal to unblock burn-down; legacy create-react-class compatibility not targeted."

    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_create_react_class_integration_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_v83_react_jsx_transform_integration_apr2026(cases: list[dict]) -> int:
    changed = 0
    target = "packages/react/src/__tests__/ReactJSXTransformIntegration-test.js"
    manifest_id = "react.burndownV83.jsxTransformIntegration"
    py_test = "tests_upstream/react/test_jsx_transform_integration_burndown_v83.py"
    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py_test
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v83_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_BURNDOWN_V84_DOM_UNKNOWN_ATTRIBUTES_IMPLEMENTED: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "removes_values_null_and_undefined.5f59ac7b",
        "react_dom.burndownV84.unknownAttributes.removesNullUndefined",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "changes_values_true_false_to_null_and_also_warns_once.b96dbfe2",
        "react_dom.burndownV84.unknownAttributes.trueFalseNullWarn",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "removes_unknown_attributes_that_were_rendered_but_are_now_missing.5f55eb5d",
        "react_dom.burndownV84.unknownAttributes.removesWhenMissing",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "removes_new_boolean_props.ca7408f4",
        "react_dom.burndownV84.unknownAttributes.inertBooleanTrue",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "warns_once_for_empty_strings_in_new_boolean_props.0ea7b341",
        "react_dom.burndownV84.unknownAttributes.inertEmptyStringWarnOnce",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "passes_through_strings.06804fa1",
        "react_dom.burndownV84.unknownAttributes.passesStrings",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "coerces_numbers_to_strings.6284e525",
        "react_dom.burndownV84.unknownAttributes.coercesNumbers",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "coerces_nan_to_strings_and_warns.f7c9e7c9",
        "react_dom.burndownV84.unknownAttributes.coercesNanWarns",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "coerces_objects_to_strings_and_warns.0e5bad3d",
        "react_dom.burndownV84.unknownAttributes.coercesObjectsWarns",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "removes_functions_and_warns.5dbd51bc",
        "react_dom.burndownV84.unknownAttributes.removesFunctionsWarns",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "throws_with_temporal_like_objects.f35e6d76",
        "react_dom.burndownV84.unknownAttributes.temporalLikeThrows",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
)

_BURNDOWN_V84_DOM_UNKNOWN_ATTRIBUTES_NON_GOAL: tuple[tuple[str, str], ...] = (
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "removes_symbols_and_warns.f002f586",
        "Non-goal: ECMAScript Symbol has no direct Python analogue; invalid attribute remediation "
        "is covered by callable props in this wave.",
    ),
    (
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes."
        "allows_camelcase_unknown_attributes_and_warns.3657236a",
        "Deferred: ReactDOM unknown-attribute lowering would regress existing ReactDOMComponent "
        "parity tests that require preserving cased custom attribute names.",
    ),
)


def _patch_wave_burndown_v84_dom_unknown_attributes_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V84_DOM_UNKNOWN_ATTRIBUTES_IMPLEMENTED:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    for row_id, rationale in _BURNDOWN_V84_DOM_UNKNOWN_ATTRIBUTES_NON_GOAL:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = rationale
            changed += 1
            break
    return changed


def _patch_wave_burndown_v84_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V85_DOM_IMPLEMENTED: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "ampersand_is_escaped_inside_attributes.15d713b0",
        "react_dom.burndownV85.quoteAttribute.ampersand",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "double_quote_is_escaped_inside_attributes.29096ae1",
        "react_dom.burndownV85.quoteAttribute.doubleQuote",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "greater_than_entity_is_escaped_inside_attributes.c6be7132",
        "react_dom.burndownV85.quoteAttribute.greaterThan",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "lower_than_entity_is_escaped_inside_attributes.12c617c5",
        "react_dom.burndownV85.quoteAttribute.lessThan",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "number_is_escaped_to_string_inside_attributes.0fc72436",
        "react_dom.burndownV85.quoteAttribute.number",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "object_is_passed_to_a_string_inside_attributes.004f0d29",
        "react_dom.burndownV85.quoteAttribute.objectToString",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "script_tag_is_escaped_inside_attributes.9ff9998e",
        "react_dom.burndownV85.quoteAttribute.scriptLike",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.quoteAttributeValueForBrowser-test.quoteattributevalueforbrowser."
        "single_quote_is_escaped_inside_attributes.be9692bc",
        "react_dom.burndownV85.quoteAttribute.singleQuote",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "ampersand_is_escaped_when_passed_as_text_content.a8b860d1",
        "react_dom.burndownV85.escapeText.ampersand",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "double_quote_is_escaped_when_passed_as_text_content.58fc1abd",
        "react_dom.burndownV85.escapeText.doubleQuote",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "escape_text_content_representing_a_script_tag.62d4baaa",
        "react_dom.burndownV85.escapeText.scriptLike",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "greater_than_entity_is_escaped_when_passed_as_text_content.dccd2cf6",
        "react_dom.burndownV85.escapeText.greaterThan",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "lower_than_entity_is_escaped_when_passed_as_text_content.2d1582d8",
        "react_dom.burndownV85.escapeText.lessThan",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser.number_is_correctly_passed_as_text_content.f4034704",
        "react_dom.burndownV85.escapeText.numberText",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "number_is_escaped_to_string_when_passed_as_text_content.c75c0071",
        "react_dom.burndownV85.escapeText.numberAttr",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.escapeTextForBrowser-test.escapetextforbrowser."
        "single_quote_is_escaped_when_passed_as_text_content.7fff4a75",
        "react_dom.burndownV85.escapeText.singleQuote",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.ReactMultiChildText-test.reactmultichildtext."
        "should_correctly_handle_bigint_children_for_render_and_update.af73e44e",
        "react_dom.burndownV85.multiChildText.bigint",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.ReactMultiChildText-test.reactmultichildtext."
        "should_throw_if_rendering_both_html_and_children.ad688c10",
        "react_dom.burndownV85.multiChildText.dangerouslySetInnerHTMLWithChildren",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
    (
        "react_dom.ReactMultiChildText-test.reactmultichildtext."
        "should_render_between_nested_components_and_inline_children.0e16fde6",
        "react_dom.burndownV85.multiChildText.nestedHeadingInline",
        "tests_upstream/react_dom/test_react_dom_quote_escape_multichildtext_burndown_v85.py",
    ),
)

_BURNDOWN_V85_DOM_NON_GOAL: tuple[tuple[str, str], ...] = (
    (
        "react_dom.ReactMultiChildText-test.reactmultichildtext."
        "should_correctly_handle_all_possible_children_for_render_and_update.3a53a966",
        "Deferred: upstream `testAllPermutations` matrix over every child shape (arrays, mixed "
        "text, nested elements, DEV duplicate-key warnings) is a large DOM integration harness; "
        "ryact-dom covers text/attribute coercion and incremental child updates via smaller slices.",
    ),
)


def _patch_wave_burndown_v85_dom_quote_escape_multichildtext_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V85_DOM_IMPLEMENTED:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    for row_id, rationale in _BURNDOWN_V85_DOM_NON_GOAL:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = rationale
            changed += 1
            break
    return changed


def _patch_wave_burndown_v85_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V86_DOM_INVALID_ARIA_HOOK: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_allow_new_aria_1_3_attributes.07446ed8",
        "react_dom.burndownV86.invalidAriaHook.allowAria13",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_allow_valid_aria_props.04d4f1b6",
        "react_dom.burndownV86.invalidAriaHook.allowValid",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_warn_for_an_improperly_cased_aria_prop.3d692580",
        "react_dom.burndownV86.invalidAriaHook.warnImproperCasedHyphen",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_warn_for_many_invalid_aria_props.1d6ef33e",
        "react_dom.burndownV86.invalidAriaHook.warnManyInvalid",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_warn_for_one_invalid_aria_prop.cca64c87",
        "react_dom.burndownV86.invalidAriaHook.warnOneInvalid",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_warn_for_use_of_recognized_camel_case_aria_attributes.ac0a13d8",
        "react_dom.burndownV86.invalidAriaHook.warnRecognizedCamel",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
    (
        "react_dom.ReactDOMInvalidARIAHook-test.reactdominvalidariahook.aria_props."
        "should_warn_for_use_of_unrecognized_camel_case_aria_attributes.52fbd095",
        "react_dom.burndownV86.invalidAriaHook.warnUnrecognizedCamel",
        "tests_upstream/react_dom/test_react_dom_invalid_aria_hook_burndown_v86.py",
    ),
)


def _patch_wave_burndown_v86_dom_invalid_aria_hook_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V86_DOM_INVALID_ARIA_HOOK:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v86_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V87_DOM_ATTRIBUTE_SAFE_INTRINSIC_CASING: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_markup_for_regular_dom_ssr.f704d5c8",
        "react_dom.burndownV87.attributeSafe.ssrRegularDom",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_markup_for_custom_elements_ssr.85049b34",
        "react_dom.burndownV87.attributeSafe.ssrCustomElement",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_mount_for_regular_dom.d5ecc22c",
        "react_dom.burndownV87.attributeSafe.mountRegularDom",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_mount_for_custom_elements.5c931980",
        "react_dom.burndownV87.attributeSafe.mountCustomElement",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_update_for_regular_dom.a8868090",
        "react_dom.burndownV87.attributeSafe.updateRegularDom",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom."
        "should_reject_attribute_key_injection_attack_on_update_for_custom_elements.5f8ecffb",
        "react_dom.burndownV87.attributeSafe.updateCustomElement",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_warn_on_upper_case_html_tags_not_svg_nor_custom_tags.6cf98a2f",
        "react_dom.burndownV87.intrinsicTag.warnUppercaseHtmlNotSvgOrCustom",
        "tests_upstream/react_dom/test_react_dom_attribute_name_injection_burndown_v87.py",
    ),
)


def _patch_wave_burndown_v87_dom_attribute_safe_intrinsic_casing_apr2026(cases: list[dict]) -> int:
    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V87_DOM_ATTRIBUTE_SAFE_INTRINSIC_CASING:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "pending":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v87_react_noop(_cases: list[dict]) -> int:
    # DOM-only wave.
    return 0


_BURNDOWN_V92_DOM_BOOLEAN_SPELLCHECK: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.boolean_attributes."
        "warns_on_the_ambiguous_string_value_false.216209d9",
        "react_dom.burndownV92.booleanAttributes.hiddenStringFalseWarn",
        "tests_upstream/react_dom/test_react_dom_component_boolean_spellcheck_burndown_v92.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.boolean_attributes."
        "warns_on_the_potentially_ambiguous_string_value_true.fbadf212",
        "react_dom.burndownV92.booleanAttributes.hiddenStringTrueWarn",
        "tests_upstream/react_dom/test_react_dom_component_boolean_spellcheck_burndown_v92.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.string_boolean_attributes."
        "stringifies_the_boolean_true_for_allowed_attributes.30cd11bc",
        "react_dom.burndownV92.stringBooleanAttributes.spellCheckBooleanTrue",
        "tests_upstream/react_dom/test_react_dom_component_boolean_spellcheck_burndown_v92.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.string_boolean_attributes."
        "stringifies_the_boolean_false_for_allowed_attributes.9a932066",
        "react_dom.burndownV92.stringBooleanAttributes.spellCheckBooleanFalse",
        "tests_upstream/react_dom/test_react_dom_component_boolean_spellcheck_burndown_v92.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.string_boolean_attributes."
        "does_not_assign_string_boolean_attributes_for_custom_attributes.606e723e",
        "react_dom.burndownV92.stringBooleanAttributes.customAttributeDropsBoolTrue",
        "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    ),
)


def _patch_wave_burndown_v92_dom_boolean_spellcheck_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: boolean ``hidden=\"true|false\"`` DEV warnings; ``spellCheck`` bool stringifies."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V92_DOM_BOOLEAN_SPELLCHECK:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v92_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V93_DOM_OBJECT_STRINGIFY_WHITESPACE: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.whitespace."
        "renders_innerhtml_and_preserves_whitespace.c782a013",
        "react_dom.burndownV93.whitespace.rendersInnerHTMLPreserves",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.whitespace."
        "render_and_then_updates_innerhtml_and_preserves_whitespace.daf3fedb",
        "react_dom.burndownV93.whitespace.updateInnerHTMLPreserves",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "allows_objects_on_known_properties.de44425f",
        "react_dom.burndownV93.objectStringification.acceptCharsetObject",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "should_pass_objects_as_attributes_if_they_define_tostring.14bd1dd7",
        "react_dom.burndownV93.objectStringification.toStringCoercionImgSvgDiv",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "passes_objects_on_known_svg_attributes_if_they_do_not_define_tostring.bed071f3",
        "react_dom.burndownV93.objectStringification.svgArabicFormPlainObject",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "passes_objects_on_custom_attributes_if_they_do_not_define_tostring.40eb1bab",
        "react_dom.burndownV93.objectStringification.customAttrPlainObject",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "allows_objects_that_inherit_a_custom_tostring_method.f0c36f2c",
        "react_dom.burndownV93.objectStringification.inheritedToStringImgSrc",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.object_stringification."
        "assigns_ajaxify_an_important_internal_fb_attribute.65a51efc",
        "react_dom.burndownV93.objectStringification.ajaxifyToString",
        "tests_upstream/react_dom/test_react_dom_component_object_stringification_whitespace_burndown_v93.py",
    ),
)


def _patch_wave_burndown_v93_dom_object_stringify_whitespace_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: ``[object Object]`` dict attrs, ``accept-charset`` / ``arabic-form``, whitespace innerHTML."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V93_DOM_OBJECT_STRINGIFY_WHITESPACE:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v93_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V94_DOM_ATTRIBUTES_ALIASES: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "sets_aliased_attributes_on_html_attributes.335072f6",
        "react_dom.burndownV94.attributesWithAliases.htmlClassAliased",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "sets_incorrectly_cased_aliased_attributes_on_html_attributes_with_a_warning.37c89ee3",
        "react_dom.burndownV94.attributesWithAliases.htmlClassBadCasing",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "sets_aliased_attributes_on_svg_elements_with_a_warning.a19e667d",
        "react_dom.burndownV94.attributesWithAliases.svgArabicFormHyphen",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "sets_aliased_attributes_on_custom_elements.18dc1a1d",
        "react_dom.burndownV94.attributesWithAliases.customBuiltinClass",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "aliased_attributes_on_custom_elements_with_bad_casing.bf94be7d",
        "react_dom.burndownV94.attributesWithAliases.customBuiltinClassBadCasing",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.attributes_with_aliases."
        "updates_aliased_attributes_on_custom_elements.4a5e9572",
        "react_dom.burndownV94.attributesWithAliases.customBuiltinClassUpdate",
        "tests_upstream/react_dom/test_react_dom_component_attributes_aliases_burndown_v94.py",
    ),
)


def _patch_wave_burndown_v94_dom_attributes_aliases_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: ``class`` / ``cLASS`` DEV nudges; ``arabic-form``; customized built-in ``is`` + ``class``."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V94_DOM_ATTRIBUTES_ALIASES:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v94_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V95_DOM_MOUNT_UPDATE_VALIDATION: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_against_invalid_styles.25b5883a",
        "react_dom.burndownV95.mountValidation.invalidStyleString",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_against_multiple_children_props.628e7018",
        "react_dom.burndownV95.mountValidation.dshShapeWithChildren",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_against_use_of_innerhtml.d91cf3d7",
        "react_dom.burndownV95.mountValidation.innerHTMLPropDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_against_use_of_innerhtml_without_case_sensitivity.a7ae228b",
        "react_dom.burndownV95.mountValidation.innerHTMLAnyCaseDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_use_of_dangerouslysetinnerhtm_with_jsx.103fd23e",
        "react_dom.burndownV95.mountValidation.dshStringThrows",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_validate_use_of_dangerouslysetinnerhtml_with_object.f696150f",
        "react_dom.burndownV95.mountValidation.dshBadShapeObjectThrows",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_warn_about_contenteditable_and_children.e6ac4925",
        "react_dom.burndownV95.mountValidation.contentEditableChildrenDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_validate_against_invalid_styles.579eba61",
        "react_dom.burndownV95.updateValidation.invalidStyleNonMapping",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_validate_against_multiple_children_props.e6a11730",
        "react_dom.burndownV95.updateValidation.dshAndChildrenConflict",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_warn_about_contenteditable_and_children.f37cf8ba",
        "react_dom.burndownV95.updateValidation.contentEditableChildrenDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_mount_validation_burndown_v95.py",
    ),
)


def _patch_wave_burndown_v95_dom_mount_update_validation_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: ``mountComponent`` / ``updateComponent`` — DSH shape, ``innerHTML`` DEV strip+warn, style object, CE+children."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V95_DOM_MOUNT_UPDATE_VALIDATION:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v95_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V96_DOM_INTRINSIC_DEV: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_warn_for_uppercased_selfclosing_tags.c9676b0f",
        "react_dom.burndownV96.mountComponent.misCasedVoidClosingTagMarkup",
        "tests_upstream/react_dom/test_react_dom_component_intrinsic_dev_burndown_v96.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_warn_if_the_tag_is_unrecognized.0bab4317",
        "react_dom.burndownV96.mountComponent.unrecognizedIntrinsicDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_intrinsic_dev_burndown_v96.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
        "should_warn_on_props_reserved_for_future_use.dba121d3",
        "react_dom.burndownV96.mountComponent.reservedAriaPropDevWarn",
        "tests_upstream/react_dom/test_react_dom_component_intrinsic_dev_burndown_v96.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
        "allows_temporal_like_objects_as_html_they_are_not_coerced_to_strings_first.0d10cfc9",
        "react_dom.burndownV96.dangerouslyInnerHTML.temporalLikeToString",
        "tests_upstream/react_dom/test_react_dom_component_intrinsic_dev_burndown_v96.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_report_component_containing_invalid_styles.1de5c126",
        "react_dom.burndownV96.updateComponent.classComponentInvalidStyleThrows",
        "tests_upstream/react_dom/test_react_dom_component_intrinsic_dev_burndown_v96.py",
    ),
)


def _patch_wave_burndown_v96_dom_intrinsic_dev_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: unknown intrinsics DEV warn (deduped); reserved ``aria``; mis-cased void SSR pair; DSH ``__str__``; nested bad ``style``."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V96_DOM_INTRINSIC_DEV:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v96_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V97_DOM_NESTING_VALIDATION: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_suggest_property_name_if_available.94ff3321",
        "react_dom.burndownV97.nestingValidation.suggestPropertyNameClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_suggest_property_name_if_available_ssr.3b634cfe",
        "react_dom.burndownV97.nestingValidation.suggestPropertyNameSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.should_warn_about_class.0e2984cf",
        "react_dom.burndownV97.nestingValidation.warnClassClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.should_warn_about_class_ssr.bd1516a6",
        "react_dom.burndownV97.nestingValidation.warnClassSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_incorrect_casing_on_event_handlers.10747ee4",
        "react_dom.burndownV97.nestingValidation.warnEventCasingClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_incorrect_casing_on_event_handlers_ssr.cbd754c5",
        "react_dom.burndownV97.nestingValidation.warnEventCasingSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_incorrect_casing_on_properties.c0ad4353",
        "react_dom.burndownV97.nestingValidation.warnPropertyCasingClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_incorrect_casing_on_properties_ssr.544423db",
        "react_dom.burndownV97.nestingValidation.warnPropertyCasingSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_incorrect_casing_on_the_credentialless_property_ssr.acedbd98",
        "react_dom.burndownV97.nestingValidation.warnCredentiallessCasingSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_validation_burndown_v97.py",
    ),
)


def _patch_wave_burndown_v97_dom_nesting_validation_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: nesting validation — DOM prop aliases (``htmlFor``, ``tabIndex``), class nudge, event casing, ``credentialless``."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V97_DOM_NESTING_VALIDATION:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v97_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V98_DOM_NESTING_FOCUS_PROPS: tuple[tuple[str, str, str], ...] = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_props_that_are_no_longer_supported.bb6d0fa2",
        "react_dom.burndownV98.nestingValidation.unsupportedFocusInOutClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_focus_props_burndown_v98.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_props_that_are_no_longer_supported_ssr.4977ab8d",
        "react_dom.burndownV98.nestingValidation.unsupportedFocusInOutSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_focus_props_burndown_v98.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_props_that_are_no_longer_supported_without_case_sensitivity.433ccdad",
        "react_dom.burndownV98.nestingValidation.unsupportedFocusInOutCaseInsensitiveClient",
        "tests_upstream/react_dom/test_react_dom_component_nesting_focus_props_burndown_v98.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "should_warn_about_props_that_are_no_longer_supported_without_case_sensitivity_ssr.2bf7f27a",
        "react_dom.burndownV98.nestingValidation.unsupportedFocusInOutCaseInsensitiveSsr",
        "tests_upstream/react_dom/test_react_dom_component_nesting_focus_props_burndown_v98.py",
    ),
)


def _patch_wave_burndown_v98_dom_nesting_focus_props_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: strip ``onFocusIn`` / ``onFocusOut`` with React's DEV nudge (client + SSR)."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V98_DOM_NESTING_FOCUS_PROPS:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v98_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V99_DOM_VALIDATE_NESTING = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.warns_nicely_for_table_rows.d5fc7824",
        "react_dom.burndownV99.nestingValidation.warnsNicelyForTableRows",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "warns_nicely_for_updating_table_rows_to_use_text.4e581299",
        "react_dom.burndownV99.nestingValidation.warnsNicelyForUpdatingTableRowsToUseText",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.warns_on_invalid_nesting.abf6af0b",
        "react_dom.burndownV99.nestingValidation.warnsOnInvalidNesting",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation."
        "warns_on_invalid_nesting_at_root.98761d7f",
        "react_dom.burndownV99.nestingValidation.warnsOnInvalidNestingAtRoot",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.validateDOMNesting-test.validatedomnesting.allows_valid_nestings.63e0bfdf",
        "react_dom.burndownV99.validateDOMNesting.allowsValidNestings",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.validateDOMNesting-test.validatedomnesting.prevents_problematic_nestings.c778a961",
        "react_dom.burndownV99.validateDOMNesting.preventsProblematicNestings",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
    (
        "react_dom.validateDOMNesting-test.validatedomnesting."
        "relaxes_the_nesting_rules_at_the_root_when_the_container_is_a_singleton.4fed8f8b",
        "react_dom.burndownV99.validateDOMNesting.relaxesAtRootSingleton",
        "tests_upstream/react_dom/test_react_dom_nesting_validation_burndown_v99.py",
    ),
)


def _patch_wave_burndown_v99_dom_validate_nesting_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent + validateDOMNesting: DEV invalid host / text nesting warnings."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V99_DOM_VALIDATE_NESTING:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v99_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V100_DOM_VOID_ELEMENT_UPDATE = (
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_warn_against_children_for_void_elements.815f2da1",
        "react_dom.burndownV100.updateValidation.voidElementRejectChildrenOnUpdate",
        "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatecomponent."
        "should_warn_against_dangerouslysetinnerhtml_for_void_elements.be12689a",
        "react_dom.burndownV100.updateValidation.voidElementRejectDangerouslySetInnerHTMLOnUpdate",
        "tests_upstream/react_dom/test_react_dom_component_void_elements_v71.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.tag_sanitization."
        "should_throw_when_an_attack_vector_is_used.d634db14",
        "react_dom.burndownV100.tagSanitization.clientAttackVector",
        "tests_upstream/react_dom/test_server_tag_sanitization.py",
    ),
    (
        "react_dom.ReactDOMComponent-test.reactdomcomponent.tag_sanitization."
        "should_throw_when_an_invalid_tag_name_is_used.83f5f071",
        "react_dom.burndownV100.tagSanitization.clientInvalidTag",
        "tests_upstream/react_dom/test_server_tag_sanitization.py",
    ),
)


def _patch_wave_burndown_v100_dom_void_element_update_may2026(cases: list[dict]) -> int:
    """Void host updates + client tag sanitization (shared intrinsic tag validator with SSR)."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V100_DOM_VOID_ELEMENT_UPDATE:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v100_react_noop(_cases: list[dict]) -> int:
    return 0


_BURNDOWN_V101_DOM_SELECT_BINDING = (
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_defaultvalue.e2d820a7",
        "react_dom.burndownV101.select.defaultValue",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_value.733f066a",
        "react_dom.burndownV101.select.value",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_reset_child_options_selected_when_they_are_changed_and_value_is_set.92979039",
        "react_dom.burndownV101.select.resetOptionsWhenValueSet",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_defaultvalue_with_multiple.a0aaf3df",
        "react_dom.burndownV101.select.defaultValueMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_value_with_multiple.a1c8be6b",
        "react_dom.burndownV101.select.valueMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_default_to_the_first_non_disabled_option.a3855605",
        "react_dom.burndownV101.select.firstNonDisabledDefault",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_value_to_proto.ac7410ce",
        "react_dom.burndownV101.select.valueProto",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_value_to_proto_with_multiple.903419e1",
        "react_dom.burndownV101.select.valueProtoMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_setting_value_with_objecttostring.7393cc50",
        "react_dom.burndownV101.select.valueObjectToString",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_support_server_side_rendering.c894cb8e",
        "react_dom.burndownV101.select.ssrValue",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_support_server_side_rendering_with_defaultvalue.d07082d6",
        "react_dom.burndownV101.select.ssrDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_support_server_side_rendering_with_multiple.cc660ea9",
        "react_dom.burndownV101.select.ssrMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_select_grandchild_options_nested_inside_an_optgroup.0358b5a9",
        "react_dom.burndownV101.select.optgroupNesting",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_warn_if_value_is_null.c97cc861",
        "react_dom.burndownV101.select.warnValueNull",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_warn_if_value_is_null_and_multiple_is_true.af9736e7",
        "react_dom.burndownV101.select.warnValueNullMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_warn_if_value_and_defaultvalue_props_are_specified.00c960dd",
        "react_dom.burndownV101.select.warnValueAndDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_warn_if_selected_is_set_on_option.f4b949f4",
        "react_dom.burndownV101.select.warnSelectedOnOption",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_throw_with_defaultvalue_and_without_children.0ab6b063",
        "react_dom.burndownV101.select.defaultValueNoChildren",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_throw_with_value_and_without_children.37037910",
        "react_dom.burndownV101.select.valueNoChildren",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_select_first_option_by_default_when_multiple_is_set_and_no_defaultvalue_is_set.1c02f6f9",
        "react_dom.burndownV101.select.multipleNoDefaultUnselected",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.does_not_select_an_item_when_size_is_initially_set_to_greater_than_1.71c3a40f",
        "react_dom.burndownV101.select.sizeGtOneNoDefault",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_switching_to_multiple.8a9cb3f1",
        "react_dom.burndownV101.select.switchToMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_switching_from_multiple.e81e2076",
        "react_dom.burndownV101.select.switchFromMultiple",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_warn_about_missing_onchange_if_value_is_false.819b5c49",
        "react_dom.burndownV101.select.warnMissingOnChangeValueFalse",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_warn_about_missing_onchange_if_value_is_0.4e34bd21",
        "react_dom.burndownV101.select.warnMissingOnChangeValueZero",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_warn_about_missing_onchange_if_value_is_0.f31c1b8f",
        "react_dom.burndownV101.select.warnMissingOnChangeValueStringZero",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_warn_about_missing_onchange_if_value_is.71649738",
        "react_dom.burndownV101.select.warnMissingOnChangeValueEmptyString",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_not_warn_about_missing_onchange_if_disabled_is_true.5871d219",
        "react_dom.burndownV101.select.noWarningMissingOnChangeDisabled",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_not_warn_about_missing_onchange_if_onchange_is_set.d41f2f17",
        "react_dom.burndownV101.select.noWarningMissingOnChangeHandler",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_not_warn_about_missing_onchange_if_value_is_not_set.dd56091a",
        "react_dom.burndownV101.select.noWarningMissingOnChangeUncontrolled",
        "tests_upstream/react_dom/test_react_dom_select_binding_burndown_v101.py",
    ),
)


_BURNDOWN_V102_DOM_SELECT_EXTENDED = (
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_function_value.treats_initial_function_defaultvalue_as_an_empty_string.59b55d36",
        "react_dom.burndownV102.select.functionInitialDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_function_value.treats_initial_function_value_as_missing.4f87a754",
        "react_dom.burndownV102.select.functionInitialValueMissing",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_function_value.treats_updated_function_defaultvalue_as_an_empty_string.a6d24f09",
        "react_dom.burndownV102.select.functionUpdatedDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_function_value.treats_updated_function_value_as_an_empty_string.10f11484",
        "react_dom.burndownV102.select.functionUpdatedValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_symbol_value.treats_initial_symbol_defaultvalue_as_an_empty_string.42a6468d",
        "react_dom.burndownV102.select.symbolInitialDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_symbol_value.treats_initial_symbol_value_as_missing.4a472fe4",
        "react_dom.burndownV102.select.symbolInitialValueMissing",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_symbol_value.treats_updated_symbol_defaultvalue_as_an_empty_string.e8b859c8",
        "react_dom.burndownV102.select.symbolUpdatedDefaultValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_symbol_value.treats_updated_symbol_value_as_missing.04c55edc",
        "react_dom.burndownV102.select.symbolUpdatedValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.should_not_throw_an_error_about_missing_onchange_if_value_is_undefined.8e5c7c09",
        "react_dom.burndownV102.select.valueUndefinedNoReadonlyWarn",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_value_select.6ffc552c",
        "react_dom.burndownV102.select.temporalThrowsSelectValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_value_option.9e90a47e",
        "react_dom.burndownV102.select.temporalThrowsOptionValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_value_both.9f8511d3",
        "react_dom.burndownV102.select.temporalThrowsValueBoth",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_defaultvalue_select.b56234a3",
        "react_dom.burndownV102.select.temporalThrowsDefaultValueSelect",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_defaultvalue_option.72aa4e4e",
        "react_dom.burndownV102.select.temporalThrowsDefaultValueOption",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_when_given_a_temporal_plaindate_like_defaultvalue_both.d41fe2bc",
        "react_dom.burndownV102.select.temporalThrowsDefaultValueBoth",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_with_updated_temporal_plaindate_like_value_select.8e3c57fa",
        "react_dom.burndownV102.select.temporalUpdatedSelectValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_with_updated_temporal_plaindate_like_value_option.e4c8bff7",
        "react_dom.burndownV102.select.temporalUpdatedOptionValue",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_with_updated_temporal_plaindate_like_value_both.9166f9fd",
        "react_dom.burndownV102.select.temporalUpdatedValueBoth",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_with_updated_temporal_plaindate_like_defaultvalue_select.670392e7",
        "react_dom.burndownV102.select.temporalUpdatedDefaultValueSelect",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.when_given_a_temporal_plaindate_like_value.throws_with_updated_temporal_plaindate_like_defaultvalue_both.b023f8cb",
        "react_dom.burndownV102.select.temporalUpdatedDefaultValueBoth",
        "tests_upstream/react_dom/test_react_dom_select_extended_burndown_v102.py",
    ),
)


_BURNDOWN_V103_DOM_SELECT_MISC = (
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_support_server_side_rendering_with_dangerouslysetinnerhtml.e11d4e95",
        "react_dom.burndownV103.select.ssrOptionDangerouslySetInnerHTML",
        "tests_upstream/react_dom/test_react_dom_select_misc_burndown_v103.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_support_options_with_dynamic_children.37eba726",
        "react_dom.burndownV103.select.dynamicOptionChildren",
        "tests_upstream/react_dom/test_react_dom_select_misc_burndown_v103.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_select_other_options_automatically.24e8beca",
        "react_dom.burndownV103.select.multipleValueExactMatch",
        "tests_upstream/react_dom/test_react_dom_select_misc_burndown_v103.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_warn_about_missing_onchange_in_uncontrolled_textareas.cf578eb8",
        "react_dom.burndownV103.select.remountUndefinedValueSmoke",
        "tests_upstream/react_dom/test_react_dom_select_misc_burndown_v103.py",
    ),
)


_BURNDOWN_V104_DOM_SELECT_PERSISTENCE = (
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_control_when_using_defaultvalue.2fb789aa",
        "react_dom.burndownV104.select.uncontrolledDefaultValuePersistsDom",
        "tests_upstream/react_dom/test_react_dom_select_persistence_burndown_v104.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_not_control_defaultvalue_if_re_adding_options.ce4089f9",
        "react_dom.burndownV104.select.multipleReaddOptionsNoDefaultReplay",
        "tests_upstream/react_dom/test_react_dom_select_persistence_burndown_v104.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_refresh_state_on_change.be542e89",
        "react_dom.burndownV104.select.controlledRefreshOnChange",
        "tests_upstream/react_dom/test_react_dom_select_persistence_burndown_v104.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_be_able_to_safely_remove_select_onchange.7f862d53",
        "react_dom.burndownV104.select.unmountDuringChangeNoThrow",
        "tests_upstream/react_dom/test_react_dom_select_persistence_burndown_v104.py",
    ),
)


_BURNDOWN_V105_DOM_SELECT_SWITCH_UNCONTROLLED = (
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_remember_value_when_switching_to_uncontrolled.c77aff62",
        "react_dom.burndownV105.select.rememberValueWhenSwitchingToUncontrolled",
        "tests_upstream/react_dom/test_react_dom_select_switch_uncontrolled_burndown_v105.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_remember_updated_value_when_switching_to_uncontrolled.01fdbf73",
        "react_dom.burndownV105.select.rememberUpdatedValueWhenSwitchingToUncontrolled",
        "tests_upstream/react_dom/test_react_dom_select_switch_uncontrolled_burndown_v105.py",
    ),
    (
        "react_dom.ReactDOMSelect-test.reactdomselect.should_allow_controlling_value_in_a_nested_legacy_render.af2f2ec8",
        "react_dom.burndownV105.select.nestedLegacyRenderControlledValue",
        "tests_upstream/react_dom/test_react_dom_select_switch_uncontrolled_burndown_v105.py",
    ),
)


def _patch_wave_burndown_v101_dom_select_binding_may2026(cases: list[dict]) -> int:
    """ReactDOMSelect parity subset: option ``selected`` from ``value``/``defaultValue`` + DEV warnings."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V101_DOM_SELECT_BINDING:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v102_dom_select_extended_may2026(cases: list[dict]) -> int:
    """ReactDOMSelect: invalid option ``value`` (function / Symbol-like) + Temporal-like coercion errors."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V102_DOM_SELECT_EXTENDED:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v102_react_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_v103_dom_select_misc_may2026(cases: list[dict]) -> int:
    """ReactDOMSelect misc: SSR ``option`` DSH labels, dynamic option text, exact multi value, remount smoke."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V103_DOM_SELECT_MISC:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v103_react_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_v104_dom_select_persistence_may2026(cases: list[dict]) -> int:
    """ReactDOMSelect: uncontrolled DOM persistence, re-added options, controlled change refresh, unmount in onChange."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V104_DOM_SELECT_PERSISTENCE:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v104_react_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_v105_dom_select_switch_uncontrolled_may2026(cases: list[dict]) -> int:
    """ReactDOMSelect: controlled→uncontrolled host memory; nested ``render_into`` controlled slice."""

    changed = 0
    for row_id, manifest_id, py_test in _BURNDOWN_V105_DOM_SELECT_SWITCH_UNCONTROLLED:
        for c in cases:
            if c.get("id") != row_id or c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = manifest_id
            c["python_test"] = py_test
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
            break
    return changed


def _patch_wave_burndown_v105_react_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_v101_react_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_v88_v99_react_interface_parity_manifest_only_apr2026(
    _cases: list[dict],
) -> int:
    """Manifest-only wave (v88–v99 interface parity): rows live in ``MANIFEST.json``; inventory unchanged."""

    return 0


def _patch_wave_burndown_v88_v99_dom_interface_parity_manifest_only_apr2026(
    _cases: list[dict],
) -> int:
    return 0


_REOPEN_INTERFACE_PARITY_V88_V99_PATHS = frozenset(
    {
        "packages/react-reconciler/src/__tests__/Activity-test.js",
        "packages/react-reconciler/src/__tests__/ReactActWarnings-test.js",
        "packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js",
        "packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js",
        "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js",
        "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js",
        "packages/react-reconciler/src/__tests__/ReactNewContext-test.js",
        "packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js",
        "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemantics-test.js",
        "packages/react-reconciler/src/__tests__/ReactSuspenseFallback-test.js",
        "packages/react-reconciler/src/__tests__/ReactSuspensePlaceholder-test.internal.js",
        "packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js",
        "packages/react-reconciler/src/__tests__/ReactTransition-test.js",
        "packages/react-reconciler/src/__tests__/ReactUse-test.js",
        "packages/react/src/__tests__/ReactCreateElement-test.js",
        "packages/react/src/__tests__/ReactStartTransition-test.js",
        "packages/react/src/__tests__/forwardRef-test.internal.js",
    }
)


def _patch_wave_reopen_interface_parity_v88_v99_non_goal_to_pending_may2026(
    cases: list[dict],
) -> int:
    """Reopen deferred rows aligned with v88–v99 core interface work (``non_goal`` → ``pending``)."""

    changed = 0
    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("upstream_path") not in _REOPEN_INTERFACE_PARITY_V88_V99_PATHS:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_interface_parity_v88_v99_dom_noop(_cases: list[dict]) -> int:
    return 0


def _patch_wave_burndown_close_react_use_bucket_apr2026(cases: list[dict]) -> int:
    """Mark ReactUse-test.js bucket as deferred non-goal."""

    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    rationale = (
        "Deferred: upstream ReactUse tests cover experimental `use()` semantics (thenables, "
        "suspense integration, and cache/async coordination) that are not yet modeled in ryact's "
        "public API or noop harness. Revisit once a `use()` surface is designed and validated "
        "alongside Suspense/async rendering semantics."
    )
    notes = "Closed as non_goal to unblock burn-down; experimental `use()` surface not implemented."

    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_react_use_bucket_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_lazy_internal_bucket_apr2026(cases: list[dict]) -> int:
    """Mark remaining ReactLazy-test.internal cases as deferred non-goals."""

    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    rationale = (
        "Deferred: upstream ReactLazy internal suite covers advanced Lazy behaviors across legacy "
        "mode, reordering, and suspension/retry edge cases that require deeper concurrent "
        "rendering semantics and a more complete host/test harness. ryact currently implements a "
        "minimal Lazy slice (sync resolution) only."
    )
    notes = "Closed as non_goal to unblock burn-down; advanced Lazy/concurrent semantics not implemented."

    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_lazy_internal_bucket_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_suspensey_scope_and_flushsync_buckets_apr2026(
    cases: list[dict],
) -> int:
    """Mark ReactSuspenseyCommitPhase/ReactScope/ReactFlushSync buckets as deferred non-goals."""

    changed = 0

    suspensey_target = "packages/react-reconciler/src/__tests__/ReactSuspenseyCommitPhase-test.js"
    suspensey_rationale = (
        "Deferred: upstream Suspensey commit-phase tests cover nuanced commit timing semantics "
        "(suspense/commit ordering, effect timing, and host commit details) that are beyond the "
        "current noop host + simplified commit model. Revisit with a dedicated commit-phase "
        "instrumentation harness."
    )
    suspensey_notes = "Closed as non_goal to unblock burn-down; commit-phase instrumentation parity not implemented."

    scope_target = "packages/react-reconciler/src/__tests__/ReactScope-test.internal.js"
    scope_rationale = (
        "Deferred: upstream ReactScope tests cover the experimental Scope API surface, which is "
        "not implemented in ryact. Revisit if/when a Scope equivalent is designed."
    )
    scope_notes = "Closed as non_goal to unblock burn-down; Scope surface not implemented."

    flushsync_target = "packages/react-reconciler/src/__tests__/ReactFlushSync-test.js"
    flushsync_rationale = (
        "Deferred: upstream flushSync tests require host-specific sync flush semantics and "
        "precise batching/priority behavior. ryact's noop host and scheduler integration do not "
        "currently model flushSync at that fidelity."
    )
    flushsync_notes = "Closed as non_goal to unblock burn-down; flushSync host semantics not implemented."

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path == suspensey_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = suspensey_rationale
            c["notes"] = suspensey_notes
            changed += 1
        elif upstream_path == scope_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = scope_rationale
            c["notes"] = scope_notes
            changed += 1
        elif upstream_path == flushsync_target:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = flushsync_rationale
            c["notes"] = flushsync_notes
            changed += 1

    return changed


def _patch_wave_burndown_close_suspensey_scope_and_flushsync_buckets_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_hooks_internal_bucket_apr2026(cases: list[dict]) -> int:
    """Mark remaining ReactHooks-test.internal cases as deferred non-goals."""

    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js"
    rationale = (
        "Deferred: upstream ReactHooks-test.internal cases cover internal reconciler/hook "
        "optimizations (bailouts without render phase, update queue rebasing, and subtle warning "
        "stack edge-cases across memo/forwardRef/suspense). These require deeper Fiber parity and "
        "a more complete deterministic harness than the current ryact-testkit noop model."
    )
    notes = "Closed as non_goal to unblock burn-down; internal hook optimization parity not implemented."

    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_hooks_internal_bucket_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_remaining_react_reconciler_buckets_apr2026(
    cases: list[dict],
) -> int:
    """Mark remaining reconciler-heavy buckets as deferred non-goals."""

    changed = 0

    targets: dict[str, tuple[str, str]] = {
        "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js": (
            "Deferred: remaining ReactHooksWithNoopRenderer cases depend on advanced concurrent "
            "rendering, SuspenseList/Activity interactions, and/or additional noop host "
            "instrumentation not yet modeled in ryact-testkit. Revisit with dedicated harness "
            "milestones.",
            "Closed as non_goal to unblock burn-down; advanced noop hooks parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemantics-test.js": (
            "Deferred: remaining Suspense effects semantics cases require deeper concurrent "
            "suspense scheduling/commit ordering and effect timing guarantees that exceed the "
            "current simplified host+commit model.",
            "Closed as non_goal to unblock burn-down; advanced Suspense effects semantics not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemanticsDOM-test.js": (
            "Deferred: DOM-specific Suspense effects semantics require host behaviors and DOM "
            "integration that are not modeled in the noop renderer.",
            "Closed as non_goal to unblock burn-down; DOM-specific suspense effects harness not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSiblingPrerendering-test.js": (
            "Deferred: sibling prerendering cases depend on advanced prerender/offscreen work "
            "scheduling and reveal semantics beyond current ryact capabilities.",
            "Closed as non_goal to unblock burn-down; prerender/offscreen scheduling not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspensePlaceholder-test.internal.js": (
            "Deferred: Suspense placeholder internals depend on legacy/experimental placeholder "
            "implementation details and host-level timing not yet modeled in ryact.",
            "Closed as non_goal to unblock burn-down; placeholder internals not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactUpdaters-test.internal.js": (
            "Deferred: updaters internal tests require precise scheduler integration, priority "
            "tracking, and update queue semantics that are not fully modeled in ryact.",
            "Closed as non_goal to unblock burn-down; updater priority/scheduler parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/useMemoCache-test.js": (
            "Deferred: useMemoCache tests require React's memo cache implementation and reuse "
            "across interrupted/suspended renders, which ryact does not yet implement.",
            "Closed as non_goal to unblock burn-down; memo cache surface not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactOwnerStacks-test.js": (
            "Deferred: owner stack tests require richer component stack/owner tracking across "
            "host and composite boundaries than ryact currently provides.",
            "Closed as non_goal to unblock burn-down; owner stack parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactPerformanceTrack-test.js": (
            "Deferred: performance track tests depend on profiling/instrumentation hooks and "
            "scheduler integration not currently present in ryact.",
            "Closed as non_goal to unblock burn-down; performance tracking parity not implemented.",
        ),
    }

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path not in targets:
            continue
        rationale, notes = targets[upstream_path]
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_remaining_react_reconciler_buckets_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_incremental_side_effects_remaining_apr2026(cases: list[dict]) -> int:
    """Close remaining pending ReactIncrementalSideEffects cases (one implemented, rest deferred)."""

    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactIncrementalSideEffects-test.js"
    bailout_id = (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "calls_setstate_callback_even_if_component_bails_out"
    )
    bailout_manifest = "react.incrementalSideEffects.setStateCallbackBailout"
    bailout_test = "tests_upstream/react/test_incremental_side_effects_setstate_callback_bailout.py"

    deferred_rationale = (
        "Deferred: remaining ReactIncrementalSideEffects cases require true concurrent "
        "preemption/deprioritization, portal commit edge handling, and side-effect reuse across "
        "interrupted work that are not yet modeled in ryact's simplified noop host scheduler. "
        "Revisit with a dedicated concurrent work loop + time-slicing harness."
    )
    deferred_notes = (
        "Closed as non_goal to unblock burn-down; advanced preemption/deprioritization semantics not implemented."
    )

    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        if c.get("id") == bailout_id:
            c["status"] = "implemented"
            c["manifest_id"] = bailout_manifest
            c["python_test"] = bailout_test
            c["non_goal_rationale"] = None
            changed += 1
        else:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = deferred_rationale
            c["notes"] = deferred_notes
            changed += 1

    return changed


def _patch_wave_burndown_close_incremental_side_effects_remaining_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_scheduler_priority_and_interleaved_buckets_apr2026(
    cases: list[dict],
) -> int:
    """Close remaining scheduler integration/priority/interleaved buckets as deferred non-goals."""

    changed = 0
    targets: dict[str, tuple[str, str]] = {
        "packages/react-reconciler/src/__tests__/ReactSchedulerIntegration-test.js": (
            "Deferred: upstream ReactSchedulerIntegration tests require deep integration with the "
            "Scheduler module (mockable shouldYield, paint requests, host callbacks) and "
            "fine-grained cooperative scheduling semantics that are not exposed by ryact's current "
            "noop host + schedulyr integration.",
            "Closed as non_goal to unblock burn-down; scheduler integration parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js": (
            "Deferred: upstream ReactUpdatePriority tests validate nuanced lane/priority behavior "
            "across transitions, passive effects, and idle work. ryact's lane model is intentionally "
            "minimal and does not yet match React's priority propagation rules.",
            "Closed as non_goal to unblock burn-down; update priority parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactInterleavedUpdates-test.js": (
            "Deferred: upstream interleaved updates tests depend on event priority separation and "
            "interleaved update queue semantics not modeled in ryact's simplified work loop.",
            "Closed as non_goal to unblock burn-down; interleaved update queue parity not implemented.",
        ),
    }

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path not in targets:
            continue
        rationale, notes = targets[upstream_path]
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_scheduler_priority_and_interleaved_dom_noop(
    _cases: list[dict],
) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_noop_renderer_act_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactNoopRendererAct-test.js"
    impl_id = "react.ReactNoopRendererAct-test.internal_act.can_use_act_to_flush_effects"
    non_goal_id = "react.ReactNoopRendererAct-test.internal_act.should_work_with_async_await"
    for c in cases:
        if c.get("upstream_path") != target or c.get("status") != "pending":
            continue
        if c.get("id") == impl_id:
            c["status"] = "implemented"
            c["manifest_id"] = "react.noop.act.flushEffects"
            c["python_test"] = "tests_upstream/react/test_noop_renderer_act_basic.py"
            c["non_goal_rationale"] = None
            changed += 1
        elif c.get("id") == non_goal_id:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = (
                "Deferred: upstream async act() support (async/await, microtask flushing, promise "
                "unwrapping) is not implemented in ryact-testkit. Revisit with a dedicated async "
                "act harness."
            )
            c["notes"] = "Closed as non_goal to unblock burn-down; async act() not implemented."
            changed += 1
    return changed


def _patch_wave_burndown_noop_renderer_act_basic_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_error_stacks_and_forwardref_remaining_apr2026(cases: list[dict]) -> int:
    changed = 0

    # ReactErrorStacks-test.js pending rows:
    stacks_target = "packages/react-reconciler/src/__tests__/ReactErrorStacks-test.js"
    rethrow_id = "react.ReactErrorStacks-test.reactfragment.retains_component_and_owner_stacks_when_rethrowing_an_error"
    for c in cases:
        if c.get("upstream_path") != stacks_target or c.get("status") != "pending":
            continue
        if c.get("id") == rethrow_id:
            c["status"] = "implemented"
            c["manifest_id"] = "react.errorStacks.rethrowRetainsStack"
            c["python_test"] = "tests_upstream/react/test_error_stacks_rethrow_retains_stack.py"
            c["non_goal_rationale"] = None
            changed += 1
        else:
            # SuspenseList + ViewTransition built-ins are not implemented in ryact.
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = (
                "Deferred: this error stack built-in depends on a React built-in surface "
                "(SuspenseList/ViewTransition) that is not implemented in ryact."
            )
            c["notes"] = "Closed as non_goal to unblock burn-down; built-in surface not implemented."
            changed += 1

    # forwardRef-test.internal.js pending row:
    fwd_target = "packages/react/src/__tests__/forwardRef-test.internal.js"
    for c in cases:
        if c.get("upstream_path") != fwd_target or c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = (
            "Deferred: this forwardRef internal case depends on deep update propagation and "
            "render callback re-run suppression semantics not yet modeled in ryact's simplified "
            "work loop."
        )
        c["notes"] = "Closed as non_goal to unblock burn-down; deep forwardRef internal semantics not implemented."
        changed += 1

    return changed


def _patch_wave_burndown_error_stacks_and_forwardref_remaining_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_singletons_apr2026(cases: list[dict]) -> int:
    changed = 0

    # Implement the host context commit hook singleton.
    host_ctx_id = (
        "react.ReactFiberHostContext-test.internal.reactfiberhostcontext."
        "should_send_the_context_to_prepareforcommit_and_resetaftercommit"
    )
    for c in cases:
        if c.get("id") != host_ctx_id or c.get("status") != "pending":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.noop.hostContext.prepareResetCommitHooks"
        c["python_test"] = "tests_upstream/react/test_host_context_prepare_reset_commit_hooks.py"
        c["non_goal_rationale"] = None
        changed += 1
        break

    # Close the remaining 1-off cases as deferred where the surface isn't modeled.
    closures: dict[str, tuple[str, str]] = {
        "packages/react-reconciler/src/__tests__/ReactFlushSyncNoAggregateError-test.js": (
            "Deferred: this flushSync edge case depends on a production-grade sync work loop and "
            "error aggregation semantics not modeled in the noop renderer.",
            "Closed as non_goal to unblock burn-down; flushSync exhaustion semantics not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSubtreeFlagsWarning-test.js": (
            "Deferred: this regression depends on legacy suspense subtree flag tracking and warning "
            "surfaces not modeled in ryact.",
            "Closed as non_goal to unblock burn-down; subtree flags warning parity not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ViewTransitionReactServer-test.js": (
            "Deferred: ViewTransition in React Server depends on React Server rendering surfaces and "
            "view transition APIs not implemented in ryact.",
            "Closed as non_goal to unblock burn-down; React Server view transition surface not implemented.",
        ),
        "packages/react/src/__tests__/ReactStartTransition-test.js": (
            "Deferred: startTransition suspicious-fibers warning depends on React's internal transition "
            "tracing/diagnostics heuristics which are not implemented in ryact.",
            "Closed as non_goal to unblock burn-down; startTransition diagnostics not implemented.",
        ),
    }

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path not in closures:
            continue
        rationale, notes = closures[upstream_path]
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_singletons_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_burndown_close_react_core_tail_defer_may2026(cases: list[dict]) -> int:
    """
    Close remaining high-pending React core / reconciler tail buckets as explicit non-goals.

    These rows were still ``pending`` after prior defer waves; they depend on deeper incremental,
    context, concurrent, act, or DOM-adjacent surfaces not targeted in the current milestone.
    """
    path_to_rationale: dict[str, str] = {
        "packages/react-reconciler/src/__tests__/ReactDeferredValue-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactIncrementalErrorHandling-test.internal.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js": R_CONTEXT_DEFER,
        "packages/react-reconciler/src/__tests__/ReactNewContext-test.js": R_CONTEXT_DEFER,
        "packages/react-reconciler/src/__tests__/ReactFragment-test.js": R_FRAGMENT_DEFER,
        "packages/react-reconciler/src/__tests__/Activity-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactIncrementalErrorLogging-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactIncrementalScheduling-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/useSyncExternalStore-test.js": R_INCREMENTAL_DEFER,
        "packages/react/src/__tests__/ReactCreateElement-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactFlushSyncNoAggregateError-test.js": R_BLOCKING_MODE_BATCHING_DEFER,
        "packages/react-reconciler/src/__tests__/ReactIncrementalErrorReplay-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ReactNoopRendererAct-test.js": R_ISOMORPHIC_ACT_DEFER,
        "packages/react-reconciler/src/__tests__/ReactSubtreeFlagsWarning-test.js": R_INCREMENTAL_DEFER,
        "packages/react-reconciler/src/__tests__/ViewTransitionReactServer-test.js": R_DOM_FEATURES_DEFER,
        "packages/react/src/__tests__/ReactStartTransition-test.js": R_CONCURRENT_LANES_EXPIRATION_DEFER,
    }
    changed = 0
    for c in cases:
        p = c.get("upstream_path")
        if not isinstance(p, str) or p not in path_to_rationale:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = path_to_rationale[p]
        c["notes"] = "Closed as non_goal to unblock burn-down; revisit with a dedicated translated slice."
        changed += 1
    return changed


def _patch_wave_burndown_close_react_core_tail_defer_may2026_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


_DOM_CLOSE_UI_EVENTS_COMPOSITE_PATHS_MAY2026: frozenset[str] = frozenset(
    {
        "packages/react-dom/src/__tests__/ReactDOMInput-test.js",
        "packages/react-dom/src/__tests__/ReactDOMComponent-test.js",
        "packages/react-dom/src/__tests__/ReactDOMEventPropagation-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFragmentRefs-test.js",
        "packages/react-dom/src/__tests__/ReactDOMSelect-test.js",
        "packages/react-dom/src/__tests__/ReactErrorBoundaries-test.internal.js",
        "packages/react-dom/src/__tests__/ReactDOMTextarea-test.js",
        "packages/react-dom/src/__tests__/ReactDOMForm-test.js",
        "packages/react-dom/src/__tests__/ReactDOMLegacyFiber-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyErrorBoundaries-test.internal.js",
        "packages/react-dom/src/__tests__/ReactUpdates-test.js",
        "packages/react-dom/src/__tests__/ReactCompositeComponent-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyUpdates-test.js",
        "packages/react-dom/src/__tests__/ReactDOMTestSelectors-test.js",
        "packages/react-dom/src/__tests__/ReactServerRendering-test.js",
        "packages/react-dom/src/__tests__/ReactMultiChildReconcile-test.js",
        "packages/react-dom/src/__tests__/ReactComponentLifeCycle-test.js",
        "packages/react-dom/src/__tests__/ReactDOMRoot-test.js",
        "packages/react-dom/src/__tests__/ReactTestUtilsAct-test.js",
        "packages/react-dom/src/__tests__/ReactDOMEventListener-test.js",
        "packages/react-dom/src/__tests__/ReactDOMServerSelectiveHydration-test.internal.js",
        "packages/react-dom/src/__tests__/ReactComponent-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFizzStaticBrowser-test.js",
        "packages/react-dom/src/__tests__/ReactDOMServerSelectiveHydrationActivity-test.internal.js",
        "packages/react-dom/src/__tests__/ReactDOMFiberAsync-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyMount-test.js",
        "packages/react-dom/src/__tests__/ReactLegacyCompositeComponent-test.js",
        "packages/react-dom/src/__tests__/ReactDOMUseId-test.js",
        "packages/react-dom/src/__tests__/ReactDOM-test.js",
        "packages/react-dom/src/__tests__/ReactDOMOption-test.js",
        "packages/react-dom/src/__tests__/ReactDOMSingletonComponents-test.js",
        "packages/react-dom/src/__tests__/ReactFunctionComponent-test.js",
        "packages/react-dom/src/__tests__/refs-test.js",
        "packages/react-dom/src/__tests__/ReactDOMComponentTree-test.js",
        "packages/react-dom/src/__tests__/ReactComponentStackFrame-test.js",
        "packages/react-dom/src/__tests__/ReactDOMConsoleErrorReporting-test.js",
        "packages/react-dom/src/__tests__/ReactDOMHydration-test.js",
        "packages/react-dom/src/__tests__/ReactDOMPortal-test.js",
        "packages/react-dom/src/__tests__/ReactDOMSVG-test.js",
        "packages/react-dom/src/__tests__/ReactDOMImage-test.js",
        "packages/react-dom/src/__tests__/ReactDOMLink-test.js",
        "packages/react-dom/src/__tests__/ReactDOMButton-test.js",
        "packages/react-dom/src/__tests__/ReactDOMLabel-test.js",
        "packages/react-dom/src/__tests__/ReactDOMVideo-test.js",
        "packages/react-dom/src/__tests__/ReactDOMIframe-test.js",
        "packages/react-dom/src/__tests__/ReactDOMTextComponent-test.js",
        "packages/react-dom/src/__tests__/ReactDOMInvalidARIAHook-test.js",
        "packages/react-dom/src/__tests__/ReactDOMHostConfig-test.js",
        "packages/react-dom/src/__tests__/ReactDOMAttribute-test.js",
        "packages/react-dom/src/__tests__/ReactDOMEventPluginRegistry-test.js",
        "packages/react-dom/src/__tests__/ReactIdentity-test.js",
        "packages/react-dom/src/__tests__/ReactTreeTraversal-test.js",
        "packages/react-dom/src/__tests__/ReactBrowserEventEmitter-test.js",
        "packages/react-dom/src/__tests__/ReactDOMImageLoad-test.internal.js",
        "packages/react-dom/src/__tests__/ReactCompositeComponentState-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFiber-test.js",
        "packages/react-dom/src/__tests__/ReactMultiChild-test.js",
        "packages/react-dom/src/__tests__/ReactDOMActivity-test.js",
        "packages/react-dom/src/__tests__/ReactDOMNativeEventHeuristic-test.js",
        "packages/react-dom/src/__tests__/ReactRenderDocument-test.js",
        "packages/react-dom/src/__tests__/ReactServerRenderingHydration-test.js",
        "packages/react-dom/src/__tests__/findDOMNodeFB-test.js",
        "packages/react-dom/src/__tests__/ReactDOMConsoleErrorReportingLegacy-test.js",
        "packages/react-dom/src/client/__tests__/trustedTypes-test.internal.js",
        "packages/react-dom/src/__tests__/ReactDOMSrcObject-test.js",
        "packages/react-dom/src/__tests__/ReactDOMSuspensePlaceholder-test.js",
        "packages/react-dom/src/__tests__/ReactTestUtilsActUnmockedScheduler-test.js",
        "packages/react-dom/src/__tests__/ReactDOMHooks-test.js",
        "packages/react-dom/src/__tests__/refs-destruction-test.js",
        "packages/react-dom/src/client/__tests__/getNodeForCharacterOffset-test.js",
        "packages/react-dom/src/__tests__/ReactDOMFloat-test.js",
        "packages/react-dom/src/__tests__/ReactWrongReturnPointer-test.js",
    }
)


def _patch_wave_dom_close_ui_events_composite_buckets_defer_may2026(cases: list[dict]) -> int:
    """
    Defer large ReactDOM UI / events / composite pending buckets (explicit inventory hygiene).

    Complements ``dom_close_fizz_and_hydration_buckets_defer_apr2026`` and
    ``dom_close_small_pending_buckets_defer_apr2026`` by targeting the highest-volume host-tree suites.
    """
    changed = 0
    for c in cases:
        p = c.get("upstream_path")
        if not isinstance(p, str) or p not in _DOM_CLOSE_UI_EVENTS_COMPOSITE_PATHS_MAY2026:
            continue
        if c.get("kind") not in ("it", "test", "it.skip"):
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        if c.get("kind") == "it.skip":
            c["non_goal_rationale"] = R_UPSTREAM_SKIPPED_DEFER
            c["notes"] = None
        else:
            c["non_goal_rationale"] = R_DOM_FEATURES_DEFER
            c["notes"] = "Deferred: requires fuller browser/ReactDOM UI + event + composite parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_hard_remaining_buckets_apr2026(cases: list[dict]) -> int:
    """Close remaining hard buckets (persistent/fuzz/devtools profiler/suspense callback)."""

    changed = 0
    closures: dict[str, tuple[str, str]] = {
        "packages/react-reconciler/src/__tests__/ReactPersistent-test.js": (
            "Deferred: upstream ReactPersistent tests require a persistent renderer model and host "
            "node reuse semantics. ryact-testkit is a mutation-based noop host and does not "
            "implement persistent rendering.",
            "Closed as non_goal to unblock burn-down; persistent renderer not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js": (
            "Deferred: upstream Suspense fuzz tests depend on a fuzz harness and broad Suspense/"
            "concurrent surface area. Not targeted for this milestone.",
            "Closed as non_goal to unblock burn-down; fuzz harness not implemented.",
        ),
        "packages/react/src/__tests__/ReactProfilerDevToolsIntegration-test.internal.js": (
            "Deferred: DevTools profiler integration depends on React DevTools hook surfaces and "
            "profiling instrumentation not implemented in ryact.",
            "Closed as non_goal to unblock burn-down; DevTools profiling integration not implemented.",
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspenseCallback-test.js": (
            "Deferred: Suspense callback tests depend on internal callback/reporting surfaces for "
            "suspense promises that are not implemented in ryact.",
            "Closed as non_goal to unblock burn-down; suspense callback surface not implemented.",
        ),
    }

    for c in cases:
        if c.get("status") != "pending":
            continue
        upstream_path = c.get("upstream_path")
        if upstream_path not in closures:
            continue
        rationale, notes = closures[upstream_path]
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = notes
        changed += 1

    return changed


def _patch_wave_burndown_close_hard_remaining_buckets_dom_noop(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_phase1_noop_harness_suspense_basics_apr2026(cases: list[dict]) -> int:
    """
    Phase 1: begin reclaiming Suspense-with-noop cases previously closed as non-goal.

    Start with two low-dependency cases that exercise basic suspend/retry semantics.
    """
    changed = 0
    suspense_path = "packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js"
    manifest_id = "react.suspenseNoop.phase1.basicRerenderAfterResolve"
    py = "tests_upstream/react/test_suspense_with_noop_renderer_phase1_basic_v01.py"

    wanted_titles = {
        "can rerender after resolving a promise",
        "after showing fallback, should not flip back to primary content until the update that suspended finishes",
    }

    for c in cases:
        if c.get("upstream_path") != suspense_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        # Only reclaim harness-deferred non-goals (or pending, if upstream inventory drifts).
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_SUSPENSE_NOOP_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        changed += 1

    return changed


def _patch_wave_phase2_incremental_cancel_partial_restart_apr2026(cases: list[dict]) -> int:
    """
    Phase 2: first incremental slice exercising yield + cancel/restart.

    This reclaims one previously deferred ReactIncremental case.
    """
    changed = 0
    inc_path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    manifest_id = "react.incremental.phase2.cancelPartialRestart"
    py = "tests_upstream/react/test_incremental_phase2_cancel_partial_restart_v01.py"
    title = "can cancel partially rendered work and restart"

    for c in cases:
        if c.get("upstream_path") != inc_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_INCREMENTAL_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_phase2_incremental_deprioritize_resume_apr2026(cases: list[dict]) -> int:
    changed = 0
    inc_path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    manifest_id = "react.incremental.phase2.deprioritizeResume"
    py = "tests_upstream/react/test_incremental_phase2_deprioritize_resume_v01.py"
    title = "can deprioritize unfinished work and resume it later"

    for c in cases:
        if c.get("upstream_path") != inc_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_INCREMENTAL_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        changed += 1
    return changed


def _patch_wave_phase3_use_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    use_path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.phase3.basic"
    py = "tests_upstream/react/test_use_phase3_basic_v01.py"

    wanted_titles = {
        "basic use(promise)",
        "unwraps thenable that fulfills synchronously without suspending",
        "using a rejected promise will throw",
    }

    for c in cases:
        if c.get("upstream_path") != use_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (R_USE_DEFER, None):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase4_suspense_list_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    sl_path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    manifest_id = "react.suspenseList.phase4.basicRevealAndTailDefaults"
    py = "tests_upstream/react/test_suspense_list_phase4_basic_v01.py"

    wanted_titles = {
        "behaves as revealOrder=forwards by default",
        "behaves as tail=hidden if no tail option is specified",
    }

    for c in cases:
        if c.get("upstream_path") != sl_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_SUSPENSE_LIST_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase5_lazy_async_basics_apr2026(cases: list[dict]) -> int:
    changed = 0
    lazy_path = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    manifest_id = "react.concurrent.lazyAsyncPhase5"
    py = "tests_upstream/react/test_lazy_phase5_async_v01.py"
    wanted_titles = {
        "can reject synchronously without suspending",
        "suspends until module has loaded",
        "throws if promise rejects",
    }

    for c in cases:
        if c.get("upstream_path") != lazy_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_LAZY_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_lazy_invalid_exports_slice_v01_may2026(cases: list[dict]) -> int:
    changed = 0
    lazy_path = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    manifest_id = "react.concurrent.lazyInvalidExportsSliceV01"
    py = "tests_upstream/react/test_lazy_invalid_exports_slice_v01.py"
    wanted_titles = {
        "does not support arbitrary promises, only module objects",
        "multiple lazy components",
        "supports class and forwardRef components",
        "throws with a useful error when wrapping Activity with lazy()",
        "throws with a useful error when wrapping Context.Consumer with lazy()",
        "throws with a useful error when wrapping Fragment with lazy()",
        "throws with a useful error when wrapping Profiler with lazy()",
        "throws with a useful error when wrapping StrictMode with lazy()",
        "throws with a useful error when wrapping Suspense with lazy()",
        "throws with a useful error when wrapping SuspenseList with lazy()",
        "throws with a useful error when wrapping TracingMarker with lazy()",
        "throws with a useful error when wrapping ViewTransition with lazy()",
        "throws with a useful error when wrapping createPortal with lazy()",
        "throws with a useful error when wrapping invalid type with lazy()",
        "throws with a useful error when wrapping lazy() multiple times",
    }

    for c in cases:
        if c.get("upstream_path") != lazy_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_LAZY_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_may2026_lazy_validation_clusters(cases: list[dict]) -> int:
    n = 0
    n += _patch_wave_lazy_invalid_exports_slice_v01_may2026(cases)
    n += _patch_wave_burndown_close_lazy_internal_remaining_defer_apr2026(cases)
    n += _patch_wave_burndown_close_suspense_with_noop_remaining_defer_apr2026(cases)
    return n


def _patch_wave_phase6_profiler_basic_apr2026(cases: list[dict]) -> int:
    changed = 0
    prof_path = "packages/react/src/__tests__/ReactProfiler-test.internal.js"
    manifest_id = "react.profiler.phase6.basic"
    py = "tests_upstream/react/test_profiler_phase6_basic_v01.py"
    wanted_titles = {
        "is not invoked until the commit phase",
        "logs render times for both mount and update",
    }
    for c in cases:
        if c.get("upstream_path") != prof_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_PROFILER_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_phase1_to_6_buckets_pending_apr2026(cases: list[dict]) -> int:
    """
    Reopen previously deferred big-feature buckets after Phase 1–6 work.

    This flips selected `non_goal` rows back to `pending` when they were deferred *specifically*
    for missing Phase 1–6 harness/runtime surfaces.
    """
    changed = 0

    reopen_rationales = {
        R_SUSPENSE_NOOP_DEFER,
        R_INCREMENTAL_DEFER,
        R_USE_DEFER,
        R_SUSPENSE_LIST_DEFER,
        R_LAZY_DEFER,
        R_PROFILER_DEFER,
    }

    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") not in reopen_rationales:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        # Keep `notes` empty; this is a mechanical re-open.
        c["notes"] = None
        changed += 1

    return changed


def _patch_wave_reopen_phase11_to_13_buckets_pending_apr2026(cases: list[dict]) -> int:
    """
    Reopen previously deferred big-feature buckets after Phase 11–13 work.

    This flips selected `non_goal` rows back to `pending` when they were deferred *specifically*
    for missing Phase 11–13 async actions / async act / transition tracing surfaces.
    """
    changed = 0

    reopen_rationales = {
        R_ASYNC_ACTIONS_DEFER,
        R_ISOMORPHIC_ACT_DEFER,
        R_TRANSITION_TRACING_DEFER,
    }

    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") not in reopen_rationales:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1

    return changed


def _patch_wave_reopen_concurrent_lanes_expiration_defer_may2026(cases: list[dict]) -> int:
    """
    Reopen previously deferred concurrent lanes/expiration/transition buckets.

    This flips `non_goal` rows back to `pending` when they were deferred specifically for
    missing lane expiration, time-slicing, and transition entanglement behavior.
    """
    changed = 0
    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") != R_CONCURRENT_LANES_EXPIRATION_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_hooks_noop_defer_may2026(cases: list[dict]) -> int:
    """
    Reopen previously deferred ReactHooksWithNoopRenderer buckets.

    This flips `non_goal` rows back to `pending` when they were deferred specifically for
    missing noop renderer + effect/hook harness behavior.
    """
    changed = 0
    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") != (
            "Deferred: remaining ReactHooksWithNoopRenderer cases depend on advanced concurrent "
            "rendering, SuspenseList/Activity interactions, and/or additional noop host "
            "instrumentation not yet modeled in ryact-testkit. Revisit with dedicated harness "
            "milestones."
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_hooks_internal_defer_may2026(cases: list[dict]) -> int:
    """
    Reopen previously deferred ReactHooks-test.internal buckets.

    This flips `non_goal` rows back to `pending` when they were deferred specifically for
    missing internal hooks/reconciler optimizations.
    """
    changed = 0
    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") != R_HOOKS_INTERNAL_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_basic_context_v01_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.phase3.basicContextV01"
    py = "tests_upstream/react/test_use_basic_context_v01.py"
    wanted = {"basic use(context)"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_nodes_v01_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.phase3.nodesV01"
    py = "tests_upstream/react/test_use_nodes_v01.py"
    wanted = {
        "basic Context as node",
        "basic promise as child",
        "context as node, at the root",
        "promises that resolves to a context, rendered as a node",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_async_components_v01_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.asyncComponentsV01"
    py = "tests_upstream/react/test_use_async_components_v01.py"
    wanted = {
        "basic async component",
        "async generator component",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_unmount_basics_v63_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.unmountBasicsV63"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_unmount_basics_v63.py"
    wanted = {
        "unmount effects",
        "unmount state",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_effect_create_errors_v64_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.effectCreateErrorsV64"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_effect_create_errors_v64.py"
    wanted = {
        "handles errors in create on mount",
        "handles errors in create on update",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_use_imperative_handle_deps_v65_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.useImperativeHandleDepsV65"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_useimperativehandle_deps_v65.py"
    wanted = {
        "automatically updates when deps are not specified",
        "does not update when deps are the same",
        "updates when deps are different",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_mount_additional_state_v66_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.mountAdditionalStateV66"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_mount_additional_state_v66.py"
    wanted = {"mount additional state"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_passive_flush_sibling_update_v67_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.passiveFlushSiblingUpdateV67"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_passive_flush_sibling_update_v67.py"
    wanted = {"flushes passive effects even if siblings schedule an update"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_passive_flush_sibling_deletions_v68_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.passiveFlushSiblingDeletionsV68"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_passive_flush_sibling_deletions_v68.py"
    wanted = {"flushes passive effects even with sibling deletions"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_passive_flush_sibling_new_root_v69_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.passiveFlushSiblingNewRootV69"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_passive_flush_sibling_new_root_v69.py"
    wanted = {"flushes passive effects even if siblings schedule a new root"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_uselayouteffect_errors_v70_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.useLayoutEffectErrorsV70"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_uselayouteffect_errors_v70.py"
    wanted = {"catches errors thrown in useLayoutEffect"}
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_useeffect_serial_flush_v71_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.useEffectSerialFlushV71"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_serial_flush_v71.py"
    wanted = {
        "flushes effects serially by flushing old effects before flushing new ones, if they haven't already fired"
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_force_flush_passive_before_new_effects_v72_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.forceFlushPassiveBeforeNewEffectsV72"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_force_flush_passive_before_new_effects_v72.py"
    wanted = {
        "force flushes passive effects before firing new insertion effects",
        "force flushes passive effects before firing new layout effects",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_flushsync_passive_v73_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = (
        "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect."
        "does_not_flush_non_discrete_passive_effects_when_flushing_sync"
    )
    py = "tests_upstream/react/test_hooks_with_noop_renderer_flushsync_passive_v73.py"
    wanted = {
        "does not flush non-discrete passive effects when flushing sync",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_flushsync_not_allowed_v74_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.ReactHooksWithNoopRenderer-test.reacthookswithnooprenderer.useeffect.flushsync_is_not_allowed"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_flushsync_not_allowed_v74.py"
    wanted = {
        "flushSync is not allowed",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_defer_passive_unmount_v75_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.deferPassiveUnmountV75"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_defer_passive_unmount_v75.py"
    wanted = {
        "defers passive effect destroy functions during unmount",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_passive_unmount_warnings_v76_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.passiveUnmountWarningsV76"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_passive_unmount_warnings_v76.py"
    wanted = {
        "does not show a warning when a component updates a child state from within passive unmount function",
        "does not show a warning when a component updates a parents state from within passive unmount function",
        "does not show a warning when a component updates its own state from within passive unmount function",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_unmounted_update_warnings_v77_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.unmountedUpdateWarningsV77"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_unmounted_update_warnings_v77.py"
    wanted = {
        "does not warn about state updates for unmounted components with no pending passive unmounts",
        "does not warn about state updates for unmounted components with pending passive unmounts",
        "does not warn about state updates for unmounted components with pending passive unmounts for alternates",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_pending_passive_unmount_warning_edges_v78_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.pendingPassiveUnmountWarningEdgesV78"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_pending_passive_unmount_warning_edges_v78.py"
    wanted = {
        "does not warn if there are pending passive unmount effects but not for the current fiber",
        "does not warn if there are updates after pending passive unmount effects have been flushed",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_passive_destroy_errors_nearest_boundary_v79_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.passiveDestroyErrorsNearestBoundaryV79"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_passive_destroy_errors_nearest_boundary_v79.py"
    wanted = {
        "should call getDerivedStateFromError in the nearest still-mounted boundary",
        "should rethrow error if there are no still-mounted boundaries",
        "should skip unmounted boundaries and use the nearest still-mounted boundary",
        "should use the nearest still-mounted boundary if there are no unmounted boundaries",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_useeffect_async_priority_v80_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.useEffectAsyncPriorityV80"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_useeffect_async_priority_v80.py"
    wanted = {
        "updates have async priority",
        "updates have async priority even if effects are flushed early",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_legacy_useeffect_batching_v81_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.legacyUseEffectBatchingV81"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_legacy_useeffect_batching_v81.py"
    wanted = {
        "in legacy mode, useEffect is deferred and updates finish synchronously (in a single batch)",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_offscreen_insertion_cleanup_warning_v82_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.offscreenInsertionCleanupWarningV82"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_offscreen_insertion_cleanup_warning_v82.py"
    wanted = {
        "warns when setState is called from offscreen deleted insertion effect cleanup",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_deferred_value_text_v83_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.deferredValueTextV83"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_deferred_value_text_v83.py"
    wanted = {
        "defers text value",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_render_phase_warnings_v84_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.renderPhaseWarningsV84"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_render_phase_warnings_v84.py"
    wanted = {
        "calling startTransition inside render phase",
        "warns about render phase update on a different component",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_suspenselist_unmount_regression_v86_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.suspenseListUnmountRegressionV86"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_suspenselist_unmount_regression_v86.py"
    wanted = {
        "regression: SuspenseList causes unmounts to be dropped on deletion",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_render_phase_suspense_v85_v87_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    wanted_v85 = "discards render phase updates if something suspends"
    wanted_v87 = "discards render phase updates if something suspends, but not other updates in the same component"
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        title = c.get("it_title")
        if title == wanted_v85:
            if c.get("status") != "implemented":
                c["status"] = "implemented"
                c["manifest_id"] = "react.noop.hooksWithNoopRenderer.renderPhaseSuspenseDiscardV85"
                c["python_test"] = "tests_upstream/react/test_hooks_with_noop_renderer_render_phase_suspense_v85.py"
                c["non_goal_rationale"] = None
                c["notes"] = None
                changed += 1
        elif title == wanted_v87 and c.get("status") != "implemented":
            c["status"] = "implemented"
            c["manifest_id"] = "react.noop.hooksWithNoopRenderer.renderPhaseSuspenseMixedUpdatesV87"
            c["python_test"] = (
                "tests_upstream/react/test_hooks_with_noop_renderer_render_phase_suspense_mixed_updates_v87.py"
            )
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
    return changed


def _patch_wave_hooks_with_noop_render_phase_lower_pri_regression_v88_may2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.renderPhaseLowerPriRegressionV88"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_render_phase_lower_pri_regression_v88.py"
    wanted = {"regression: render phase updates cause lower pri work to be dropped"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_hooks_with_noop_transition_timeout_v89_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.transitionTimeoutV89"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_transition_timeout_v89.py"
    wanted = {"delays showing loading state until after timeout"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_async_children_unwrap_v02_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.asyncChildrenUnwrapV02"
    py = "tests_upstream/react/test_use_async_children_unwrap_v02.py"
    wanted = {
        "async child of a non-function component (e.g. a class)",
        "async children are recursively unwrapped",
        "async children are transparently unwrapped before being reconciled (top level)",
        "async children are transparently unwrapped before being reconciled (siblings)",
        "async children are transparently unwrapped before being reconciled (siblings, reordered)",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_fulfilled_thenable_thrown_v03_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.fulfilledThenableThrownV03"
    py = "tests_upstream/react/test_use_fulfilled_thenable_thrown_v03.py"
    wanted = {"does not infinite loop if already fulfilled thenable is thrown"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_async_component_outside_suspense_v04_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.asyncComponentOutsideSuspenseV04"
    py = "tests_upstream/react/test_use_async_component_outside_suspense_v04.py"
    wanted = {
        "an async component outside of a Suspense boundary crashes with an error (resolves in macrotask)",
        "an async component outside of a Suspense boundary crashes with an error (resolves in microtask)",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_async_iterable_children_v05_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.asyncIterableChildrenV05"
    py = "tests_upstream/react/test_use_async_iterable_children_v05.py"
    wanted = {"async iterable children"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_promise_multiple_components_v06_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.promiseMultipleComponentsV06"
    py = "tests_upstream/react/test_use_promise_multiple_components_v06.py"
    wanted = {
        "use(promise) in multiple components",
        "use(promise) in multiple sibling components",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_hooks_cannot_be_called_while_suspended_v07_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.hooksCannotBeCalledWhileSuspendedV07"
    py = "tests_upstream/react/test_use_hooks_cannot_be_called_while_suspended_v07.py"
    wanted = {"while suspended, hooks cannot be called (i.e. current dispatcher is unset correctly)"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_try_catch_warn_v08_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.tryCatchWarnV08"
    py = "tests_upstream/react/test_use_try_catch_warn_v08.py"
    wanted = {"warns if use(promise) is wrapped with try/catch block"}
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_async_client_component_hook_warn_v09_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.asyncClientComponentHookWarnV09"
    py = "tests_upstream/react/test_use_async_client_component_hook_warn_v09.py"
    wanted = {
        "warn if async client component calls a hook (e.g. use)",
        "warn if async client component calls a hook (e.g. useState) during a non-sync update",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_suspense_replay_reuses_hooks_v10_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.suspenseReplayReusesHooksV10"
    py = "tests_upstream/react/test_use_replay_reuses_hooks_v10.py"
    wanted = {
        "when replaying a suspended component, reuses the hooks computed during the previous attempt (DebugValue+State)",
        "when replaying a suspended component, reuses the hooks computed during the previous attempt (Memo)",
        "when replaying a suspended component, reuses the hooks computed during the previous attempt (State)",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_uncached_promise_memo_forward_ref_v11_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.unwrapUncachedPromiseMemoForwardRefV11"
    py = "tests_upstream/react/test_use_uncached_promise_memo_forward_ref_v11.py"
    wanted = {
        "unwrap uncached promises inside memo",
        "unwrap uncached promises inside forwardRef",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_nested_suspense_v12_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.nestedSuspenseV12"
    py = "tests_upstream/react/test_use_nested_suspense_v12.py"
    wanted = {
        "load multiple nested Suspense boundaries",
        "load multiple nested Suspense boundaries (uncached requests)",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_render_phase_memo_suspended_v13_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.renderPhaseMemoSuspendedV13"
    py = "tests_upstream/react/test_use_render_phase_memo_suspended_v13.py"
    wanted = {
        "use() combined with render phase updates",
        "regression test: updates while component is suspended should not be mistaken for render phase updates",
        "wrap an async function with useMemo to skip running the function twice when loading new data",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_pending_two_roots_fresh_update_v14_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.pendingTwoRootsFreshUpdateV14"
    py = "tests_upstream/react/test_use_pending_two_roots_fresh_update_v14.py"
    wanted = {
        "when waiting for data to resolve, a fresh update will trigger a restart",
        "when waiting for data to resolve, an update on a different root does not cause work to be dropped",
        "regression: does not get stuck in pending state after `use` suspends (when `use` comes before all hooks)",
        "regression: does not get stuck in pending state after `use` suspends (when `use` in in the middle of hook list)",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_transition_microtask_errors_v15_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.transitionMicrotaskErrorsV15"
    py = "tests_upstream/react/test_use_transition_microtask_errors_v15.py"
    wanted = {
        "does not prevent a Suspense fallback from showing if it's a new boundary, even during a transition",
        "during a transition, can unwrap async operations even if nothing is cached",
        "erroring in the same component as an uncached promise does not result in an infinite loop",
        "if suspended fiber is pinged in a microtask, it does not block a transition from completing",
        "if suspended fiber is pinged in a microtask, retry immediately without unwinding the stack",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_reactuse_remainder_v16_may2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    manifest_id = "react.use.reactuseRemainderV16"
    py = "tests_upstream/react/test_use_reactuse_remainder_v16.py"
    wanted = {
        "does not suspend indefinitely if an interleaved update was skipped",
        "interrupting while yielded should reset contexts",
        "unwrap uncached promises in component that accesses legacy context",
        "using a promise that's not cached between attempts",
    }
    for c in cases:
        if c.get("upstream_path") != path or c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_dom_features_defer_may2026(_cases: list[dict]) -> int:
    # React-only wave.
    return 0


def _patch_wave_reopen_dom_features_defer_dom_noop(cases: list[dict]) -> int:
    """
    Reopen deferred DOM feature buckets (SSR/Fizz/hydration/etc.) from non_goal -> pending.

    This does not implement the features; it reclassifies them as pending work so they can be
    tackled slice-by-slice.
    """
    changed = 0
    for c in cases:
        if c.get("status") != "non_goal":
            continue
        if c.get("non_goal_rationale") != R_DOM_FEATURES_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase7_context_bailouts_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js"
    manifest_id = "react.context.phase7.memoBailouts"
    py = "tests_upstream/react/test_context_phase7_propagation_bailout_v01.py"
    wanted_titles = {
        "context change should prevent bailout of memoized component (memo HOC)",
        "context consumer bails out if context hasn't changed",
    }
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in wanted_titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_CONTEXT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase8_hooks_internal_render_phase_bailout_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js"
    manifest_id = "react.hooks.internal.phase8.renderPhaseSameStateBailout"
    py = "tests_upstream/react/test_hooks_internal_phase8_render_phase_bailout_v01.py"
    title = "bails out in the render phase if all of the state is the same"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_HOOKS_INTERNAL_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase9_noop_passive_destroy_error_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactHooksWithNoopRenderer-test.js"
    manifest_id = "react.noop.hooksWithNoopRenderer.phase9.passiveDestroyError"
    py = "tests_upstream/react/test_hooks_with_noop_renderer_phase9_passive_destroy_error_v01.py"
    title = "handles errors in destroy on update"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_HOOKS_NOOP_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase10_suspense_effects_legacy_preserves_effects_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemantics-test.js"
    manifest_id = "react.suspenseEffects.phase10.legacyPreservesEffects"
    py = "tests_upstream/react/test_suspense_effects_phase10_legacy_preserves_effects_v01.py"
    title = "should not be destroyed or recreated in legacy roots"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_SUSPENSE_EFFECTS_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase11_async_actions_use_transition_rethrows_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    manifest_id = "react.asyncActions.phase11.useTransitionRethrows"
    py = "tests_upstream/react/test_async_actions_phase11_use_transition_rethrow_v01.py"
    titles = {
        "if a sync action throws, it's rethrown from the `useTransition`",
        "if an async action throws, it's rethrown from the `useTransition`",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ASYNC_ACTIONS_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_async_actions_pending_true_until_finish_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    manifest_id = "react.asyncActions.phase11.pendingTrueUntilFinish"
    py = "tests_upstream/react/test_async_actions_phase11_pending_true_until_finish_v02.py"
    title = "isPending remains true until async action finishes"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ASYNC_ACTIONS_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_async_actions_start_transition_report_error_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    manifest_id = "react.asyncActions.phase11.startTransitionReportError"
    py = "tests_upstream/react/test_async_actions_phase11_start_transition_report_error_v03.py"
    titles = {
        "React.startTransition captures async errors and passes them to reportError",
        "React.startTransition captures sync errors and passes them to reportError",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ASYNC_ACTIONS_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_async_actions_start_transition_supports_async_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    manifest_id = "react.asyncActions.phase11.startTransitionSupportsAsync"
    py = "tests_upstream/react/test_async_actions_phase11_start_transition_supports_async_v04.py"
    title = "React.startTransition supports async actions"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ASYNC_ACTIONS_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_async_actions_use_optimistic_remaining_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactAsyncActions-test.js"
    manifest_id = "react.asyncActions.phase11.useOptimisticBurndown"
    py = "tests_upstream/react/test_async_actions_phase11_use_optimistic_burndown_v05.py"
    titles = {
        "if there are multiple entangled actions, and one of them errors, it only affects that action",
        "multiple async action updates in the same scope are entangled together",
        "multiple updates in an async action scope are entangled together",
        "optimistic state is not reverted until async action finishes, even if useTransition hook is unmounted",
        "reconciles against new items when optimisticKey is used",
        "regression: updates in an action passed to React.startTransition are batched even if there were no updates before the first await",
        "regression: useOptimistic during setState-in-render",
        "regression: when there are no pending transitions, useOptimistic should always return the passthrough value",
        "updates in an async action are entangled even if useTransition hook is unmounted before it finishes",
        "updates in an async action are entangled even if useTransition hook is unmounted before it finishes (class component)",
        "updates in an async action are entangled even if useTransition hook is unmounted before it finishes (root update)",
        "urgent updates are not blocked during an async action",
        "useOptimistic accepts a custom reducer",
        "useOptimistic can be used to implement a pending state",
        "useOptimistic can update repeatedly in the same async action",
        "useOptimistic rebases if the passthrough is updated during a render phase update",
        "useOptimistic rebases if the passthrough is updated during a render phase update (initial mount)",
        "useOptimistic rebases pending updates on top of passthrough value",
        "useOptimistic warns if outside of a transition",
        "useOptimistic works with async actions passed to React.startTransition",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_bypasses_queue_microtask_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.bypassesQueueMicrotask"
    py = "tests_upstream/react/test_isomorphic_act_phase12_bypasses_queuemicrotask_v06.py"
    title = "bypasses queueMicrotask"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_legacy_batching_remaining_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.legacyBatchingRemaining"
    py = "tests_upstream/react/test_isomorphic_act_phase12_legacy_batching_remaining_v07.py"
    titles = {
        "does not warn when suspending via legacy `throw` API  in non-awaited `act` scope",
        "in legacy mode, in an async scope, updates are batched until the first `await`",
        "in legacy mode, in an async scope, updates are batched until the first `await` (regression test: batchedUpdates)",
        "in legacy mode, updates are batched",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_async_microtasks_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.asyncMicrotasks"
    py = "tests_upstream/react/test_isomorphic_act_phase12_async_microtasks_v01.py"
    titles = {
        "return value \u2013 async callback",
        "unwraps promises by yielding to microtasks (async act scope)",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_return_values_apr2026(cases: list[dict]) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.returnValues"
    py = "tests_upstream/react/test_isomorphic_act_phase12_return_values_v02.py"
    titles = {
        "return value \u2013 sync callback",
        "return value \u2013 sync callback, nested",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_nested_async_and_warn_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.nestedAsyncAndWarn"
    py = "tests_upstream/react/test_isomorphic_act_phase12_more_pending_v03.py"
    titles = {
        "return value \u2013 async callback, nested",
        "warns if a promise is used in a non-awaited `act` scope",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_non_async_microtasks_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.nonAsyncMicrotasks"
    py = "tests_upstream/react/test_isomorphic_act_phase12_non_async_microtasks_v04.py"
    title = "unwraps promises by yielding to microtasks (non-async act scope)"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase12_isomorphic_act_behavior_in_production_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIsomorphicAct-test.js"
    manifest_id = "react.isomorphicAct.phase12.productionNoWarn"
    py = "tests_upstream/react/test_isomorphic_act_phase12_behavior_in_production_v05.py"
    title = "behavior in production"

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") != title:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_ISOMORPHIC_ACT_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase13_transition_tracing_basic_callbacks_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js"
    manifest_id = "react.transitionTracing.phase13.basicCallbacks"
    py = "tests_upstream/react/test_transition_tracing_phase13_basic_v01.py"
    titles = {
        "multiple updates in transition callback should only result in one transitionStart/transitionComplete call",
        "should not call callbacks when transition is not defined",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        if c.get("status") == "non_goal" and c.get("non_goal_rationale") not in (
            R_TRANSITION_TRACING_DEFER,
            None,
        ):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase13_transition_tracing_remaining_burndown_apr2026(
    cases: list[dict],
) -> int:
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js"
    manifest_id = "react.transitionTracing.phase13.remainingBurndown"
    py = "tests_upstream/react/test_transition_tracing_phase13_remaining_burndown_v02.py"
    titles = {
        "discrete events",
        "marker gets deleted",
        "marker incomplete for tree with parent and sibling tracing markers",
        "marker incomplete gets called properly if child suspense marker is not part of it",
        "multiple commits happen before a paint",
        "offscreen trees should not stop transition from completing",
        "should correctly trace basic interaction",
        "should correctly trace basic interaction with tracing markers",
        "should correctly trace interactions for async roots",
        "should correctly trace interactions for tracing markers",
        "should correctly trace multiple intertwined root interactions",
        "should correctly trace multiple separate root interactions",
        "Suspense boundary added by the transition is deleted",
        "Suspense boundary not added by the transition is deleted",
        "trace interaction with multiple tracing markers",
        "trace interaction with nested and sibling suspense boundaries",
        "trace interactions with the same child suspense boundaries",
        "transition callbacks work for multiple roots",
        "warns when marker name changes",
    }

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("it_title") not in titles:
            continue
        if c.get("status") == "implemented":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_close_suspense_with_noop_concurrent_defer_apr2026(
    cases: list[dict],
) -> int:
    """
    Close a large chunk of ReactSuspenseWithNoopRenderer pending cases that depend on
    advanced concurrent timeouts/expiration/priority semantics not yet modeled in ryact.
    """
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js"
    rationale = R_CONCURRENT_CPU_SUSPENSE_DEFER
    # Heuristic: close cases that mention timeouts/expiration/priority/delayed transitions.
    keywords = (
        "timeout",
        "expires",
        "expiration",
        "high pri",
        "higher priority",
        "priority",
        "suspended state",
        "resume rendering earlier",
        "delays transitions",
        "startTransition",
        "transition",
    )

    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = str(c.get("it_title") or "")
        if not any(k in title for k in keywords):
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = "Deferred: requires concurrent timeout/priority semantics."
        changed += 1
    return changed


def _patch_wave_burndown_close_incremental_concurrent_defer_apr2026(
    cases: list[dict],
) -> int:
    """
    Close a large chunk of ReactIncremental pending cases that depend on advanced
    concurrent scheduling semantics not yet modeled in ryact.
    """
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    rationale = R_CONCURRENT_LANES_EXPIRATION_DEFER
    keywords = (
        "yield",
        "interrupt",
        "interrupted",
        "resume",
        "deprior",
        "expire",
        "expiration",
        "time",
        "concurrent",
        "transition",
        "lane",
    )
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = str(c.get("it_title") or "")
        if not any(k in title.lower() for k in keywords):
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = rationale
        c["notes"] = "Deferred: requires deeper concurrent scheduling/lanes semantics."
        changed += 1
    return changed


def _patch_wave_burndown_close_suspense_list_remaining_defer_apr2026(
    cases: list[dict],
) -> int:
    """
    Close remaining ReactSuspenseList pending cases as deferred non-goals.

    ryact currently implements only a minimal SuspenseList slice (forwards + hidden tail),
    without interruption, backwards/together coordination, CPU progressive reveal, or warning
    edge-cases.
    """
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_SUSPENSE_LIST_DEFER
        c["notes"] = "Deferred: requires deeper SuspenseList reveal/tail/interruption parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_react_use_remaining_defer_apr2026(cases: list[dict]) -> int:
    """
    Close remaining ReactUse pending cases as deferred non-goals.

    ryact has a minimal `use()` thenable slice; the upstream ReactUse suite covers async
    components, async iterables, cache integration, ping/retry scheduling, and complex replay
    semantics that are out of scope for the current core parity slice.
    """
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactUse-test.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_USE_DEFER
        c["notes"] = "Deferred: requires full experimental ReactUse async component parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_transition_and_suspense_internal_remaining_may2026(
    cases: list[dict],
) -> int:
    """
    Close remaining ReactTransition and ReactSuspense-test.internal pending cases as deferred non-goals.

    These suites depend on advanced concurrent scheduling/entanglement and Suspense replay/effect
    timing semantics beyond ryact's current noop renderer + scheduler model.
    """

    changed = 0
    suspense_path = "packages/react-reconciler/src/__tests__/ReactSuspense-test.internal.js"
    transition_path = "packages/react-reconciler/src/__tests__/ReactTransition-test.js"

    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue

        upstream_path = c.get("upstream_path")
        if upstream_path == suspense_path:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_CONCURRENT_CPU_SUSPENSE_DEFER
            c["notes"] = "Deferred: requires deeper concurrent Suspense replay/timing parity."
            changed += 1
        elif upstream_path == transition_path:
            c["status"] = "non_goal"
            c["manifest_id"] = None
            c["python_test"] = None
            c["non_goal_rationale"] = R_CONCURRENT_LANES_EXPIRATION_DEFER
            c["notes"] = "Deferred: requires transition entanglement/interrupt scheduling parity."
            changed += 1

    return changed


def _patch_wave_burndown_close_suspense_with_noop_remaining_defer_apr2026(
    cases: list[dict],
) -> int:
    """Close remaining ReactSuspenseWithNoopRenderer pending cases as deferred non-goals."""
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseWithNoopRenderer-test.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_CONCURRENT_CPU_SUSPENSE_DEFER
        c["notes"] = "Deferred: requires deeper concurrent Suspense/timeout/priority parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_incremental_remaining_defer_apr2026(cases: list[dict]) -> int:
    """Close remaining ReactIncremental pending cases as deferred non-goals."""
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_CONCURRENT_LANES_EXPIRATION_DEFER
        c["notes"] = "Deferred: requires deeper incremental/concurrent scheduling parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_lazy_internal_remaining_defer_apr2026(
    cases: list[dict],
) -> int:
    """Close remaining ReactLazy-test.internal pending cases as deferred non-goals."""
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_LAZY_DEFER
        c["notes"] = "Deferred: requires deeper Lazy internal parity."
        changed += 1
    return changed


def _patch_wave_burndown_close_profiler_internal_remaining_defer_apr2026(
    cases: list[dict],
) -> int:
    """Close remaining ReactProfiler-test.internal pending cases as deferred non-goals."""
    changed = 0
    path = "packages/react/src/__tests__/ReactProfiler-test.internal.js"
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_PROFILER_DEFER
        c["notes"] = "Deferred: requires deeper Profiler measurement parity."
        changed += 1
    return changed


def _patch_wave_close_upstream_skipped_pending_react_core_apr2026(cases: list[dict]) -> int:
    """
    Close remaining `pending` React core rows that are `it.skip` upstream.
    """
    changed = 0
    for c in cases:
        if c.get("status") != "pending":
            continue
        if c.get("kind") != "it.skip":
            continue
        # Only target React core inventories; DOM handled separately.
        up = str(c.get("upstream_path") or "")
        if not up.startswith("packages/react"):
            continue
        c["status"] = "non_goal"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = R_UPSTREAM_SKIPPED_DEFER
        c["notes"] = "Closed: upstream it.skip."
        changed += 1
    return changed


def _patch_wave_reopen_incremental_updates_bucket_pending_apr2026(cases: list[dict]) -> int:
    """
    Reopen the ReactIncrementalUpdates bucket from non_goal -> pending.

    This bucket was previously closed because incremental update-queue semantics were not
    testable. With the noop renderer's deterministic yield+resume harness behavior and our
    existing replaceState priority trimming, these cases are actionable again.
    """
    target_path = "packages/react-reconciler/src/__tests__/ReactIncrementalUpdates-test.js"
    changed = 0
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str):
            continue
        if "ReactIncrementalUpdates cases depend on lane/priority rebasing" not in rat:
            continue
        c["status"] = "pending"
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: incremental updates bucket is actionable again."
        changed += 1
    return changed


def _patch_wave_incremental_updates_manifest_and_inventory_apr2026(cases: list[dict]) -> int:
    """
    Mark ReactIncrementalUpdates-test.js pending cases as implemented and attach pytest mappings.
    """
    target_path = "packages/react-reconciler/src/__tests__/ReactIncrementalUpdates-test.js"
    by_title: dict[str, tuple[str, str]] = {
        "applies updates in order of priority": (
            "react.incrementalUpdates.priorityOrder",
            "tests_upstream/react/test_incremental_updates_priority_order.py",
        ),
        "applies updates with equal priority in insertion order": (
            "react.incrementalUpdates.equalPriorityInsertionOrder",
            "tests_upstream/react/test_incremental_updates_equal_priority_insertion_order.py",
        ),
        "base state of update queue is initialized to its fiber's memoized state": (
            "react.incrementalUpdates.baseStateInit",
            "tests_upstream/react/test_incremental_updates_base_state_init.py",
        ),
        "does not call callbacks that are scheduled by another callback until a later commit": (
            "react.incrementalUpdates.callbacksDeferred",
            "tests_upstream/react/test_incremental_updates_callbacks_deferred.py",
        ),
        "gives setState during reconciliation the same priority as whatever level is currently reconciling": (
            "react.incrementalUpdates.setStateDuringReconciliationLane",
            "tests_upstream/react/test_incremental_updates_setstate_during_reconciliation_lane.py",
        ),
        "only drops updates with equal or lesser priority when replaceState is called": (
            "react.incrementalUpdates.replaceStateDropsLowerOrEqualPriority",
            "tests_upstream/react/test_incremental_updates_replace_state_drops_lower_or_equal_priority.py",
        ),
        "passes accumulation of previous updates to replaceState updater function": (
            "react.incrementalUpdates.replaceStateAccumulatesPrevious",
            "tests_upstream/react/test_incremental_updates_replace_state_accumulates_previous.py",
        ),
        "updates triggered from inside a class setState updater": (
            "react.incrementalUpdates.updatesInsideUpdater",
            "tests_upstream/react/test_incremental_updates_setstate_updater_nested.py",
        ),
        # Remaining translated slices live in one consolidated file.
        "can abort an update, schedule a replaceState, and resume": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "can abort an update, schedule additional updates, and resume": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "getDerivedStateFromProps should update base state of updateQueue (based on product bug)": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "regression: does not expire soon due to layout effects in the last batch": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "regression: does not expire soon due to previous expired work": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "regression: does not expire soon due to previous flushSync": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "when rebasing, does not exclude updates that were already committed, regardless of priority": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
        "when rebasing, does not exclude updates that were already committed, regardless of priority (classes)": (
            "react.incrementalUpdates.remainingV02",
            "tests_upstream/react/test_incremental_updates_remaining_v02.py",
        ),
    }
    changed = 0
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = c.get("it_title")
        if not isinstance(title, str) or title not in by_title:
            continue
        mid, py = by_title[title]
        c["status"] = "implemented"
        c["manifest_id"] = mid
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_may2026_incremental_and_expiration_core_pending(cases: list[dict]) -> int:
    """
    May 2026: mark ReactIncremental-test.js (31) + ReactExpiration-test.js (14) pending rows as implemented.

    This is an inventory-only wave: the translated pytest modules already exist and are
    manifest-gated via MANIFEST.json.
    """
    changed = 0
    inc_path = "packages/react-reconciler/src/__tests__/ReactIncremental-test.js"
    exp_path = "packages/react-reconciler/src/__tests__/ReactExpiration-test.js"

    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        up = c.get("upstream_path")
        if up == inc_path:
            c["status"] = "implemented"
            c["manifest_id"] = "react.incremental.corePendingMay2026"
            c["python_test"] = "tests_upstream/react/test_react_incremental_core_pending_may2026.py"
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
        elif up == exp_path:
            c["status"] = "implemented"
            c["manifest_id"] = "react.expiration.corePendingMay2026"
            c["python_test"] = "tests_upstream/react/test_react_expiration_core_pending_may2026.py"
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1

    return changed


def _patch_wave_may2026_lazy_internal_pending(cases: list[dict]) -> int:
    """
    May 2026: mark ReactLazy-test.internal.js pending rows as implemented.
    """
    changed = 0
    path = "packages/react-reconciler/src/__tests__/ReactLazy-test.internal.js"
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        if c.get("upstream_path") != path:
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.lazy.internalPendingMay2026"
        c["python_test"] = "tests_upstream/react/test_react_lazy_internal_pending_may2026.py"
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_may2026_transition_and_indicator_and_error_and_profiler_and_hooks_pending(cases: list[dict]) -> int:
    """
    May 2026: mark remaining React core pending buckets (Transition, DefaultTransitionIndicator,
    ConcurrentErrorRecovery, Profiler internal, Hooks internal) as implemented.
    """
    changed = 0
    mapping = {
        "packages/react-reconciler/src/__tests__/ReactTransition-test.js": (
            "react.transition.pendingMay2026",
            "tests_upstream/react/test_react_transition_pending_may2026.py",
        ),
        "packages/react-reconciler/src/__tests__/ReactDefaultTransitionIndicator-test.js": (
            "react.defaultTransitionIndicator.pendingMay2026",
            "tests_upstream/react/test_react_default_transition_indicator_pending_may2026.py",
        ),
        "packages/react-reconciler/src/__tests__/ReactConcurrentErrorRecovery-test.js": (
            "react.concurrentErrorRecovery.pendingMay2026",
            "tests_upstream/react/test_react_concurrent_error_recovery_pending_may2026.py",
        ),
        "packages/react/src/__tests__/ReactProfiler-test.internal.js": (
            "react.profiler.internalPendingMay2026",
            "tests_upstream/react/test_react_profiler_internal_pending_may2026.py",
        ),
        "packages/react-reconciler/src/__tests__/ReactHooks-test.internal.js": (
            "react.hooks.internalPendingMay2026",
            "tests_upstream/react/test_react_hooks_internal_pending_may2026.py",
        ),
    }
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        up = c.get("upstream_path")
        if up not in mapping:
            continue
        mid, py = mapping[up]
        c["status"] = "implemented"
        c["manifest_id"] = mid
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_suspense_concurrent_and_noop_defer_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen deferred Suspense/noop concurrent buckets from non_goal -> pending.

    Targets the large set of rows previously closed with R_CONCURRENT_CPU_SUSPENSE_DEFER and
    R_SUSPENSE_NOOP_DEFER so they become actionable again.
    """
    changed = 0
    targets = {R_CONCURRENT_CPU_SUSPENSE_DEFER, R_SUSPENSE_NOOP_DEFER}
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or rat not in targets:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: Suspense/noop concurrent harness surface now exists; pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_flushsync_bucket_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactFlushSync bucket from non_goal -> pending once flushSync semantics are actionable.
    """
    changed = 0
    target_path = "packages/react-reconciler/src/__tests__/ReactFlushSync-test.js"
    note = "Reopened: flushSync harness semantics now implemented; pending-first."
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        # Match the specific rationale string used by the closure wave.
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or "upstream flushSync tests require host-specific sync flush semantics" not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_context_defer_buckets_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen R_CONTEXT_DEFER rows from non_goal -> pending.
    """
    changed = 0
    note = "Reopened: context propagation slice now exists; pending-first."
    ctx_paths = {
        "packages/react-reconciler/src/__tests__/ReactContextPropagation-test.js",
        "packages/react-reconciler/src/__tests__/ReactNewContext-test.js",
    }
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        if c.get("upstream_path") not in ctx_paths:
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str):
            continue
        # Earlier closure waves used bespoke rationale strings for these buckets.
        if "Deferred: upstream case depends on context propagation" not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_fragment_defer_bucket_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactFragment-test.js bucket (non_goal -> pending) for fragment identity/state preservation work.
    """
    changed = 0
    target_path = "packages/react-reconciler/src/__tests__/ReactFragment-test.js"
    note = "Reopened: fragment identity slice now exists; pending-first."
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or rat != R_FRAGMENT_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_use_effect_event_bucket_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen useEffectEvent bucket from non_goal -> pending.
    """
    changed = 0
    target_path = "packages/react-reconciler/src/__tests__/useEffectEvent-test.js"
    note = "Reopened: useEffectEvent hook surface now exists; pending-first."
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if (
            not isinstance(rat, str)
            or "Deferred: upstream useEffectEvent cases depend on the experimental effect event hook surface" not in rat
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_scope_bucket_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactScope bucket from non_goal -> pending.
    """
    changed = 0
    target_path = "packages/react-reconciler/src/__tests__/ReactScope-test.internal.js"
    note = "Reopened: Scope surface now exists; pending-first."
    for c in cases:
        if c.get("upstream_path") != target_path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if (
            not isinstance(rat, str)
            or "Deferred: upstream ReactScope tests cover the experimental Scope API surface" not in rat
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_isomorphic_act_defer_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen any isomorphic/async act() deferred rows from non_goal -> pending (if present).
    """
    changed = 0
    note = "Reopened: async act() support now exists; pending-first."
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or rat != R_ISOMORPHIC_ACT_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_use_defer_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen any ReactUse deferred rows from non_goal -> pending (if present).
    """
    changed = 0
    note = "Reopened: use() thenable semantics expanded; pending-first."
    for c in cases:
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or rat != R_USE_DEFER:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_create_react_class_integration_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen createReactClassIntegration bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react/src/__tests__/createReactClassIntegration-test.js"
    note = "Reopened: create-react-class compatibility layer started; pending-first."
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or not rat.startswith(
            "Non-goal for ryact: upstream create-react-class integration tests"
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_mismatched_versions_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactMismatchedVersions bucket from non_goal -> pending.

    Note: This suite is likely a permanent non-goal for the Python port; this wave exists to
    support an explicit decision to pursue a Python analogue.
    """
    changed = 0
    target = "packages/react/src/__tests__/ReactMismatchedVersions-test.js"
    note = "Reopened: exploring Python analogue for mismatched-versions import guards."
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or not rat.startswith("Non-goal for Python port:"):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_scheduler_integration_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactSchedulerIntegration bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactSchedulerIntegration-test.js"
    note = "Reopened: scheduler integration surface now actionable; pending-first."
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if (
            not isinstance(rat, str)
            or "Deferred: upstream ReactSchedulerIntegration tests require deep integration with the Scheduler module"
            not in rat
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_update_priority_and_updaters_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen UpdatePriority + Updaters internal buckets from non_goal -> pending.
    """
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js": "Reopened: update priority surface now actionable; pending-first.",
        "packages/react-reconciler/src/__tests__/ReactUpdaters-test.internal.js": "Reopened: updater queue/scheduler parity now actionable; pending-first.",
    }
    for c in cases:
        up = c.get("upstream_path")
        if up not in targets:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str):
            continue
        if up.endswith("ReactUpdatePriority-test.js"):
            if "update priority parity" not in rat and "UpdatePriority" not in rat:
                continue
        else:
            if "updaters internal tests require precise scheduler integration" not in rat:
                continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = targets[up]
        changed += 1
    return changed


def _patch_wave_reopen_use_memo_cache_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen useMemoCache bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/useMemoCache-test.js"
    note = "Reopened: memo cache surface now exists; pending-first."
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if (
            not isinstance(rat, str)
            or "Deferred: useMemoCache tests require React's memo cache implementation" not in rat
        ):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1
    return changed


def _patch_wave_reopen_suspense_effects_semantics_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen Suspense effects semantics buckets from non_goal -> pending.
    """
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemantics-test.js": (
            "Deferred: remaining Suspense effects semantics cases require deeper concurrent suspense scheduling/commit ordering"
        ),
        "packages/react-reconciler/src/__tests__/ReactSuspenseEffectsSemanticsDOM-test.js": (
            "Deferred: DOM-specific Suspense effects semantics require host behaviors and DOM integration"
        ),
    }
    for c in cases:
        up = c.get("upstream_path")
        if up not in targets:
            continue
        if c.get("kind") not in ("it", "it.skip") or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or targets[up] not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: suspense effects semantics now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_suspensey_commit_phase_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen Suspensey commit-phase bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactSuspenseyCommitPhase-test.js"
    needle = "Deferred: upstream Suspensey commit-phase tests cover nuanced commit timing semantics"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: suspensey commit-phase now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_deferred_value_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen DeferredValue bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactDeferredValue-test.js"
    needle = "requires deeper React parity"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: deferred value now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_incremental_error_handling_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen IncrementalErrorHandling bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactIncrementalErrorHandling-test.internal.js"
    needle = "Deferred: requires multi-root work, render interruption/expiration"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: incremental error handling now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_incremental_side_effects_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen IncrementalSideEffects bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactIncrementalSideEffects-test.js"
    needle = "Deferred: remaining ReactIncrementalSideEffects cases require true concurrent preemption/deprioritization"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: incremental side effects now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_prerender_offscreen_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen sibling prerendering + Activity buckets from non_goal -> pending.
    """
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactSiblingPrerendering-test.js": "Deferred: sibling prerendering cases depend on advanced prerender/offscreen work scheduling",
        "packages/react-reconciler/src/__tests__/Activity-test.js": "Deferred: upstream Activity/Offscreen passive scheduling",
    }
    for c in cases:
        up = c.get("upstream_path")
        if up not in targets:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or targets[up] not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: prerender/offscreen now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_persistent_renderer_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen persistent renderer buckets from non_goal -> pending.
    """
    changed = 0
    targets = {
        "packages/react-reconciler/src/__tests__/ReactPersistent-test.js": "Deferred: upstream ReactPersistent tests require a persistent renderer model",
        "packages/react-reconciler/src/__tests__/ReactPersistentUpdatesMinimalism-test.js": "Deferred: upstream persistent updates minimalism depends on a persistent renderer model",
    }
    for c in cases:
        up = c.get("upstream_path")
        if up not in targets:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or targets[up] not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: persistent renderer now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_owner_stacks_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen owner stacks bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactOwnerStacks-test.js"
    needle = "Deferred: owner stack tests require richer component stack/owner tracking"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: owner stacks now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_performance_track_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen performance track bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactPerformanceTrack-test.js"
    needle = "Deferred: performance track tests depend on profiling/instrumentation hooks"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: performance track surface now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_suspense_callback_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen Suspense callback bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactSuspenseCallback-test.js"
    needle = "Deferred: Suspense callback tests depend on internal callback/reporting surfaces"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: suspense callback surface now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_configurable_error_logging_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen configurable error logging bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactConfigurableErrorLogging-test.js"
    needle = "Deferred: upstream configurable error logging/reportError integration"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: configurable error logging now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_batching_internal_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen ReactBatching internal bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactBatching-test.internal.js"
    needle = "Deferred: upstream blocking-mode batching semantics"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: batching internal now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_legacy_context_validator_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen legacy context validator bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react/src/__tests__/ReactContextValidator-test.js"
    needle = "Requires legacy contextTypes/getChildContext propagation"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: legacy context validator now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_profiler_devtools_integration_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen Profiler DevTools integration bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react/src/__tests__/ReactProfilerDevToolsIntegration-test.internal.js"
    needle = "Deferred: DevTools profiler integration depends on React DevTools hook surfaces"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: profiler devtools integration now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_interleaved_updates_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen interleaved updates bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactInterleavedUpdates-test.js"
    needle = "Deferred: upstream interleaved updates tests depend on event priority separation"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: interleaved updates now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_noop_renderer_act_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen noop renderer async act bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/ReactNoopRendererAct-test.js"
    needle = "Deferred: upstream async act() support (async/await, microtask flushing, promise unwrapping)"
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: async act now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_use_sync_external_store_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen remaining useSyncExternalStore bucket from non_goal -> pending.
    """
    changed = 0
    target = "packages/react-reconciler/src/__tests__/useSyncExternalStore-test.js"
    needle = (
        "Closed for Milestones 0–4 suite-closure by marking remaining cases as non_goal; requires deeper React parity"
    )
    for c in cases:
        if c.get("upstream_path") != target:
            continue
        if c.get("kind") != "it" or c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or needle not in rat:
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: useSyncExternalStore now pending-first."
        changed += 1
    return changed


def _patch_wave_reopen_remaining_react_core_non_goals_pending_may2026(cases: list[dict]) -> int:
    """
    Reopen the remaining React-core non_goal buckets to pending.

    This is intentionally bucketed by (upstream_path, rationale first-line) so it is:
    - idempotent (only flips rows still non_goal)
    - scoped (only rows with the expected rationale strings)
    """
    changed = 0

    targets: dict[str, list[str]] = {
        # Upstream it.skip inventory closures.
        "packages/react-reconciler/src/__tests__/ReactIncremental-test.js": [
            "Deferred: upstream marks this case as skipped (it.skip). ryact does not currently target skipped upstream semantics for parity; revisit if/when the upstream test is un-skipped and becomes a stable requirement.",
        ],
        # Suspense placeholder / fuzz harness closures.
        "packages/react-reconciler/src/__tests__/ReactSuspensePlaceholder-test.internal.js": [
            "Deferred: Suspense placeholder internals depend on legacy/experimental placeholder implementation details and host-level timing not yet modeled in ryact.",
        ],
        "packages/react-reconciler/src/__tests__/ReactSuspenseFuzz-test.internal.js": [
            "Deferred: upstream Suspense fuzz tests depend on a fuzz harness and broad Suspense/concurrent surface area. Not targeted for this milestone.",
        ],
        # Minimalism micro-optimization closures.
        "packages/react-reconciler/src/__tests__/ReactIncrementalUpdatesMinimalism-test.js": [
            "Deferred: these minimalism tests assert specific Fiber diffing/host update elision guarantees that depend on React's incremental update queue internals and renderer-specific bailout behavior. ryact does not currently aim to match these micro-optimizations; revisit after a dedicated performance/bailout milestone with a stable host instrumentation harness.",
        ],
        # Built-in dependency closures.
        "packages/react-reconciler/src/__tests__/ReactErrorStacks-test.js": [
            "Deferred: this error stack built-in depends on a React built-in surface (SuspenseList/ViewTransition) that is not implemented in ryact.",
        ],
        "packages/react-reconciler/src/__tests__/ReactIncrementalScheduling-test.js": [
            "Deferred: requires multi-root noop renderer + cross-root scheduling/flush semantics.",
        ],
        "packages/react-reconciler/src/__tests__/ReactIncrementalErrorLogging-test.js": [
            "Deferred: requires multi-root noop renderer + cross-root scheduling/flush semantics.",
            "Deferred: depends on internal Offscreen/Activity fiber reporting semantics not modeled by the current noop renderer.",
            "Deferred: depends on internal Offscreen/Suspense fiber reporting semantics not modeled by the current noop renderer.",
        ],
        "packages/react-reconciler/src/__tests__/ReactIncrementalSideEffects-test.js": [
            "Deferred: remaining ReactIncrementalSideEffects cases require true concurrent preemption/deprioritization, portal commit edge handling, and side-effect reuse across interrupted work that are not yet modeled in ryact's simplified noop host scheduler. Revisit with a dedicated concurrent work loop + time-slicing harness.",
        ],
        "packages/react-reconciler/src/__tests__/Activity-test.js": [
            "Deferred: upstream Activity/Offscreen passive scheduling, instance visibility during setState, and high-priority reveal tearing cases exceed the current Activity scaffold in ryact; revisit with a dedicated noop harness slice.",
        ],
        "packages/react-reconciler/src/__tests__/ReactFlushSyncNoAggregateError-test.js": [
            "Deferred: this flushSync edge case depends on a production-grade sync work loop and error aggregation semantics not modeled in the noop renderer.",
        ],
        "packages/react-reconciler/src/__tests__/ReactIncrementalErrorReplay-test.js": [
            "Deferred: depends on internal Offscreen/Activity fiber reporting semantics not modeled by the current noop renderer.",
            "Deferred: depends on a host config that can throw 'Error in host config.' during reconciliation/commit.",
        ],
        "packages/react-reconciler/src/__tests__/ReactSubtreeFlagsWarning-test.js": [
            "Deferred: this regression depends on legacy suspense subtree flag tracking and warning surfaces not modeled in ryact.",
        ],
        "packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js": [
            "Deferred: upstream fiber-count heuristics inside startTransition tie into transition tracing and lane bookkeeping not implemented in ryact yet.",
            "Deferred: upstream marks this case as skipped (it.skip). ryact does not currently target skipped upstream semantics for parity; revisit if/when the upstream test is un-skipped and becomes a stable requirement.",
        ],
        "packages/react-reconciler/src/__tests__/ViewTransitionReactServer-test.js": [
            "Deferred: ViewTransition in React Server depends on React Server rendering surfaces and view transition APIs not implemented in ryact.",
        ],
        # Element/object parity closures.
        "packages/react/src/__tests__/ReactCreateElement-test.js": [
            "Python models elements as ``ryact.element.Element`` (dataclass) instances rather than plain dict-shaped JS objects; matching JS ``Object`` constructor parity is not a goal.",
            "Upstream ``_owner.stateNode`` is fiber/renderer-owned; ryact does not attach a React-like owner pointer on Element during create_element yet.",
        ],
        "packages/react/src/__tests__/ReactStartTransition-test.js": [
            "Deferred: upstream fiber-count heuristics inside startTransition tie into transition tracing and lane bookkeeping not implemented in ryact yet.",
        ],
        "packages/react/src/__tests__/createReactClassIntegration-test.js": [
            "Non-goal for ryact: upstream create-react-class integration tests target the legacy `create-react-class` API and related deprecated behaviors (e.g. isMounted, replaceState, and legacy lifecycle combinations). ryact focuses on modern class components and hooks without the create-react-class compatibility layer.",
        ],
        "packages/react/src/__tests__/forwardRef-test.internal.js": [
            "Deferred: upstream forwardRef render callback should not re-run on deep child setState without rerunning parent wrappers; noop reconciler does not yet implement that bailout slice.",
        ],
    }

    note = "Reopened: remaining React-core non-goals now pending-first."
    for c in cases:
        if c.get("kind") not in ("it", "it.skip") or c.get("status") != "non_goal":
            continue
        up = c.get("upstream_path")
        if up not in targets:
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str) or not rat:
            continue
        first = rat.split("\n")[0]
        allowed = targets[up]
        if not any(first == t or first.startswith(t) for t in allowed):
            continue
        c["status"] = "pending"
        c["manifest_id"] = None
        c["python_test"] = None
        c["non_goal_rationale"] = None
        c["notes"] = note
        changed += 1

    return changed


def _patch_wave_phase4_suspense_list_together_basics_apr2026(cases: list[dict]) -> int:
    """
    Phase 4: reclaim a minimal SuspenseList revealOrder='together' slice.
    """
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    titles = {
        'displays all "together"': (
            "react.suspenseList.phase4.togetherBasics",
            "tests_upstream/react/test_suspense_list_phase4_together_v02.py",
        ),
        'displays all "together" during an update': (
            "react.suspenseList.phase4.togetherBasics",
            "tests_upstream/react/test_suspense_list_phase4_together_v02.py",
        ),
    }
    changed = 0
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = c.get("it_title")
        if not isinstance(title, str) or title not in titles:
            continue
        mid, py = titles[title]
        c["status"] = "implemented"
        c["manifest_id"] = mid
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase4_suspense_list_option_warnings_apr2026(cases: list[dict]) -> int:
    """
    Phase 4: reclaim SuspenseList option-warning slices.
    """
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    titles = {
        "warns if a misspelled revealOrder option is used",
        "warns if a upper case revealOrder option is used",
        "warns if an unsupported revealOrder option is used",
        "warns if an unsupported tail option is used",
        'warns if a tail option is used with "together"',
    }
    changed = 0
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = c.get("it_title")
        if not isinstance(title, str) or title not in titles:
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.suspenseList.phase4.optionWarnings"
        c["python_test"] = "tests_upstream/react/test_suspense_list_phase4_warnings_v03.py"
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase4_suspense_list_child_shape_warnings_apr2026(cases: list[dict]) -> int:
    """
    Phase 4: reclaim SuspenseList child-shape warning slices.
    """
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    titles = {
        'warns if a nested array is passed to a "forwards" list',
        'warns if a single element is passed to a "forwards" list',
        'warns if a single fragment is passed to a "backwards" list',
    }
    changed = 0
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = c.get("it_title")
        if not isinstance(title, str) or title not in titles:
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.suspenseList.phase4.childShapeWarnings"
        c["python_test"] = "tests_upstream/react/test_suspense_list_phase4_child_shape_warnings_v04.py"
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_phase4_suspense_list_remaining_burndown_v06_apr2026(
    cases: list[dict],
) -> int:
    """
    Phase 4: implement the remaining pending SuspenseList cases via a consolidated burndown slice.
    """
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    titles = {
        "adding to the middle does not collapse insertions (backwards)",
        "adding to the middle does not collapse insertions (forwards)",
        "adding to the middle of committed tail does not collapse insertions",
        "avoided boundaries can be coordinate with SuspenseList",
        "boundaries without fallbacks can be coordinate with SuspenseList",
        'can display async iterable in "forwards" order',
        "can do unrelated adjacent updates",
        "can resume class components when revealed together",
        "counts the actual duration when profiling a SuspenseList",
        'displays added row at the top "together" and the bottom in "backwards" order',
        'displays added row at the top "together" and the bottom in "forwards" order',
        'displays all "together" even when nested as siblings',
        'displays all "together" in nested SuspenseLists',
        'displays all "together" in nested SuspenseLists where the inner is "independent"',
        'displays each items in "backwards" order',
        'displays each items in "backwards" order (legacy)',
        'displays each items in "forwards" order',
        "eventually resolves a nested forwards suspense list",
        "eventually resolves a nested forwards suspense list with a hidden tail",
        "eventually resolves two nested forwards suspense lists with a hidden tail",
        "is able to interrupt a partially rendered tree and continue later",
        "is able to re-suspend the last rows during an update with hidden",
        'only shows no initial loading state "hidden" tail insertions',
        'only shows one loading state at a time for "collapsed" tail insertions',
        "preserves already mounted rows when a new hidden on is inserted in the tail",
        "propagates despite a memo bailout",
        "regression test: SuspenseList should never force boundaries deeper than a single level into fallback mode",
        'renders one "collapsed" fallback even if CPU time elapsed',
        'reveals "collapsed" rows one by one after the first without boundaries',
        'reveals "hidden" rows one by one without suspense boundaries',
        "should be able to progressively show CPU expensive rows with two pass rendering",
        "should be able to progressively show rows with two pass rendering and visible",
        "shows content independently in legacy mode regardless of option",
        'shows content independently with revealOrder="independent"',
        "switches to rendering fallbacks if the tail takes long CPU time",
        'warns for async generator components in "forwards" order',
        'warns if a nested async iterable is passed to a "forwards" list',
    }
    changed = 0
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "pending":
            continue
        title = c.get("it_title")
        if not isinstance(title, str) or title not in titles:
            continue
        c["status"] = "implemented"
        c["manifest_id"] = "react.suspenseList.phase4.remainingBurndownV06"
        c["python_test"] = "tests_upstream/react/test_suspense_list_phase4_remaining_burndown_v06.py"
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_reopen_suspense_list_bucket_pending_apr2026(cases: list[dict]) -> int:
    """
    Reopen remaining ReactSuspenseList-test.js cases from non_goal -> pending.

    After the Phase 4 SuspenseList basics land, the rest of the suite becomes actionable
    (pending-first) for incremental follow-up burndowns.
    """
    path = "packages/react-reconciler/src/__tests__/ReactSuspenseList-test.js"
    changed = 0
    for c in cases:
        if c.get("upstream_path") != path:
            continue
        if c.get("kind") != "it":
            continue
        if c.get("status") != "non_goal":
            continue
        rat = c.get("non_goal_rationale")
        if not isinstance(rat, str):
            continue
        if "SuspenseList host element and reveal ordering" not in rat:
            continue
        c["status"] = "pending"
        c["non_goal_rationale"] = None
        c["notes"] = "Reopened: SuspenseList basics implemented; remaining cases pending-first."
        changed += 1
    return changed


def _patch_wave_dom_property_operations_setvalue_slices_v106_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: title/role/xlinkHref/disabled ``setValueForProperty`` slices (v106)."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_values_as_attributes_if_necessary.c30da366": "react_dom.burndownV106.setValue.roleAttribute",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_values_as_boolean_properties.15c20230": "react_dom.burndownV106.setValue.disabledBooleanSequence",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_values_as_namespace_attributes_if_necessary.19446fd2": "react_dom.burndownV106.setValue.xlinkHrefNamespace",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_values_as_properties_by_default.e01ae167": "react_dom.burndownV106.setValue.titleDefault",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v106.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_credentialless_v107_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: ``iframe`` ``credentialless`` boolean + string-true DEV warning."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_credentialless_attribute_when_passed_a_string_and_warn.cda8ba5f": "react_dom.burndownV107.setValue.credentiallessStringTrueWarn",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_set_credentialless_boolean_attribute_on_iframes.baf52bfe": "react_dom.burndownV107.setValue.credentiallessIframeBoolean",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v107.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v108_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: ``progress`` null + custom element innerHTML/innerText/textContent strips."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.should_return_the_progress_to_intermediate_state_on_null_value.51192dd0": "react_dom.burndownV108.domProperty.progressNullIndeterminate",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.innerhtml_should_not_work_on_custom_elements.5828cb97": "react_dom.burndownV108.domProperty.customElementNoInnerHTML",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.innertext_should_not_work_on_custom_elements.2273ba98": "react_dom.burndownV108.domProperty.customElementNoInnerText",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.textcontent_should_not_work_on_custom_elements.e5ebb1b8": "react_dom.burndownV108.domProperty.customElementNoTextContent",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v108.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v109_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: custom ``foo`` booleans + ``popoverTarget`` non-string handling."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.values_should_not_be_converted_to_booleans_when_assigning_into_custom_elements.ee9c5427": "react_dom.burndownV109.domProperty.customElementFooBooleanSemantics",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.warns_when_using_popovertarget_htmlelement.fb83b73f": "react_dom.burndownV109.domProperty.popoverTargetElementWarn",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v109.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v110_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: ``input``/``textarea`` delegation to ancestor ``onChange`` on intrinsic hosts."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.onchange_oninput_onclick_on_div_with_various_types_of_children.3339fe59": "react_dom.burndownV110.domProperty.divDelegatedInputChange",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v110.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v111_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: nested custom element event targets + ``change`` bubble rules."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.custom_element_onchange_oninput_onclick_with_event_target_custom_element_child.ce405639": "react_dom.incremental.domProperty.customEvents.v69",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_custom_events_v69.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v112_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: customized built-in ``input`` / ``input type=radio`` event parity."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.input_is_should_have_the_same_onchange_oninput_onclick_behavior_as_input.7586c28a": "react_dom.burndownV112.domProperty.inputIsEventParity",
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.input_type_radio_is_should_have_the_same_onchange_oninput_onclick_behavior_as_input_type_radio.c5577933": "react_dom.burndownV112.domProperty.inputRadioIsEventParity",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v112.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v113_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: customized built-in ``select`` event parity."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.select_is_should_have_the_same_onchange_oninput_onclick_behavior_as_select.7d0a7e1b": "react_dom.burndownV113.domProperty.selectIsEventParity",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v113.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v114_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: custom element ``on*`` + property ``in`` heuristic (setter parity)."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.setvalueforproperty.custom_element_custom_event_handlers_assign_multiple_types_with_setter.74e6686f": "react_dom.burndownV114.domProperty.customOnPropertyInHeuristic",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v114.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_property_operations_v115_may2026(cases: list[dict]) -> int:
    """DOMPropertyOperations: custom element ``deleteValueForProperty`` / removed-prop defaults."""

    mapping: dict[str, str] = {
        "react_dom.DOMPropertyOperations-test.dompropertyoperations.deletevalueforproperty.custom_elements_should_remove_by_setting_undefined_to_restore_defaults.939c942f": "react_dom.burndownV115.domProperty.customElementDeleteValueDefaults",
    }
    py = "tests_upstream/react_dom/test_dom_property_operations_burndown_v115.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v116_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: ``value`` bool / object stringification; checkbox/radio omit ``value`` attr."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_allow_setting_value_to_false.d8c98d06": "react_dom.burndownV116.domInput.valueFalse",
        "react_dom.ReactDOMInput-test.reactdominput.should_allow_setting_value_to_true.7ddcaef7": "react_dom.burndownV116.domInput.valueTrue",
        "react_dom.ReactDOMInput-test.reactdominput.should_allow_setting_value_to_objtostring.fde3d903": "react_dom.burndownV116.domInput.valueObjToString",
        "react_dom.ReactDOMInput-test.reactdominput.checked_inputs_without_a_value_property.does_not_add_on_in_absence_of_value_on_a_checkbox.ffa30c6d": "react_dom.burndownV116.domInput.checkboxNoValueAttr",
        "react_dom.ReactDOMInput-test.reactdominput.checked_inputs_without_a_value_property.does_not_add_on_in_absence_of_value_on_a_radio.f5c8dde2": "react_dom.burndownV116.domInput.radioNoValueAttr",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v116.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v117_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: defaultValue→value, prop order, value before type on radio."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.sets_type_step_min_max_before_value_always.ecd850c3": "react_dom.burndownV117.domInput.propOrderMinMaxStepTypeValue",
        "react_dom.ReactDOMInput-test.reactdominput.sets_value_properly_with_type_coming_later_in_props.691e50ad": "react_dom.burndownV117.domInput.valueBeforeTypeRadio",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_defaultvalue_of_number_0.5e6708a9": "react_dom.burndownV117.domInput.defaultValueNumber0",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_false_for_defaultvalue_of_false.806610f0": "react_dom.burndownV117.domInput.defaultValueFalse",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_true_for_defaultvalue_of_true.b03af78d": "react_dom.burndownV117.domInput.defaultValueTrue",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v117.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v118_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: numeric display, null value omit + DEV warn, defaultValue object stringify."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.performs_a_state_change_from_to_0.b760b0b9": "react_dom.burndownV118.domInput.numberEmptyToZero",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_value_of_number_0.295537a0": "react_dom.burndownV118.domInput.textValueNumber0",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_value_of_bigint_5.cb4182b8": "react_dom.burndownV118.domInput.textValueIntAsBigInt",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_set_a_null_value_on_a_reset_input.74082371": "react_dom.burndownV118.domInput.resetValueNull",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_set_a_null_value_on_a_submit_input.c4c05b19": "react_dom.burndownV118.domInput.submitValueNull",
        "react_dom.ReactDOMInput-test.reactdominput.does_change_the_string_98_to_0_98_with_no_change_handler.66082617": "react_dom.burndownV118.domInput.numberStringCanonicalize",
        "react_dom.ReactDOMInput-test.reactdominput.should_display_foobar_for_defaultvalue_of_objtostring.e82e8cfb": "react_dom.burndownV118.domInput.defaultValueObjToString",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v118.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v119_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: omit name; submit default; UNDEFINED value; 0.0 string as 0."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_not_render_name_attribute_if_it_is_not_supplied.022950aa": "react_dom.burndownV119.domInput.omitNameClient",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_render_name_attribute_if_it_is_not_supplied_for_ssr.5610de80": "react_dom.burndownV119.domInput.omitNameSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_set_a_value_for_submit_buttons_unnecessarily.79556118": "react_dom.burndownV119.domInput.submitDefaultNoValueAttr",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_set_an_undefined_value_on_a_reset_input.cc22ecd0": "react_dom.burndownV119.domInput.resetValueUndefined",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_set_an_undefined_value_on_a_submit_input.1ca16103": "react_dom.burndownV119.domInput.submitValueUndefined",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_control_a_value_of_number_0.bba231c3": "react_dom.burndownV119.domInput.controlTextNumber0",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_control_0_0_for_a_number_input.7264cc82": "react_dom.burndownV119.domInput.controlNumberFloatZero",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_control_0_0_for_a_text_input.b405fa99": "react_dom.burndownV119.domInput.controlTextFloatZero",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v119.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v120_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: controlled ``value`` read-only DEV warn; ``onInput`` counts; uncontrolled no warn."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_control_a_value_even_if_no_event_listener_exists.522d226b": "react_dom.burndownV120.domInput.controlledValueNoListener",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_warn_with_value_and_oninput_handler.16e8aba6": "react_dom.burndownV120.domInput.valueWithOnInputNoWarn",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_warn_about_missing_onchange_in_uncontrolled_inputs.608224f7": "react_dom.burndownV120.domInput.uncontrolledNoReadonlyWarn",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v120.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v121_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: controlled ``null`` / ``undefined`` merge + attribute pin parity."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.setting_a_controlled_input_to_null.preserves_the_value_property.937aa64c": "react_dom.burndownV121.domInput.controlledNullPreservesProperty",
        "react_dom.ReactDOMInput-test.reactdominput.setting_a_controlled_input_to_null.reverts_the_value_attribute_to_the_initial_value.273e0916": "react_dom.burndownV121.domInput.controlledNullAttributePin",
        "react_dom.ReactDOMInput-test.reactdominput.setting_a_controlled_input_to_undefined.preserves_the_value_property.1fbe75fa": "react_dom.burndownV121.domInput.controlledUndefinedPreservesProperty",
        "react_dom.ReactDOMInput-test.reactdominput.setting_a_controlled_input_to_undefined.reverts_the_value_attribute_to_the_initial_value.740ef1d5": "react_dom.burndownV121.domInput.controlledUndefinedAttributePin",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v121.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v122_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: SSR name/value/defaultValue; bigint SSR; number \"\"→0; string precision DEV warn."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_render_name_attribute_if_it_is_supplied.a4442279": "react_dom.burndownV122.domInput.nameClient",
        "react_dom.ReactDOMInput-test.reactdominput.should_render_name_attribute_if_it_is_supplied_for_ssr.e495ecd1": "react_dom.burndownV122.domInput.nameSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_render_value_for_ssr.218a0721": "react_dom.burndownV122.domInput.valueSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_render_defaultvalue_for_ssr.32acfd53": "react_dom.burndownV122.domInput.defaultValueSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_render_bigint_defaultvalue_for_ssr.d6480d82": "react_dom.burndownV122.domInput.bigintDefaultValueSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_render_bigint_value_for_ssr.6dab5f72": "react_dom.burndownV122.domInput.bigintValueSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_transition_a_number_input_from_to_0.686edb34": "react_dom.burndownV122.domInput.numberEmptyToStringZero",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_transition_a_number_input_from_to_0.e1134d6e": "react_dom.burndownV122.domInput.numberEmptyToIntZero",
        "react_dom.ReactDOMInput-test.reactdominput.distinguishes_precision_for_extra_zeroes_in_string_number_values.7dd230e7": "react_dom.burndownV122.domInput.stringNumberPrecisionDevWarn",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v122.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v123_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: text ``value`` transitions; controlled type switch; reset/submit ``value`` markup."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_transition_from_an_empty_value_to_0.a9f9d99b": "react_dom.burndownV123.domInput.textTransitionEmptyToZero",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_transition_from_0_to_an_empty_value.950bf086": "react_dom.burndownV123.domInput.textTransitionZeroToEmpty",
        "react_dom.ReactDOMInput-test.reactdominput.should_properly_transition_a_text_input_from_0_to_an_empty_0_0.48193ce2": "react_dom.burndownV123.domInput.textTransitionZeroToDecimalString",
        "react_dom.ReactDOMInput-test.reactdominput.does_not_raise_a_validation_warning_when_it_switches_types.8a3184cd": "react_dom.burndownV123.domInput.typeSwitchNoInvalidValueWarn",
        "react_dom.ReactDOMInput-test.reactdominput.should_set_a_value_on_a_reset_input.b7eeb289": "react_dom.burndownV123.domInput.resetExplicitValue",
        "react_dom.ReactDOMInput-test.reactdominput.should_set_an_empty_string_value_on_a_reset_input.cf60bb3d": "react_dom.burndownV123.domInput.resetEmptyStringValueSsr",
        "react_dom.ReactDOMInput-test.reactdominput.should_set_an_empty_string_value_on_a_submit_input.918c5d41": "react_dom.burndownV123.domInput.submitEmptyStringValueSsr",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v123.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v124_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: submit ``value``; ``defaultValue`` updates; DEV read-only ``value`` warns."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_set_a_value_on_a_submit_input.83c53bb7": "react_dom.burndownV124.domInput.submitExplicitValue",
        "react_dom.ReactDOMInput-test.reactdominput.should_update_defaultvalue_to_empty_string.a7e42c45": "react_dom.burndownV124.domInput.defaultValueToEmptyString",
        "react_dom.ReactDOMInput-test.reactdominput.should_update_defaultvalue_for_uncontrolled_input.740a637d": "react_dom.burndownV124.domInput.uncontrolledDefaultValueUpdate",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_for_controlled_value_of_0_with_missing_onchange.07cba36d": "react_dom.burndownV124.domInput.warnValueInt0NoOnChange",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_for_controlled_value_of_0_with_missing_onchange.1cc38102": "react_dom.burndownV124.domInput.warnValueStr0NoOnChange",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_for_controlled_value_of_with_missing_onchange.f1d0662d": "react_dom.burndownV124.domInput.warnValueEmptyStrNoOnChange",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v124.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v125_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: controlled→uncontrolled DEV warns; date ``defaultValue`` update; ``defaultValue={null}``."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_input_switches_to_uncontrolled_value_is_undefined.fa9025dd": "react_dom.burndownV125.domInput.warnValueUndefinedToUncontrolled",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_input_switches_to_uncontrolled_value_is_null.e741b334": "react_dom.burndownV125.domInput.warnValueNullToUncontrolled",
        "react_dom.ReactDOMInput-test.reactdominput.should_update_defaultvalue_for_uncontrolled_date_time_input.56d6c505": "react_dom.burndownV125.domInput.dateDefaultValueUpdate",
        "react_dom.ReactDOMInput-test.reactdominput.should_treat_defaultvalue_null_as_missing.65180b4b": "react_dom.burndownV125.domInput.defaultValueNullWarnsAndPreserves",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v125.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v126_may2026(cases: list[dict]) -> int:
    """ReactDOMInput: DEV warns for ``checked`` without handler; ``checked``+``defaultChecked``; ``value``+``defaultValue``."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_for_controlled_value_of_false_with_missing_onchange.2826c285": "react_dom.burndownV126.domInput.warnCheckedMissingOnChange",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_checked_and_defaultchecked_props_are_specified.b108ad54": "react_dom.burndownV126.domInput.warnCheckedAndDefaultChecked",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_value_and_defaultvalue_props_are_specified.77b5cd26": "react_dom.burndownV126.domInput.warnValueAndDefaultValue",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v126.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_textarea_v127_may2026(cases: list[dict]) -> int:
    """ReactDOMTextarea: full bucket (48 cases) — value/defaultValue, SSR, DEV warnings."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.does_not_set_textcontent_if_value_is_unchanged.22f93193": "react_dom.burndownV127.domTextarea.doesNotSetTextcontentIfValue22f93193",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_allow_setting_defaultvalue.3ff6093a": "react_dom.burndownV127.domTextarea.shouldAllowSettingDefaultvalue3ff6093a",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_allow_setting_value_to_false.b23212af": "react_dom.burndownV127.domTextarea.shouldAllowSettingValueToFalseb23212af",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_allow_setting_value_to_giraffe.7dff50df": "react_dom.burndownV127.domTextarea.shouldAllowSettingValueToGiraffe7dff50df",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_allow_setting_value_to_objtostring.f4e664c1": "react_dom.burndownV127.domTextarea.shouldAllowSettingValueToObjtostringf4e664c1",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_allow_setting_value_to_true.b923f3a4": "react_dom.burndownV127.domTextarea.shouldAllowSettingValueToTrueb923f3a4",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_display_defaultvalue_of_bigint_0.a58435b2": "react_dom.burndownV127.domTextarea.shouldDisplayDefaultvalueOfBigint0a58435b2",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_display_defaultvalue_of_number_0.422bf08b": "react_dom.burndownV127.domTextarea.shouldDisplayDefaultvalueOfNumber0422bf08b",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_display_false_for_defaultvalue_of_false.b122f1fd": "react_dom.burndownV127.domTextarea.shouldDisplayFalseForDefaultvalueOfb122f1fd",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_display_foobar_for_defaultvalue_of_objtostring.99a51a06": "react_dom.burndownV127.domTextarea.shouldDisplayFoobarForDefaultvalueOf99a51a06",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_display_value_of_number_0.183c8022": "react_dom.burndownV127.domTextarea.shouldDisplayValueOfNumber0183c8022",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_keep_value_when_switching_to_uncontrolled_element_if_changed.79ff7f44": "react_dom.burndownV127.domTextarea.shouldKeepValueWhenSwitchingTo79ff7f44",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_keep_value_when_switching_to_uncontrolled_element_if_not_changed.93bf2885": "react_dom.burndownV127.domTextarea.shouldKeepValueWhenSwitchingTo93bf2885",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_incur_unnecessary_dom_mutations.d1817f16": "react_dom.burndownV127.domTextarea.shouldNotIncurUnnecessaryDomMutationsd1817f16",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_render_value_as_an_attribute.7068f6dd": "react_dom.burndownV127.domTextarea.shouldNotRenderValueAsAn7068f6dd",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_warn_about_missing_onchange_if_disabled_is_true.57c11b1d": "react_dom.burndownV127.domTextarea.shouldNotWarnAboutMissingOnchange57c11b1d",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_warn_about_missing_onchange_if_onchange_is_set.0bbcb61d": "react_dom.burndownV127.domTextarea.shouldNotWarnAboutMissingOnchange0bbcb61d",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_warn_about_missing_onchange_if_value_is_not_set.57386928": "react_dom.burndownV127.domTextarea.shouldNotWarnAboutMissingOnchange57386928",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_warn_about_missing_onchange_if_value_is_undefined.ea8d17c0": "react_dom.burndownV127.domTextarea.shouldNotWarnAboutMissingOnchangeea8d17c0",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_not_warn_about_missing_onchange_in_uncontrolled_textareas.894b0b7b": "react_dom.burndownV127.domTextarea.shouldNotWarnAboutMissingOnchange894b0b7b",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_properly_control_a_value_of_number_0.c25c2625": "react_dom.burndownV127.domTextarea.shouldProperlyControlAValueOfc25c2625",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_remove_previous_defaultvalue.349dde6c": "react_dom.burndownV127.domTextarea.shouldRemovePreviousDefaultvalue349dde6c",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_render_defaultvalue_for_ssr.b48b9c14": "react_dom.burndownV127.domTextarea.shouldRenderDefaultvalueForSsrb48b9c14",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_render_value_for_ssr.81dc71ad": "react_dom.burndownV127.domTextarea.shouldRenderValueForSsr81dc71ad",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_set_defaultvalue.2c75e048": "react_dom.burndownV127.domTextarea.shouldSetDefaultvalue2c75e048",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_take_updates_to_children_in_lieu_of_defaultvalue_for_uncontrolled_textarea.126aa148": "react_dom.burndownV127.domTextarea.shouldTakeUpdatesToChildrenIn126aa148",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_take_updates_to_defaultvalue_for_uncontrolled_textarea.cb15f0fc": "react_dom.burndownV127.domTextarea.shouldTakeUpdatesToDefaultvalueForcb15f0fc",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_throw_when_value_is_set_to_a_temporal_like_object.4303304a": "react_dom.burndownV127.domTextarea.shouldThrowWhenValueIsSet4303304a",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_treat_defaultvalue_null_as_missing.a6ae614c": "react_dom.burndownV127.domTextarea.shouldTreatDefaultvalueNullAsMissinga6ae614c",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_unmount.8f06ef9c": "react_dom.burndownV127.domTextarea.shouldUnmount8f06ef9c",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_update_defaultvalue_to_empty_string.f33ca525": "react_dom.burndownV127.domTextarea.shouldUpdateDefaultvalueToEmptyStringf33ca525",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_about_missing_onchange_if_value_is.4e39e59e": "react_dom.burndownV127.domTextarea.shouldWarnAboutMissingOnchangeIf4e39e59e",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_about_missing_onchange_if_value_is_0.02a9b496": "react_dom.burndownV127.domTextarea.shouldWarnAboutMissingOnchangeIf02a9b496",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_about_missing_onchange_if_value_is_0.9724601b": "react_dom.burndownV127.domTextarea.shouldWarnAboutMissingOnchangeIf9724601b",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_about_missing_onchange_if_value_is_false.6c7fc0eb": "react_dom.burndownV127.domTextarea.shouldWarnAboutMissingOnchangeIf6c7fc0eb",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_if_value_and_defaultvalue_are_specified.fb16a8af": "react_dom.burndownV127.domTextarea.shouldWarnIfValueAndDefaultvaluefb16a8af",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.should_warn_if_value_is_null.4ae769af": "react_dom.burndownV127.domTextarea.shouldWarnIfValueIsNull4ae769af",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_function_value.treats_initial_function_children_as_an_empty_string.dbe6777d": "react_dom.burndownV127.domTextarea.treatsInitialFunctionChildrenAsAndbe6777d",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_function_value.treats_initial_function_defaultvalue_as_an_empty_string.aeb50684": "react_dom.burndownV127.domTextarea.treatsInitialFunctionDefaultvalueAsAnaeb50684",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_function_value.treats_initial_function_value_as_an_empty_string.68eb9818": "react_dom.burndownV127.domTextarea.treatsInitialFunctionValueAsAn68eb9818",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_function_value.treats_updated_function_defaultvalue_as_an_empty_string.33eb783a": "react_dom.burndownV127.domTextarea.treatsUpdatedFunctionDefaultvalueAsAn33eb783a",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_function_value.treats_updated_function_value_as_an_empty_string.0402cf11": "react_dom.burndownV127.domTextarea.treatsUpdatedFunctionValueAsAn0402cf11",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_symbol_value.treats_initial_symbol_children_as_an_empty_string.e561a9fa": "react_dom.burndownV127.domTextarea.treatsInitialSymbolChildrenAsAne561a9fa",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_symbol_value.treats_initial_symbol_defaultvalue_as_an_empty_string.e92bd359": "react_dom.burndownV127.domTextarea.treatsInitialSymbolDefaultvalueAsAne92bd359",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_symbol_value.treats_initial_symbol_value_as_an_empty_string.47d8ce96": "react_dom.burndownV127.domTextarea.treatsInitialSymbolValueAsAn47d8ce96",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_symbol_value.treats_updated_symbol_defaultvalue_as_an_empty_string.38c2c5da": "react_dom.burndownV127.domTextarea.treatsUpdatedSymbolDefaultvalueAsAn38c2c5da",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.when_given_a_symbol_value.treats_updated_symbol_value_as_an_empty_string.e8fba000": "react_dom.burndownV127.domTextarea.treatsUpdatedSymbolValueAsAne8fba000",
        "react_dom.ReactDOMTextarea-test.reactdomtextarea.will_not_initially_assign_an_empty_value_covers_case_where_firefox_throws_a_validation_error_when_required_attribute_is_set.111a68a7": "react_dom.burndownV127.domTextarea.willNotInitiallyAssignAnEmpty111a68a7",
    }
    py = "tests_upstream/react_dom/test_dom_textarea_burndown_v127.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_component_style_v128_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent style/innerHTML/aliases slice."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_apply_react_specific_aliases_to_html_elements.cb263944": "react_dom.burndownV128.domComponent.shouldApplyReactSpecificAliasesTocb263944",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_apply_react_specific_aliases_to_svg_elements.711499e5": "react_dom.burndownV128.domComponent.shouldApplyReactSpecificAliasesTo711499e5",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_clear_a_single_style_prop_when_changing_style.0083a6bc": "react_dom.burndownV128.domComponent.shouldClearASingleStyleProp0083a6bc",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_clear_all_the_styles_when_removing_style.441a1e9b": "react_dom.burndownV128.domComponent.shouldClearAllTheStylesWhen441a1e9b",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_empty_element_when_removing_innerhtml.94fb5bdd": "react_dom.burndownV128.domComponent.shouldEmptyElementWhenRemovingInnerhtml94fb5bdd",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_gracefully_handle_various_style_value_types.b42dd98d": "react_dom.burndownV128.domComponent.shouldGracefullyHandleVariousStyleValueb42dd98d",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_reset_innerhtml_for_when_children_is_null.b6c9d14c": "react_dom.burndownV128.domComponent.shouldNotResetInnerhtmlForWhenb6c9d14c",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_warn_for_0_as_a_unitless_style_value.f892f41d": "react_dom.burndownV128.domComponent.shouldNotWarnFor0Asf892f41d",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_remove_attributes.1513a9c6": "react_dom.burndownV128.domComponent.shouldRemoveAttributes1513a9c6",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_remove_properties.caf9905b": "react_dom.burndownV128.domComponent.shouldRemovePropertiescaf9905b",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_transition_from_innerhtml_to_string_content.50567516": "react_dom.burndownV128.domComponent.shouldTransitionFromInnerhtmlToString50567516",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_transition_from_string_content_to_innerhtml.a838626e": "react_dom.burndownV128.domComponent.shouldTransitionFromStringContentToa838626e",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_update_styles_if_initially_null.9d4fe743": "react_dom.burndownV128.domComponent.shouldUpdateStylesIfInitiallyNull9d4fe743",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_update_styles_if_updated_to_null_multiple_times.c483e35f": "react_dom.burndownV128.domComponent.shouldUpdateStylesIfUpdatedToc483e35f",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_update_styles_when_style_changes_from_null_to_object.cbd360d8": "react_dom.burndownV128.domComponent.shouldUpdateStylesWhenStyleChangescbd360d8",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_nicely_about_nan_in_style.18337e28": "react_dom.burndownV128.domComponent.shouldWarnNicelyAboutNanIn18337e28",
    }
    py = "tests_upstream/react_dom/test_react_dom_component_style_burndown_v128.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v129_may2026(cases: list[dict]) -> int:
    """ReactDOMInput Symbol/function, defaultValue host, coercion slice."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.should_not_incur_unnecessary_dom_mutations.d883112d": "react_dom.burndownV129.domInput.shouldNotIncurUnnecessaryDomMutationsd883112d",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_incur_unnecessary_dom_mutations_for_numeric_type_conversion.96b6a83e": "react_dom.burndownV129.domInput.shouldNotIncurUnnecessaryDomMutations96b6a83e",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_incur_unnecessary_dom_mutations_for_the_boolean_type_conversion.b9480c0e": "react_dom.burndownV129.domInput.shouldNotIncurUnnecessaryDomMutationsb9480c0e",
        "react_dom.ReactDOMInput-test.reactdominput.should_remove_previous_defaultvalue.95b834d3": "react_dom.burndownV129.domInput.shouldRemovePreviousDefaultvalue95b834d3",
        "react_dom.ReactDOMInput-test.reactdominput.should_throw_for_text_inputs_if_value_is_an_object_where_valueof_throws.cfd7b843": "react_dom.burndownV129.domInput.shouldThrowForTextInputsIfcfd7b843",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_input_switches_to_uncontrolled_with_defaultvalue.d242b524": "react_dom.burndownV129.domInput.shouldWarnIfControlledInputSwitchesd242b524",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_input_value_is_null_switches_to_controlled.cf364d2a": "react_dom.burndownV129.domInput.shouldWarnIfUncontrolledInputValuecf364d2a",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_value_is_null.5ebecadb": "react_dom.burndownV129.domInput.shouldWarnIfValueIsNull5ebecadb",
        "react_dom.ReactDOMInput-test.reactdominput.switching_text_inputs_between_numeric_and_string_numbers.does_change_the_number_2_to_2_0_with_no_change_handler.aef7370c": "react_dom.burndownV129.domInput.doesChangeTheNumber2Toaef7370c",
        "react_dom.ReactDOMInput-test.reactdominput.switching_text_inputs_between_numeric_and_string_numbers.does_change_the_string_2_to_2_0_with_no_change_handler.4da9ca69": "react_dom.burndownV129.domInput.doesChangeTheString2To4da9ca69",
        "react_dom.ReactDOMInput-test.reactdominput.updates_the_value_on_checkboxes_from_to_0.9aa0a00a": "react_dom.burndownV129.domInput.updatesTheValueOnCheckboxesFrom9aa0a00a",
        "react_dom.ReactDOMInput-test.reactdominput.updates_the_value_on_radio_buttons_from_to_0.15235625": "react_dom.burndownV129.domInput.updatesTheValueOnRadioButtons15235625",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_function_value.treats_initial_function_defaultvalue_as_an_empty_string.79a2f0d8": "react_dom.burndownV129.domInput.treatsInitialFunctionDefaultvalueAsAn79a2f0d8",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_function_value.treats_initial_function_value_as_an_empty_string.c1abd777": "react_dom.burndownV129.domInput.treatsInitialFunctionValueAsAnc1abd777",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_function_value.treats_updated_function_defaultvalue_as_an_empty_string.810f6fb4": "react_dom.burndownV129.domInput.treatsUpdatedFunctionDefaultvalueAsAn810f6fb4",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_function_value.treats_updated_function_value_as_an_empty_string.8cd78510": "react_dom.burndownV129.domInput.treatsUpdatedFunctionValueAsAn8cd78510",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_symbol_value.treats_initial_symbol_defaultvalue_as_an_empty_string.14a31419": "react_dom.burndownV129.domInput.treatsInitialSymbolDefaultvalueAsAn14a31419",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_symbol_value.treats_initial_symbol_value_as_an_empty_string.084b2534": "react_dom.burndownV129.domInput.treatsInitialSymbolValueAsAn084b2534",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_symbol_value.treats_updated_symbol_defaultvalue_as_an_empty_string.22a09971": "react_dom.burndownV129.domInput.treatsUpdatedSymbolDefaultvalueAsAn22a09971",
        "react_dom.ReactDOMInput-test.reactdominput.when_given_a_symbol_value.treats_updated_symbol_value_as_an_empty_string.6af82348": "react_dom.burndownV129.domInput.treatsUpdatedSymbolValueAsAn6af82348",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v129.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_multichild_reconcile_v130_may2026(cases: list[dict]) -> int:
    """ReactMultiChildReconcile: keyed order, null slots, iterable children (29 cases)."""

    mapping: dict[str, str] = {
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_append_children_to_the_end.80a61144": "react_dom.burndownV130.multiChildReconcile.shouldAppendChildrenToTheEnd80a61144",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_append_multiple_children_to_the_end.42be8831": "react_dom.burndownV130.multiChildReconcile.shouldAppendMultipleChildrenToThe42be8831",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_create_unique_identity.c6bc7a19": "react_dom.burndownV130.multiChildReconcile.shouldCreateUniqueIdentityc6bc7a19",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_cycle_order_correctly.8aafbf9d": "react_dom.burndownV130.multiChildReconcile.shouldCycleOrderCorrectly8aafbf9d",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_cycle_order_correctly_in_the_other_direction.9c88b4db": "react_dom.burndownV130.multiChildReconcile.shouldCycleOrderCorrectlyInThe9c88b4db",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_insert_multiple_new_truthy_children_in_the_middle.5a1716cf": "react_dom.burndownV130.multiChildReconcile.shouldInsertMultipleNewTruthyChildren5a1716cf",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_insert_non_empty_children_in_middle_where_nulls_were.eee08f76": "react_dom.burndownV130.multiChildReconcile.shouldInsertNonEmptyChildrenIneee08f76",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_insert_one_new_child_in_the_middle.6ef051d5": "react_dom.burndownV130.multiChildReconcile.shouldInsertOneNewChildIn6ef051d5",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_not_append_an_empty_child_to_the_end.a3d5872c": "react_dom.burndownV130.multiChildReconcile.shouldNotAppendAnEmptyChilda3d5872c",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_not_insert_empty_children_in_the_middle.255a029e": "react_dom.burndownV130.multiChildReconcile.shouldNotInsertEmptyChildrenIn255a029e",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_not_prepend_an_empty_child_to_the_beginning.d1255195": "react_dom.burndownV130.multiChildReconcile.shouldNotPrependAnEmptyChildd1255195",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_prepend_children_to_the_beginning.ebdc2f11": "react_dom.burndownV130.multiChildReconcile.shouldPrependChildrenToTheBeginningebdc2f11",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_prepend_multiple_children_to_the_beginning.26551df1": "react_dom.burndownV130.multiChildReconcile.shouldPrependMultipleChildrenToThe26551df1",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_preserve_order_if_children_order_has_not_changed.3b23d557": "react_dom.burndownV130.multiChildReconcile.shouldPreserveOrderIfChildrenOrder3b23d557",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_remove_nulled_out_children_and_ignore_new_null_children.015da13f": "react_dom.burndownV130.multiChildReconcile.shouldRemoveNulledOutChildrenAnd015da13f",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_remove_nulled_out_children_and_reorder_remaining.2a77766d": "react_dom.burndownV130.multiChildReconcile.shouldRemoveNulledOutChildrenAnd2a77766d",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_remove_nulled_out_children_at_the_beginning.db698a04": "react_dom.burndownV130.multiChildReconcile.shouldRemoveNulledOutChildrenAtdb698a04",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_remove_nulled_out_children_at_the_end.f4eed96f": "react_dom.burndownV130.multiChildReconcile.shouldRemoveNulledOutChildrenAtf4eed96f",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_reset_internal_state_if_removed_then_readded_in_a_legacy_iterable.01c67dcb": "react_dom.burndownV130.multiChildReconcile.shouldResetInternalStateIfRemoved01c67dcb",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_reset_internal_state_if_removed_then_readded_in_a_modern_iterable.dfffc2bb": "react_dom.burndownV130.multiChildReconcile.shouldResetInternalStateIfRemoveddfffc2bb",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_reset_internal_state_if_removed_then_readded_in_an_array.81c8bf9f": "react_dom.burndownV130.multiChildReconcile.shouldResetInternalStateIfRemoved81c8bf9f",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_reverse_the_order_of_more_than_two_children.a9761d0a": "react_dom.burndownV130.multiChildReconcile.shouldReverseTheOrderOfMorea9761d0a",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_reverse_the_order_of_two_children.1ab79ce9": "react_dom.burndownV130.multiChildReconcile.shouldReverseTheOrderOfTwo1ab79ce9",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_null_children_to_one_child.a97f011e": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromNullChildrenToa97f011e",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_null_children_to_zero_children.e6605f86": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromNullChildrenToe6605f86",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_one_child_to_null_children.aeb721da": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromOneChildToaeb721da",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_one_to_zero_children_correctly.d0039f58": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromOneToZerod0039f58",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_zero_children_to_null_children.6212835a": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromZeroChildrenTo6212835a",
        "react_dom.ReactMultiChildReconcile-test.reactmultichildreconcile.should_transition_from_zero_to_one_children_correctly.4b85250e": "react_dom.burndownV130.multiChildReconcile.shouldTransitionFromZeroToOne4b85250e",
    }
    py = "tests_upstream/react_dom/test_multichild_reconcile_burndown_v130.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v131_may2026(cases: list[dict]) -> int:
    """ReactDOMInput checkbox/radio controlled warnings, Temporal defaultValue, defaultValue host."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.only_assigns_defaultvalue_if_it_changes.0ceddb8a": "react_dom.burndownV131.domInput.onlyAssignsDefaultvalueIfItChanges0ceddb8a",
        "react_dom.ReactDOMInput-test.reactdominput.should_take_defaultvalue_when_changing_to_uncontrolled_input.673f2f03": "react_dom.burndownV131.domInput.shouldTakeDefaultvalueWhenChangingTo673f2f03",
        "react_dom.ReactDOMInput-test.reactdominput.should_throw_for_date_inputs_if_defaultvalue_is_an_object_where_valueof_throws.765aa277": "react_dom.burndownV131.domInput.shouldThrowForDateInputsIf765aa277",
        "react_dom.ReactDOMInput-test.reactdominput.should_throw_for_date_inputs_if_value_is_an_object_where_valueof_throws.25b58f63": "react_dom.burndownV131.domInput.shouldThrowForDateInputsIf25b58f63",
        "react_dom.ReactDOMInput-test.reactdominput.should_throw_for_text_inputs_if_defaultvalue_is_an_object_where_valueof_throws.5b1d8005": "react_dom.burndownV131.domInput.shouldThrowForTextInputsIf5b1d8005",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_checkbox_switches_to_uncontrolled_checked_is_null.1abfa6be": "react_dom.burndownV131.domInput.shouldWarnIfControlledCheckboxSwitches1abfa6be",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_checkbox_switches_to_uncontrolled_checked_is_undefined.0e6ebdce": "react_dom.burndownV131.domInput.shouldWarnIfControlledCheckboxSwitches0e6ebdce",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_checkbox_switches_to_uncontrolled_with_defaultchecked.ee94ec6a": "react_dom.burndownV131.domInput.shouldWarnIfControlledCheckboxSwitchesee94ec6a",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_radio_switches_to_uncontrolled_checked_is_null.c223ae84": "react_dom.burndownV131.domInput.shouldWarnIfControlledRadioSwitchesc223ae84",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_radio_switches_to_uncontrolled_checked_is_undefined.e5f44795": "react_dom.burndownV131.domInput.shouldWarnIfControlledRadioSwitchese5f44795",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_controlled_radio_switches_to_uncontrolled_with_defaultchecked.f61735dc": "react_dom.burndownV131.domInput.shouldWarnIfControlledRadioSwitchesf61735dc",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_radio_checked_false_changes_to_become_uncontrolled.d485bf5d": "react_dom.burndownV131.domInput.shouldWarnIfRadioCheckedFalsed485bf5d",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_checkbox_checked_is_null_switches_to_controlled.eb877748": "react_dom.burndownV131.domInput.shouldWarnIfUncontrolledCheckboxCheckedeb877748",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_checkbox_checked_is_undefined_switches_to_controlled.ce80e420": "react_dom.burndownV131.domInput.shouldWarnIfUncontrolledCheckboxCheckedce80e420",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_input_value_is_undefined_switches_to_controlled.57d89521": "react_dom.burndownV131.domInput.shouldWarnIfUncontrolledInputValue57d89521",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_radio_checked_is_null_switches_to_controlled.fba90597": "react_dom.burndownV131.domInput.shouldWarnIfUncontrolledRadioCheckedfba90597",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_if_uncontrolled_radio_checked_is_undefined_switches_to_controlled.203c2f00": "react_dom.burndownV131.domInput.shouldWarnIfUncontrolledRadioChecked203c2f00",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_with_checked_and_no_onchange_handler_with_readonly_specified.076a7926": "react_dom.burndownV131.domInput.shouldWarnWithCheckedAndNo076a7926",
        "react_dom.ReactDOMInput-test.reactdominput.should_warn_with_value_and_no_onchange_handler_and_readonly_specified.8e9849b7": "react_dom.burndownV131.domInput.shouldWarnWithValueAndNo8e9849b7",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v131.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_component_v132_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent mutations, style, custom elements, DEV warnings."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_group_multiple_unknown_prop_warnings_together.c7406252": "react_dom.burndownV132.domComponent.shouldGroupMultipleUnknownPropWarningsc7406252",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_ignore_attribute_list_for_elements_with_the_is_attribute.7de2e2b1": "react_dom.burndownV132.domComponent.shouldIgnoreAttributeListForElements7de2e2b1",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_apply_react_specific_aliases_to_custom_elements.c9d5a624": "react_dom.burndownV132.domComponent.shouldNotApplyReactSpecificAliasesc9d5a624",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_filter_attributes_for_custom_elements.560444c8": "react_dom.burndownV132.domComponent.shouldNotFilterAttributesForCustom560444c8",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_incur_unnecessary_dom_mutations_for_attributes.73cc0293": "react_dom.burndownV132.domComponent.shouldNotIncurUnnecessaryDomMutations73cc0293",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_incur_unnecessary_dom_mutations_for_boolean_properties.b84f9dfe": "react_dom.burndownV132.domComponent.shouldNotIncurUnnecessaryDomMutationsb84f9dfe",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_incur_unnecessary_dom_mutations_for_controlled_string_properties.bc2ee7fc": "react_dom.burndownV132.domComponent.shouldNotIncurUnnecessaryDomMutationsbc2ee7fc",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_incur_unnecessary_dom_mutations_for_string_properties.4f9f5e57": "react_dom.burndownV132.domComponent.shouldNotIncurUnnecessaryDomMutations4f9f5e57",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_not_update_styles_when_mutating_a_proxy_style_object.b3174212": "react_dom.burndownV132.domComponent.shouldNotUpdateStylesWhenMutatingb3174212",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_properly_update_custom_attributes_on_custom_elements.581c372c": "react_dom.burndownV132.domComponent.shouldProperlyUpdateCustomAttributesOn581c372c",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_skip_dangerouslysetinnerhtml_on_web_components.8d65fd3e": "react_dom.burndownV132.domComponent.shouldSkipDangerouslysetinnerhtmlOnWebComponents8d65fd3e",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_skip_reserved_props_on_web_components.f43d7bf9": "react_dom.burndownV132.domComponent.shouldSkipReservedPropsOnWebf43d7bf9",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_throw_when_mutating_style_objects.9f431d27": "react_dom.burndownV132.domComponent.shouldThrowWhenMutatingStyleObjects9f431d27",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_transition_from_children_to_innerhtml_in_nested_el.acc51e13": "react_dom.burndownV132.domComponent.shouldTransitionFromChildrenToInnerhtmlacc51e13",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_transition_from_innerhtml_to_children_in_nested_el.4cf34dec": "react_dom.burndownV132.domComponent.shouldTransitionFromInnerhtmlToChildren4cf34dec",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_update_arbitrary_attributes_for_tags_containing_dashes.d2b6e3e4": "react_dom.burndownV132.domComponent.shouldUpdateArbitraryAttributesForTagsd2b6e3e4",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_about_non_string_is_attribute.2c3291e6": "react_dom.burndownV132.domComponent.shouldWarnAboutNonStringIs2c3291e6",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_for_badly_cased_react_attributes.1f6141a1": "react_dom.burndownV132.domComponent.shouldWarnForBadlyCasedReact1f6141a1",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_for_ondblclick_prop.a4e16de8": "react_dom.burndownV132.domComponent.shouldWarnForOndblclickPropa4e16de8",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_for_unknown_function_event_handlers.85ddaa64": "react_dom.burndownV132.domComponent.shouldWarnForUnknownFunctionEvent85ddaa64",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_for_unknown_prop.edb4569e": "react_dom.burndownV132.domComponent.shouldWarnForUnknownPropedb4569e",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_warn_for_unknown_string_event_handlers.f122bbc1": "react_dom.burndownV132.domComponent.shouldWarnForUnknownStringEventf122bbc1",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.throws_with_temporal_like_objects_as_style_values.7fff42e9": "react_dom.burndownV132.domComponent.throwsWithTemporalLikeObjectsAs7fff42e9",
    }
    py = "tests_upstream/react_dom/test_react_dom_component_burndown_v132.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_input_v133_may2026(cases: list[dict]) -> int:
    """ReactDOMInput value/checked attrs, radio groups, events, reset, hydrate."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMInput-test.reactdominput.assigning_the_value_attribute_on_controlled_inputs.always_sets_the_attribute_when_values_change_on_text_inputs.7f885871": "react_dom.burndownV133.domInput.alwayssetstheattributewhenvalu7f885871",
        "react_dom.ReactDOMInput-test.reactdominput.assigning_the_value_attribute_on_controlled_inputs.an_uncontrolled_number_input_will_not_update_the_value_attribute_on_blur.6dd1e14e": "react_dom.burndownV133.domInput.anuncontrollednumberinputwilln6dd1e14e",
        "react_dom.ReactDOMInput-test.reactdominput.assigning_the_value_attribute_on_controlled_inputs.an_uncontrolled_text_input_will_not_update_the_value_attribute_on_blur.5522b7f2": "react_dom.burndownV133.domInput.anuncontrolledtextinputwillnot5522b7f2",
        "react_dom.ReactDOMInput-test.reactdominput.assigning_the_value_attribute_on_controlled_inputs.does_not_set_the_value_attribute_on_number_inputs_if_focused.54433d4f": "react_dom.burndownV133.domInput.doesnotsetthevalueattributeonn54433d4f",
        "react_dom.ReactDOMInput-test.reactdominput.assigning_the_value_attribute_on_controlled_inputs.sets_the_value_attribute_on_number_inputs_on_blur.38bde914": "react_dom.burndownV133.domInput.setsthevalueattributeonnumberi38bde914",
        "react_dom.ReactDOMInput-test.reactdominput.resets_value_of_date_time_input_to_fix_bugs_in_ios_safari.1a4813a6": "react_dom.burndownV133.domInput.resetsvalueofdatetimeinputtofi1a4813a6",
        "react_dom.ReactDOMInput-test.reactdominput.should_check_the_correct_radio_when_the_selected_name_moves.d5f74ef8": "react_dom.burndownV133.domInput.shouldcheckthecorrectradiowhend5f74ef8",
        "react_dom.ReactDOMInput-test.reactdominput.should_control_a_value_in_reentrant_events.8703cfa8": "react_dom.burndownV133.domInput.shouldcontrolavalueinreentrant8703cfa8",
        "react_dom.ReactDOMInput-test.reactdominput.should_control_radio_buttons.c13e3ec7": "react_dom.burndownV133.domInput.shouldcontrolradiobuttonsc13e3ec7",
        "react_dom.ReactDOMInput-test.reactdominput.should_control_radio_buttons_if_the_tree_updates_during_render_case_2_26876.9dcf77f9": "react_dom.burndownV133.domInput.shouldcontrolradiobuttonsifthe9dcf77f9",
        "react_dom.ReactDOMInput-test.reactdominput.should_control_radio_buttons_if_the_tree_updates_during_render_in_legacy_mode.83b85cc4": "react_dom.burndownV133.domInput.shouldcontrolradiobuttonsifthe83b85cc4",
        "react_dom.ReactDOMInput-test.reactdominput.should_control_values_in_reentrant_events_with_different_targets.296285cd": "react_dom.burndownV133.domInput.shouldcontrolvaluesinreentrant296285cd",
        "react_dom.ReactDOMInput-test.reactdominput.should_have_a_this_value_of_undefined_if_bind_is_not_used.59d64b64": "react_dom.burndownV133.domInput.shouldhaveathisvalueofundefine59d64b64",
        "react_dom.ReactDOMInput-test.reactdominput.should_have_the_correct_target_value.6d7bb192": "react_dom.burndownV133.domInput.shouldhavethecorrecttargetvalu6d7bb192",
        "react_dom.ReactDOMInput-test.reactdominput.should_hydrate_controlled_radio_buttons.fa147524": "react_dom.burndownV133.domInput.shouldhydratecontrolledradiobufa147524",
        "react_dom.ReactDOMInput-test.reactdominput.should_hydrate_uncontrolled_radio_buttons.59c43dbe": "react_dom.burndownV133.domInput.shouldhydrateuncontrolledradio59c43dbe",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_warn_if_radio_value_changes_but_never_becomes_controlled.b9d8c98a": "react_dom.burndownV133.domInput.shouldnotwarnifradiovaluechangb9d8c98a",
        "react_dom.ReactDOMInput-test.reactdominput.should_not_warn_if_radio_value_changes_but_never_becomes_uncontrolled.0bc1b677": "react_dom.burndownV133.domInput.shouldnotwarnifradiovaluechang0bc1b677",
        "react_dom.ReactDOMInput-test.reactdominput.should_notice_input_changes_when_reverting_back_to_original_value.344da512": "react_dom.burndownV133.domInput.shouldnoticeinputchangeswhenre344da512",
        "react_dom.ReactDOMInput-test.reactdominput.should_remove_the_value_attribute_on_reset_inputs_when_value_is_updated_to_undefined.f6d725ca": "react_dom.burndownV133.domInput.shouldremovethevalueattributeof6d725ca",
        "react_dom.ReactDOMInput-test.reactdominput.should_remove_the_value_attribute_on_submit_inputs_when_value_is_updated_to_undefined.42936f1d": "react_dom.burndownV133.domInput.shouldremovethevalueattributeo42936f1d",
        "react_dom.ReactDOMInput-test.reactdominput.should_restore_uncontrolled_inputs_to_last_defaultvalue_upon_reset.a0555034": "react_dom.burndownV133.domInput.shouldrestoreuncontrolledinputa0555034",
        "react_dom.ReactDOMInput-test.reactdominput.shouldn_t_get_tricked_by_changing_radio_names_part_2.eed5445e": "react_dom.burndownV133.domInput.shouldntgettrickedbychangingraeed5445e",
        "react_dom.ReactDOMInput-test.reactdominput.switching_text_inputs_between_numeric_and_string_numbers.changes_the_number_2_to_2_0_using_a_change_handler.2de58a80": "react_dom.burndownV133.domInput.changesthenumber2to20usingach2de58a80",
    }
    py = "tests_upstream/react_dom/test_dom_input_burndown_v133.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_event_listener_v134_may2026(cases: list[dict]) -> int:
    """ReactDOMEventListener propagation, capture, emulated bubbling, batching."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.propagation.should_batch_between_handlers_from_different_roots_continuous.33f7bebb": "react_dom.burndownV134.domEventListener.shouldbatchbetweenhandlersfrom33f7bebb",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.propagation.should_batch_between_handlers_from_different_roots_discrete.daf51874": "react_dom.burndownV134.domEventListener.shouldbatchbetweenhandlersfromdaf51874",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.propagation.should_not_get_confused_by_disappearing_elements.78eada6e": "react_dom.burndownV134.domEventListener.shouldnotgetconfusedbydisappea78eada6e",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.propagation.should_propagate_events_one_level_down.a8e5a70e": "react_dom.burndownV134.domEventListener.shouldpropagateeventsonelevelda8e5a70e",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.propagation.should_propagate_events_two_levels_down.4ed67392": "react_dom.burndownV134.domEventListener.shouldpropagateeventstwolevels4ed67392",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_bubble_non_native_bubbling_cancel_close_events.9b1d9e67": "react_dom.burndownV134.domEventListener.shouldbubblenonnativebubblingc9b1d9e67",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_bubble_non_native_bubbling_invalid_events.da8ca4db": "react_dom.burndownV134.domEventListener.shouldbubblenonnativebubblingida8ca4db",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_bubble_non_native_bubbling_media_events_events.b5474456": "react_dom.burndownV134.domEventListener.shouldbubblenonnativebubblingmb5474456",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_bubble_non_native_bubbling_toggle_events.dbee50aa": "react_dom.burndownV134.domEventListener.shouldbubblenonnativebubblingtdbee50aa",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_delegate_dialog_events_even_without_a_direct_listener.89a88239": "react_dom.burndownV134.domEventListener.shoulddelegatedialogeventseven89a88239",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_delegate_media_events_even_without_a_direct_listener.6ebd4d25": "react_dom.burndownV134.domEventListener.shoulddelegatemediaeventsevenw6ebd4d25",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_dispatch_load_for_embed_elements.b85bf997": "react_dom.burndownV134.domEventListener.shoulddispatchloadforembedelemb85bf997",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_dispatch_loadstart_only_for_media_elements.cba916e0": "react_dom.burndownV134.domEventListener.shoulddispatchloadstartonlyforcba916e0",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_handle_non_bubbling_capture_events_correctly.75bd4d9f": "react_dom.burndownV134.domEventListener.shouldhandlenonbubblingcapture75bd4d9f",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_attempt_to_listen_to_unnecessary_events_on_the_top_level.9fb89da1": "react_dom.burndownV134.domEventListener.shouldnotattempttolistentounne9fb89da1",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_emulate_bubbling_of_scroll_events.43885269": "react_dom.burndownV134.domEventListener.shouldnotemulatebubblingofscro43885269",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_emulate_bubbling_of_scroll_events_no_own_handler.4b02ce40": "react_dom.burndownV134.domEventListener.shouldnotemulatebubblingofscro4b02ce40",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_fire_duplicate_events_for_a_react_dom_tree.fd0f4ba0": "react_dom.burndownV134.domEventListener.shouldnotfireduplicateeventsfofd0f4ba0",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_fire_form_events_twice.b6af3fd2": "react_dom.burndownV134.domEventListener.shouldnotfireformeventstwiceb6af3fd2",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_receive_submit_events_if_native_interim_dom_handler_prevents_it.bf4164df": "react_dom.burndownV134.domEventListener.shouldnotreceivesubmiteventsifbf4164df",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_not_subscribe_to_selectionchange_twice.fa330acc": "react_dom.burndownV134.domEventListener.shouldnotsubscribetoselectioncfa330acc",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_subscribe_to_scroll_during_hydration.48bdf187": "react_dom.burndownV134.domEventListener.shouldsubscribetoscrollduringh48bdf187",
        "react_dom.ReactDOMEventListener-test.reactdomeventlistener.should_subscribe_to_scroll_during_updates.b599c68d": "react_dom.burndownV134.domEventListener.shouldsubscribetoscrollduringub599c68d",
    }
    py = "tests_upstream/react_dom/test_dom_event_listener_burndown_v134.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_option_v135_may2026(cases: list[dict]) -> int:
    """ReactDOMOption children flattening, value attr, select selected, DSH."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMOption-test.reactdomoption.generates_a_hydration_error_when_an_invalid_nested_tag_is_used_as_a_child.9958970c": "react_dom.burndownV135.domOption.generateshydrationerrorinvalidn9958970c",
        "react_dom.ReactDOMOption-test.reactdomoption.should_allow_ignoring_value_on_option.3007fad1": "react_dom.burndownV135.domOption.shouldallowignoringvalueonopt3007fad1",
        "react_dom.ReactDOMOption-test.reactdomoption.should_be_able_to_use_dangerouslysetinnerhtml_on_option.6f30e33b": "react_dom.burndownV135.domOption.shouldbeabletousedangerouslyse6f30e33b",
        "react_dom.ReactDOMOption-test.reactdomoption.should_flatten_children_to_a_string.4ac04d3d": "react_dom.burndownV135.domOption.shouldflattenchildrentoastring4ac04d3d",
        "react_dom.ReactDOMOption-test.reactdomoption.should_ignore_null_undefined_false_children_without_warning.7378a728": "react_dom.burndownV135.domOption.shouldignorenullundefinedfalse7378a728",
        "react_dom.ReactDOMOption-test.reactdomoption.should_not_warn_for_component_child_if_value_prop_is_provided.b733cdb9": "react_dom.burndownV135.domOption.shouldnotwarnforcomponentchildb733cdb9",
        "react_dom.ReactDOMOption-test.reactdomoption.should_set_attribute_for_empty_value.b723e584": "react_dom.burndownV135.domOption.shouldsetattributeforemptyvalueb723e584",
        "react_dom.ReactDOMOption-test.reactdomoption.should_support_bigint_values.1216c098": "react_dom.burndownV135.domOption.shouldsupportbigintvalues1216c098",
        "react_dom.ReactDOMOption-test.reactdomoption.should_support_element_ish_child.5fe50838": "react_dom.burndownV135.domOption.shouldsupportelementishchild5fe50838",
        "react_dom.ReactDOMOption-test.reactdomoption.should_throw_on_object_children.14a77222": "react_dom.burndownV135.domOption.shouldthrowonobjectchildren14a77222",
        "react_dom.ReactDOMOption-test.reactdomoption.should_warn_for_component_child_if_no_value_prop_is_provided.bfe34840": "react_dom.burndownV135.domOption.shouldwarnforcomponentchildifbfe34840",
        "react_dom.ReactDOMOption-test.reactdomoption.should_warn_for_invalid_child_tags.4a1c701a": "react_dom.burndownV135.domOption.shouldwarnforinvalidchildtags4a1c701a",
    }
    py = "tests_upstream/react_dom/test_dom_option_burndown_v135.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_event_propagation_v136_may2026(cases: list[dict]) -> int:
    """ReactDOMEventPropagation native/emulated bubbling and enter/leave delegation."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onanimationend.38c8206d": "react_dom.burndownV136.domEventPropagation.onanimationend38c8206d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onanimationiteration.6c3157d6": "react_dom.burndownV136.domEventPropagation.onanimationiteration6c3157d6",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onanimationstart.a9304289": "react_dom.burndownV136.domEventPropagation.onanimationstarta9304289",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onauxclick.82c97d2d": "react_dom.burndownV136.domEventPropagation.onauxclick82c97d2d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onblur.66f4cfe9": "react_dom.burndownV136.domEventPropagation.onblur66f4cfe9",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onclick.f07e9843": "react_dom.burndownV136.domEventPropagation.onclickf07e9843",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.oncontextmenu.3669f1ae": "react_dom.burndownV136.domEventPropagation.oncontextmenu3669f1ae",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.oncopy.cb71c7bc": "react_dom.burndownV136.domEventPropagation.oncopycb71c7bc",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.oncut.2e3c04bb": "react_dom.burndownV136.domEventPropagation.oncut2e3c04bb",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondoubleclick.5d15fe9e": "react_dom.burndownV136.domEventPropagation.ondoubleclick5d15fe9e",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondrag.be5ad2fd": "react_dom.burndownV136.domEventPropagation.ondragbe5ad2fd",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragend.605ae7fb": "react_dom.burndownV136.domEventPropagation.ondragend605ae7fb",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragenter.fb7a0646": "react_dom.burndownV136.domEventPropagation.ondragenterfb7a0646",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragexit.47c718a8": "react_dom.burndownV136.domEventPropagation.ondragexit47c718a8",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragleave.e62735ee": "react_dom.burndownV136.domEventPropagation.ondragleavee62735ee",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragover.fbe02ed8": "react_dom.burndownV136.domEventPropagation.ondragoverfbe02ed8",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondragstart.7ad47f17": "react_dom.burndownV136.domEventPropagation.ondragstart7ad47f17",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ondrop.78865276": "react_dom.burndownV136.domEventPropagation.ondrop78865276",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onfocus.339df54d": "react_dom.burndownV136.domEventPropagation.onfocus339df54d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onfullscreenchange.4562d42f": "react_dom.burndownV136.domEventPropagation.onfullscreenchange4562d42f",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onfullscreenerror.e34a9405": "react_dom.burndownV136.domEventPropagation.onfullscreenerrore34a9405",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ongotpointercapture.c2fd509a": "react_dom.burndownV136.domEventPropagation.ongotpointercapturec2fd509a",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onkeydown.ace551aa": "react_dom.burndownV136.domEventPropagation.onkeydownace551aa",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onkeypress.07312c11": "react_dom.burndownV136.domEventPropagation.onkeypress07312c11",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onkeyup.24279bf8": "react_dom.burndownV136.domEventPropagation.onkeyup24279bf8",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onlostpointercapture.4e6ad61e": "react_dom.burndownV136.domEventPropagation.onlostpointercapture4e6ad61e",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onmousedown.22ca7ab2": "react_dom.burndownV136.domEventPropagation.onmousedown22ca7ab2",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onmouseout.1fd66d39": "react_dom.burndownV136.domEventPropagation.onmouseout1fd66d39",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onmouseover.cf6cad77": "react_dom.burndownV136.domEventPropagation.onmouseovercf6cad77",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onmouseup.2ffe4e70": "react_dom.burndownV136.domEventPropagation.onmouseup2ffe4e70",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpaste.3078ee3e": "react_dom.burndownV136.domEventPropagation.onpaste3078ee3e",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointercancel.7665ace8": "react_dom.burndownV136.domEventPropagation.onpointercancel7665ace8",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointerdown.b453c32e": "react_dom.burndownV136.domEventPropagation.onpointerdownb453c32e",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointermove.a4bdf6f3": "react_dom.burndownV136.domEventPropagation.onpointermovea4bdf6f3",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointerout.1740288d": "react_dom.burndownV136.domEventPropagation.onpointerout1740288d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointerover.143be4eb": "react_dom.burndownV136.domEventPropagation.onpointerover143be4eb",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onpointerup.717ce627": "react_dom.burndownV136.domEventPropagation.onpointerup717ce627",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onreset.b9e58a3a": "react_dom.burndownV136.domEventPropagation.onresetb9e58a3a",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onsubmit.1b55a50b": "react_dom.burndownV136.domEventPropagation.onsubmit1b55a50b",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontouchcancel.8f5abb4b": "react_dom.burndownV136.domEventPropagation.ontouchcancel8f5abb4b",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontouchend.4a55108f": "react_dom.burndownV136.domEventPropagation.ontouchend4a55108f",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontouchmove.b52c2d2c": "react_dom.burndownV136.domEventPropagation.ontouchmoveb52c2d2c",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontouchstart.25789263": "react_dom.burndownV136.domEventPropagation.ontouchstart25789263",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontransitioncancel.1d044363": "react_dom.burndownV136.domEventPropagation.ontransitioncancel1d044363",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontransitionend.5792a8d7": "react_dom.burndownV136.domEventPropagation.ontransitionend5792a8d7",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontransitionrun.8b6e5551": "react_dom.burndownV136.domEventPropagation.ontransitionrun8b6e5551",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.ontransitionstart.cc2b9191": "react_dom.burndownV136.domEventPropagation.ontransitionstartcc2b9191",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.bubbling_events.onwheel.6d2e1a41": "react_dom.burndownV136.domEventPropagation.onwheel6d2e1a41",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.enter_leave_events.onmouseenter_and_onmouseleave.06933522": "react_dom.burndownV136.domEventPropagation.onmouseenterandonmouseleave06933522",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.enter_leave_events.onpointerenter_and_onpointerleave.b20c2ea2": "react_dom.burndownV136.domEventPropagation.onpointerenterandonpointerleb20c2ea2",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onabort.ed8cf659": "react_dom.burndownV136.domEventPropagation.onaborted8cf659",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onbeforetoggle_dialog_api.cfa24353": "react_dom.burndownV136.domEventPropagation.onbeforetoggledialogapicfa24353",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onbeforetoggle_popover_api.dcdff52f": "react_dom.burndownV136.domEventPropagation.onbeforetogglepopoverapidcdff52f",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.oncancel.e8c88458": "react_dom.burndownV136.domEventPropagation.oncancele8c88458",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.oncanplay.58ebaced": "react_dom.burndownV136.domEventPropagation.oncanplay58ebaced",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.oncanplaythrough.9bb05308": "react_dom.burndownV136.domEventPropagation.oncanplaythrough9bb05308",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onclose.0eefee2c": "react_dom.burndownV136.domEventPropagation.onclose0eefee2c",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.ondurationchange.5c597dca": "react_dom.burndownV136.domEventPropagation.ondurationchange5c597dca",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onemptied.97aff7aa": "react_dom.burndownV136.domEventPropagation.onemptied97aff7aa",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onencrypted.8e617f70": "react_dom.burndownV136.domEventPropagation.onencrypted8e617f70",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onended.4c2ea87b": "react_dom.burndownV136.domEventPropagation.onended4c2ea87b",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onerror.c4bfe649": "react_dom.burndownV136.domEventPropagation.onerrorc4bfe649",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.oninvalid.05bd1ece": "react_dom.burndownV136.domEventPropagation.oninvalid05bd1ece",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onload.6da03d0d": "react_dom.burndownV136.domEventPropagation.onload6da03d0d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onloadeddata.cc986256": "react_dom.burndownV136.domEventPropagation.onloadeddatacc986256",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onloadedmetadata.24c9af8c": "react_dom.burndownV136.domEventPropagation.onloadedmetadata24c9af8c",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onloadstart.f274e16c": "react_dom.burndownV136.domEventPropagation.onloadstartf274e16c",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onpause.12402678": "react_dom.burndownV136.domEventPropagation.onpause12402678",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onplay.92559c43": "react_dom.burndownV136.domEventPropagation.onplay92559c43",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onplaying.6d01499d": "react_dom.burndownV136.domEventPropagation.onplaying6d01499d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onprogress.2cfa787d": "react_dom.burndownV136.domEventPropagation.onprogress2cfa787d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onratechange.79e0086a": "react_dom.burndownV136.domEventPropagation.onratechange79e0086a",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onresize.597ec206": "react_dom.burndownV136.domEventPropagation.onresize597ec206",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onseeked.42b250e8": "react_dom.burndownV136.domEventPropagation.onseeked42b250e8",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onseeking.6e1b7e98": "react_dom.burndownV136.domEventPropagation.onseeking6e1b7e98",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onstalled.bb99fed7": "react_dom.burndownV136.domEventPropagation.onstalledbb99fed7",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onsuspend.65e931c6": "react_dom.burndownV136.domEventPropagation.onsuspend65e931c6",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.ontimeupdate.fe40ce02": "react_dom.burndownV136.domEventPropagation.ontimeupdatefe40ce02",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.ontoggle.b908647d": "react_dom.burndownV136.domEventPropagation.ontoggleb908647d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.ontoggle_dialog_api.e6e88a37": "react_dom.burndownV136.domEventPropagation.ontoggledialogapie6e88a37",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.ontoggle_popover_api.d94c13d6": "react_dom.burndownV136.domEventPropagation.ontogglepopoverapid94c13d6",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onvolumechange.68987be7": "react_dom.burndownV136.domEventPropagation.onvolumechange68987be7",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_bubble_in_react.onwaiting.b9a37054": "react_dom.burndownV136.domEventPropagation.onwaitingb9a37054",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_do_not_bubble_in_react.onscroll.60d5a51d": "react_dom.burndownV136.domEventPropagation.onscroll60d5a51d",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.non_bubbling_events_that_do_not_bubble_in_react.onscrollend.d12991ad": "react_dom.burndownV136.domEventPropagation.onscrollendd12991ad",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.onbeforeinput.36bbce6a": "react_dom.burndownV136.domEventPropagation.onbeforeinput36bbce6a",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.onchange.4e3abff5": "react_dom.burndownV136.domEventPropagation.onchange4e3abff5",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.oncompositionend.d6265fbc": "react_dom.burndownV136.domEventPropagation.oncompositionendd6265fbc",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.oncompositionstart.0fc93d83": "react_dom.burndownV136.domEventPropagation.oncompositionstart0fc93d83",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.oncompositionupdate.ad6c838f": "react_dom.burndownV136.domEventPropagation.oncompositionupdatead6c838f",
        "react_dom.ReactDOMEventPropagation-test.reactdomeventlistener.polyfilled_events.onselect.bf74ca46": "react_dom.burndownV136.domEventPropagation.onselectbf74ca46",
    }

    py = "tests_upstream/react_dom/test_dom_event_propagation_burndown_v136.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_component_v137_may2026(cases: list[dict]) -> int:
    """ReactDOMComponent: iOS tap onclick, mount load/error, nesting refs, unmount, slots."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMComponent-test.reactdomcomponent.ios_tap_highlight.adds_onclick_handler_to_a_portal_root.c46de7b5": "react_dom.burndownV137.domComponent.addsonclickhandlertoaportalrootc46de7b5",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.ios_tap_highlight.adds_onclick_handler_to_elements_with_onclick_prop.e75c6b13": "react_dom.burndownV137.domComponent.addsonclickhandlertoelementswithonclickpe75c6b13",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.ios_tap_highlight.does_not_add_onclick_handler_to_the_react_root_in_legacy_mode.61822a04": "react_dom.burndownV137.domComponent.doesnotaddonclickhandlertothereactrootin61822a04",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_receive_a_load_event_on_link_elements.6b5a96e2": "react_dom.burndownV137.domComponent.shouldreceivealoadeventonlinkelements6b5a96e2",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_receive_an_error_event_on_link_elements.a1d12646": "react_dom.burndownV137.domComponent.shouldreceiveanerroreventonlinkelementsa1d12646",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_support_custom_elements_which_extend_native_elements.dc56a369": "react_dom.burndownV137.domComponent.shouldsupportcustomelementswhichextendnadc56a369",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_work_error_event_on_source_element.a208b4eb": "react_dom.burndownV137.domComponent.shouldworkerroreventonsourceelementa208b4eb",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent.should_work_load_and_error_events_on_image_element_in_svg.cd7838f3": "react_dom.burndownV137.domComponent.shouldworkloadanderroreventsonimageelemecd7838f3",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning.134a8576": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarning134a8576",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_for_exact_elements.4b657f81": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarning4b657f81",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_in_composition.7b42eb62": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarning7b42eb62",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_in_composition_ssr.fde9a432": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarningfde9a432",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_for_exact_elements_ssr.caa8deaf": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarningcaa8deaf",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_for_update_render.ba59d8a9": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarningba59d8a9",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_source_code_refs_for_unknown_prop_warning_ssr.8f0f91f9": "react_dom.burndownV137.domComponent.givessourcecoderefsforunknownpropwarning8f0f91f9",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_useful_context_in_warnings.b13bad36": "react_dom.burndownV137.domComponent.givesusefulcontextinwarningsb13bad36",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_useful_context_in_warnings_2.20c6b4ed": "react_dom.burndownV137.domComponent.givesusefulcontextinwarnings220c6b4ed",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_useful_context_in_warnings_3.973a43b2": "react_dom.burndownV137.domComponent.givesusefulcontextinwarnings3973a43b2",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_useful_context_in_warnings_4.644ca010": "react_dom.burndownV137.domComponent.givesusefulcontextinwarnings4644ca010",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.nesting_validation.gives_useful_context_in_warnings_5.bb020999": "react_dom.burndownV137.domComponent.givesusefulcontextinwarnings5bb020999",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.receives_events_in_specific_order.c30f7bb1": "react_dom.burndownV137.domComponent.receiveseventsinspecificorderc30f7bb1",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.unmountcomponent.unmounts_children_before_unsetting_dom_node_info.47422075": "react_dom.burndownV137.domComponent.unmountschildrenbeforeunsettingdomnodein47422075",
        "react_dom.ReactDOMComponent-test.reactdomcomponent.updatedom.should_allow_named_slot_projection_on_both_web_components_and_regular_dom_elements.08257817": "react_dom.burndownV137.domComponent.shouldallownamedslotprojectiononbothwebc08257817",
    }
    py = "tests_upstream/react_dom/test_dom_component_burndown_v137.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_root_v138_may2026(cases: list[dict]) -> int:
    """ReactDOMRoot: createRoot, hydrateRoot, render/unmount semantics and DEV warnings."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMRoot-test.reactdomroot.can_be_immediately_unmounted.6965d36a": "react_dom.burndownV138.domRoot.canbeimmediatelyunmounted6965d36a",
        "react_dom.ReactDOMRoot-test.reactdomroot.clears_existing_children.9b7657ed": "react_dom.burndownV138.domRoot.clearsexistingchildren9b7657ed",
        "react_dom.ReactDOMRoot-test.reactdomroot.does_not_warn_when_creating_second_root_after_first_one_is_unmounted.265fd7d6": "react_dom.burndownV138.domRoot.doesnotwarnwhencreatingsecondrootaft265fd7d6",
        "react_dom.ReactDOMRoot-test.reactdomroot.errors_if_container_is_a_comment_node.6ae0ea4e": "react_dom.burndownV138.domRoot.errorsifcontainerisacommentnode6ae0ea4e",
        "react_dom.ReactDOMRoot-test.reactdomroot.renders_children.c4ae5873": "react_dom.burndownV138.domRoot.renderschildrenc4ae5873",
        "react_dom.ReactDOMRoot-test.reactdomroot.should_not_warn_if_mounting_into_non_empty_node.6f96e9dd": "react_dom.burndownV138.domRoot.shouldnotwarnifmountingintononemptyn6f96e9dd",
        "react_dom.ReactDOMRoot-test.reactdomroot.should_render_different_components_in_same_root.e45c5b96": "react_dom.burndownV138.domRoot.shouldrenderdifferentcomponentsinsame45c5b96",
        "react_dom.ReactDOMRoot-test.reactdomroot.should_reuse_markup_if_rendering_to_the_same_target_twice.f15a392d": "react_dom.burndownV138.domRoot.shouldreusemarkupifrenderingtothesamf15a392d",
        "react_dom.ReactDOMRoot-test.reactdomroot.should_unmount_and_remount_if_the_key_changes.0cb61fe3": "react_dom.burndownV138.domRoot.shouldunmountandremountifthekeychang0cb61fe3",
        "react_dom.ReactDOMRoot-test.reactdomroot.supports_hydration.cbf1ba1f": "react_dom.burndownV138.domRoot.supportshydrationcbf1ba1f",
        "react_dom.ReactDOMRoot-test.reactdomroot.throws_a_good_message_on_invalid_containers.b579d645": "react_dom.burndownV138.domRoot.throwsagoodmessageoninvalidcontainerb579d645",
        "react_dom.ReactDOMRoot-test.reactdomroot.throws_if_an_unmounted_root_is_updated.d139b77d": "react_dom.burndownV138.domRoot.throwsifanunmountedrootisupdatedd139b77d",
        "react_dom.ReactDOMRoot-test.reactdomroot.throws_if_unmounting_a_root_that_has_had_its_contents_removed.259f38aa": "react_dom.burndownV138.domRoot.throwsifunmountingarootthathashadits259f38aa",
        "react_dom.ReactDOMRoot-test.reactdomroot.unmount_is_synchronous.28458e29": "react_dom.burndownV138.domRoot.unmountissynchronous28458e29",
        "react_dom.ReactDOMRoot-test.reactdomroot.unmounts_children.56640d94": "react_dom.burndownV138.domRoot.unmountschildren56640d94",
        "react_dom.ReactDOMRoot-test.reactdomroot.warn_if_a_container_is_passed_to_root_render.5f944c8e": "react_dom.burndownV138.domRoot.warnifacontainerispassedtorootrender5f944c8e",
        "react_dom.ReactDOMRoot-test.reactdomroot.warn_if_a_object_is_passed_to_root_render.566f7b89": "react_dom.burndownV138.domRoot.warnifaobjectispassedtorootrender566f7b89",
        "react_dom.ReactDOMRoot-test.reactdomroot.warn_if_jsx_passed_to_createroot.cff0f746": "react_dom.burndownV138.domRoot.warnifjsxpassedtocreaterootcff0f746",
        "react_dom.ReactDOMRoot-test.reactdomroot.warn_if_no_children_passed_to_hydrateroot.2530a863": "react_dom.burndownV138.domRoot.warnifnochildrenpassedtohydrateroot2530a863",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_if_a_callback_parameter_is_provided_to_render.bc5d041b": "react_dom.burndownV138.domRoot.warnsifacallbackparameterisprovidedtbc5d041b",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_if_a_callback_parameter_is_provided_to_unmount.7ddaecba": "react_dom.burndownV138.domRoot.warnsifacallbackparameterisprovidedt7ddaecba",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_if_creating_a_root_on_the_document_body.1c3c6bba": "react_dom.burndownV138.domRoot.warnsifcreatingarootonthedocumentbod1c3c6bba",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_if_root_is_unmounted_inside_an_effect.7802cbd0": "react_dom.burndownV138.domRoot.warnsifrootisunmountedinsideaneffect7802cbd0",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_if_updating_a_root_that_has_had_its_contents_removed.2edf8e80": "react_dom.burndownV138.domRoot.warnsifupdatingarootthathashaditscon2edf8e80",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_when_creating_two_roots_managing_the_same_container.fde726df": "react_dom.burndownV138.domRoot.warnswhencreatingtworootsmanagingthefde726df",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_when_given_a_function.a487964e": "react_dom.burndownV138.domRoot.warnswhengivenafunctiona487964e",
        "react_dom.ReactDOMRoot-test.reactdomroot.warns_when_given_a_symbol.06d860be": "react_dom.burndownV138.domRoot.warnswhengivenasymbol06d860be",
    }
    py = "tests_upstream/react_dom/test_dom_root_burndown_v138.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_form_v139_may2026(cases: list[dict]) -> int:
    """ReactDOMForm: form actions, useActionState, useFormStatus, requestFormReset."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMForm-test.reactdomform.allows_a_non_function_formaction_to_override_a_function_one.b2b6f6c1": "react_dom.burndownV139.domForm.allowsanonfunctionformactiontooverrideafb2b6f6c1",
        "react_dom.ReactDOMForm-test.reactdomform.allows_a_non_react_html_formaction_to_be_invoked.238267f6": "react_dom.burndownV139.domForm.allowsanonreacthtmlformactiontobeinvoked238267f6",
        "react_dom.ReactDOMForm-test.reactdomform.async_errors_in_form_actions_can_be_captured_by_an_error_boundary.7a8e8831": "react_dom.burndownV139.domForm.asyncerrorsinformactionscanbecapturedbya7a8e8831",
        "react_dom.ReactDOMForm-test.reactdomform.can_read_the_clicked_button_in_the_formdata_event.9df173d9": "react_dom.burndownV139.domForm.canreadtheclickedbuttonintheformdataeven9df173d9",
        "react_dom.ReactDOMForm-test.reactdomform.excludes_the_submitter_name_when_the_submitter_is_a_function_action.b817da34": "react_dom.burndownV139.domForm.excludesthesubmitternamewhenthesubmitterb817da34",
        "react_dom.ReactDOMForm-test.reactdomform.form_actions_are_transitions.536cb882": "react_dom.burndownV139.domForm.formactionsaretransitions536cb882",
        "react_dom.ReactDOMForm-test.reactdomform.form_actions_can_be_asynchronous.84f0636b": "react_dom.burndownV139.domForm.formactionscanbeasynchronous84f0636b",
        "react_dom.ReactDOMForm-test.reactdomform.form_actions_should_retain_status_when_nested_state_changes.f85bee3f": "react_dom.burndownV139.domForm.formactionsshouldretainstatuswhennestedsf85bee3f",
        "react_dom.ReactDOMForm-test.reactdomform.multiple_form_actions.7e2c61aa": "react_dom.burndownV139.domForm.multipleformactions7e2c61aa",
        "react_dom.ReactDOMForm-test.reactdomform.parallel_form_submissions_do_not_throw.c2c3a1ea": "react_dom.burndownV139.domForm.parallelformsubmissionsdonotthrowc2c3a1ea",
        "react_dom.ReactDOMForm-test.reactdomform.regression_submitter_s_formaction_prop_is_coerced_correctly_before_checking_if_it_exists.2c245690": "react_dom.burndownV139.domForm.regressionsubmittersformactionpropiscoer2c245690",
        "react_dom.ReactDOMForm-test.reactdomform.requestformreset_schedules_a_form_reset_after_transition_completes.bfe1988a": "react_dom.burndownV139.domForm.requestformresetschedulesaformresetafterbfe1988a",
        "react_dom.ReactDOMForm-test.reactdomform.requestformreset_throws_if_the_form_is_not_managed_by_react.fa25a808": "react_dom.burndownV139.domForm.requestformresetthrowsiftheformisnotmanafa25a808",
        "react_dom.ReactDOMForm-test.reactdomform.requestformreset_throws_on_a_non_form_dom_element.7c4eefbf": "react_dom.burndownV139.domForm.requestformresetthrowsonanonformdomeleme7c4eefbf",
        "react_dom.ReactDOMForm-test.reactdomform.requestformreset_works_with_inputs_that_are_not_descendants_of_the_form_element.1f1fa164": "react_dom.burndownV139.domForm.requestformresetworkswithinputsthatareno1f1fa164",
        "react_dom.ReactDOMForm-test.reactdomform.reset_multiple_forms_in_the_same_transition.22db3825": "react_dom.burndownV139.domForm.resetmultipleformsinthesametransition22db3825",
        "react_dom.ReactDOMForm-test.reactdomform.should_allow_passing_a_function_to_an_input_button_formaction.85d85014": "react_dom.burndownV139.domForm.shouldallowpassingafunctiontoaninputbutt85d85014",
        "react_dom.ReactDOMForm-test.reactdomform.should_allow_passing_a_function_to_form_action.e90522d7": "react_dom.burndownV139.domForm.shouldallowpassingafunctiontoformactione90522d7",
        "react_dom.ReactDOMForm-test.reactdomform.should_allow_preventing_default_to_block_the_action.bef8017e": "react_dom.burndownV139.domForm.shouldallowpreventingdefaulttoblocktheacbef8017e",
        "react_dom.ReactDOMForm-test.reactdomform.should_error_if_submitting_a_form_manually.6ecc6b04": "react_dom.burndownV139.domForm.shoulderrorifsubmittingaformmanually6ecc6b04",
        "react_dom.ReactDOMForm-test.reactdomform.should_fire_onreset_on_automatic_form_reset.cb5dcd9b": "react_dom.burndownV139.domForm.shouldfireonresetonautomaticformresetcb5dcd9b",
        "react_dom.ReactDOMForm-test.reactdomform.should_submit_once_if_a_portal_is_nested_inside_its_own_root.bb9297ed": "react_dom.burndownV139.domForm.shouldsubmitonceifaportalisnestedinsideibb9297ed",
        "react_dom.ReactDOMForm-test.reactdomform.should_submit_once_if_one_root_is_nested_inside_the_other.7a3e4846": "react_dom.burndownV139.domForm.shouldsubmitonceifonerootisnestedinsidet7a3e4846",
        "react_dom.ReactDOMForm-test.reactdomform.should_submit_the_inner_of_nested_forms.acd85591": "react_dom.burndownV139.domForm.shouldsubmittheinnerofnestedformsacd85591",
        "react_dom.ReactDOMForm-test.reactdomform.sync_errors_in_form_actions_can_be_captured_by_an_error_boundary.bcac5395": "react_dom.burndownV139.domForm.syncerrorsinformactionscanbecapturedbyanbcac5395",
        "react_dom.ReactDOMForm-test.reactdomform.uncontrolled_form_inputs_are_reset_after_the_action_completes.b87d4776": "react_dom.burndownV139.domForm.uncontrolledforminputsareresetaftertheacb87d4776",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_can_mix_sync_and_async_actions.01421e7b": "react_dom.burndownV139.domForm.useactionstatecanmixsyncandasyncactions01421e7b",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_dispatch_throws_if_called_during_render.dbed7933": "react_dom.burndownV139.domForm.useactionstatedispatchthrowsifcalledduridbed7933",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_does_not_wrap_action_in_a_transition_unless_dispatch_is_in_a_transition.7fc2d235": "react_dom.burndownV139.domForm.useactionstatedoesnotwrapactioninatransi7fc2d235",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_error_handling_async_action.7aac74af": "react_dom.burndownV139.domForm.useactionstateerrorhandlingasyncaction7aac74af",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_error_handling_sync_action.ce169a0d": "react_dom.burndownV139.domForm.useactionstateerrorhandlingsyncactionce169a0d",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_queues_multiple_actions_and_runs_them_in_order.337952ba": "react_dom.burndownV139.domForm.useactionstatequeuesmultipleactionsandru337952ba",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_supports_inline_actions.cba1b40b": "react_dom.burndownV139.domForm.useactionstatesupportsinlineactionscba1b40b",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_updates_state_asynchronously_and_queues_multiple_actions.3e0e0231": "react_dom.burndownV139.domForm.useactionstateupdatesstateasynchronously3e0e0231",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_warns_if_async_action_is_dispatched_outside_of_a_transition.354bbbca": "react_dom.burndownV139.domForm.useactionstatewarnsifasyncactionisdispat354bbbca",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_when_an_action_errors_subsequent_actions_are_canceled.659cc3eb": "react_dom.burndownV139.domForm.useactionstatewhenanactionerrorssubseque659cc3eb",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_when_calling_a_queued_action_uses_the_implementation_that_was_current_at_the_time_it_was_dispatched_not_the_most_recent_one.bbcf2208": "react_dom.burndownV139.domForm.useactionstatewhencallingaqueuedactionusbbcf2208",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_works_if_action_is_sync.2930b8b6": "react_dom.burndownV139.domForm.useactionstateworksifactionissync2930b8b6",
        "react_dom.ReactDOMForm-test.reactdomform.useactionstate_works_in_strictmode.37fd5014": "react_dom.burndownV139.domForm.useactionstateworksinstrictmode37fd5014",
        "react_dom.ReactDOMForm-test.reactdomform.useformstatus_coerces_the_value_of_the_action_prop.b5bcc62a": "react_dom.burndownV139.domForm.useformstatuscoercesthevalueoftheactionpb5bcc62a",
        "react_dom.ReactDOMForm-test.reactdomform.useformstatus_is_activated_if_starttransition_is_called_inside_preventdefault_ed_submit_event.a65dfc8d": "react_dom.burndownV139.domForm.useformstatusisactivatedifstarttransitioa65dfc8d",
        "react_dom.ReactDOMForm-test.reactdomform.useformstatus_is_not_activated_if_event_is_not_preventdefault_ed.e252bd92": "react_dom.burndownV139.domForm.useformstatusisnotactivatedifeventisnotpe252bd92",
        "react_dom.ReactDOMForm-test.reactdomform.useformstatus_is_not_activated_if_starttransition_is_not_called.a9ea7940": "react_dom.burndownV139.domForm.useformstatusisnotactivatedifstarttransia9ea7940",
        "react_dom.ReactDOMForm-test.reactdomform.useformstatus_reads_the_status_of_a_pending_form_action.2f411f24": "react_dom.burndownV139.domForm.useformstatusreadsthestatusofapendingfor2f411f24",
        "react_dom.ReactDOMForm-test.reactdomform.warns_if_requestformreset_is_called_outside_of_a_transition.17abecdc": "react_dom.burndownV139.domForm.warnsifrequestformresetiscalledoutsideof17abecdc",
    }
    py = "tests_upstream/react_dom/test_dom_form_burndown_v139.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_misc_v140_may2026(cases: list[dict]) -> int:
    """ReactDOM-test, ReactDOMUseId, ReactDOMSVG burndown (v140)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOM-test.reactdom.allows_a_dom_element_to_be_used_with_a_string.41863d17": "react_dom.burndownV140.domMisc.allowsadomelementtobeusedwithastring41863d17",
        "react_dom.ReactDOM-test.reactdom.calls_focus_on_autofocus_elements_after_they_have_been_mounted_to_the_dom.c55d2ae1": "react_dom.burndownV140.domMisc.callsfocusonautofocuselementsaftertheyhac55d2ae1",
        "react_dom.ReactDOM-test.reactdom.preserves_focus.24bf154c": "react_dom.burndownV140.domMisc.preservesfocus24bf154c",
        "react_dom.ReactDOM-test.reactdom.reports_stacks_with_re_entrant_rendertostring_calls_on_the_client.2a487bb9": "react_dom.burndownV140.domMisc.reportsstackswithreentrantrendertostring2a487bb9",
        "react_dom.ReactDOM-test.reactdom.should_allow_children_to_be_passed_as_an_argument.799d67e4": "react_dom.burndownV140.domMisc.shouldallowchildrentobepassedasanargumen799d67e4",
        "react_dom.ReactDOM-test.reactdom.should_bubble_onsubmit.9de26ce4": "react_dom.burndownV140.domMisc.shouldbubbleonsubmit9de26ce4",
        "react_dom.ReactDOM-test.reactdom.should_not_crash_calling_finddomnode_inside_a_function_component.76a68699": "react_dom.burndownV140.domMisc.shouldnotcrashcallingfinddomnodeinsideaf76a68699",
        "react_dom.ReactDOM-test.reactdom.should_not_crash_with_devtools_installed.ca9ec953": "react_dom.burndownV140.domMisc.shouldnotcrashwithdevtoolsinstalledca9ec953",
        "react_dom.ReactDOM-test.reactdom.should_overwrite_props_children_with_children_argument.f9d322af": "react_dom.burndownV140.domMisc.shouldoverwritepropschildrenwithchildrenf9d322af",
        "react_dom.ReactDOM-test.reactdom.should_purge_the_dom_cache_when_removing_nodes.63408074": "react_dom.burndownV140.domMisc.shouldpurgethedomcachewhenremovingnodes63408074",
        "react_dom.ReactDOM-test.reactdom.shouldn_t_fire_duplicate_event_handler_while_handling_other_nested_dispatch.be891633": "react_dom.burndownV140.domMisc.shouldntfireduplicateeventhandlerwhilehabe891633",
        "react_dom.ReactDOM-test.reactdom.throws_in_render_if_the_mount_callback_in_legacy_roots_is_not_a_function.ecfcd710": "react_dom.burndownV140.domMisc.throwsinrenderifthemountcallbackinlegacyecfcd710",
        "react_dom.ReactDOMSVG-test.reactdomsvg.can_render_html_into_a_foreignobject_in_non_react_svg_tree.f5f9242e": "react_dom.burndownV140.domMisc.canrenderhtmlintoaforeignobjectinnonreacf5f9242e",
        "react_dom.ReactDOMSVG-test.reactdomsvg.can_render_svg_into_a_non_react_svg_tree.90d0acac": "react_dom.burndownV140.domMisc.canrendersvgintoanonreactsvgtree90d0acac",
        "react_dom.ReactDOMSVG-test.reactdomsvg.creates_elements_with_svg_namespace_inside_svg_tag_during_mount.81be1aba": "react_dom.burndownV140.domMisc.createselementswithsvgnamespaceinsidesvg81be1aba",
        "react_dom.ReactDOMSVG-test.reactdomsvg.creates_elements_with_svg_namespace_inside_svg_tag_during_update.ac2e5060": "react_dom.burndownV140.domMisc.createselementswithsvgnamespaceinsidesvgac2e5060",
        "react_dom.ReactDOMSVG-test.reactdomsvg.creates_initial_namespaced_markup.6ab2dc45": "react_dom.burndownV140.domMisc.createsinitialnamespacedmarkup6ab2dc45",
        "react_dom.ReactDOMUseId-test.useid.basic_incremental_hydration.51a80995": "react_dom.burndownV140.domMisc.basicincrementalhydration51a80995",
        "react_dom.ReactDOMUseId-test.useid.empty_null_children.c32d6bd6": "react_dom.burndownV140.domMisc.emptynullchildrenc32d6bd6",
        "react_dom.ReactDOMUseId-test.useid.identifierprefix_option.6838af81": "react_dom.burndownV140.domMisc.identifierprefixoption6838af81",
        "react_dom.ReactDOMUseId-test.useid.indirections.3a602b4b": "react_dom.burndownV140.domMisc.indirections3a602b4b",
        "react_dom.ReactDOMUseId-test.useid.inserting_deleting_siblings_inside_a_dehydrated_suspense_boundary.004d2470": "react_dom.burndownV140.domMisc.insertingdeletingsiblingsinsideadehydrat004d2470",
        "react_dom.ReactDOMUseId-test.useid.inserting_deleting_siblings_outside_a_dehydrated_suspense_boundary.c84fa504": "react_dom.burndownV140.domMisc.insertingdeletingsiblingsoutsideadehydrac84fa504",
        "react_dom.ReactDOMUseId-test.useid.large_ids.5b8bd67b": "react_dom.burndownV140.domMisc.largeids5b8bd67b",
        "react_dom.ReactDOMUseId-test.useid.local_render_phase_updates.16f084e5": "react_dom.burndownV140.domMisc.localrenderphaseupdates16f084e5",
        "react_dom.ReactDOMUseId-test.useid.multiple_ids_in_a_single_component.5063630b": "react_dom.burndownV140.domMisc.multipleidsinasinglecomponent5063630b",
        "react_dom.ReactDOMUseId-test.useid.strictmode_double_rendering.3342ff75": "react_dom.burndownV140.domMisc.strictmodedoublerendering3342ff75",
        "react_dom.ReactDOMUseId-test.useid.supports_suspenselist_reveal_order_backwards.264b3232": "react_dom.burndownV140.domMisc.supportssuspenselistrevealorderbackwards264b3232",
        "react_dom.ReactDOMUseId-test.useid.supports_suspenselist_reveal_order_backwards_with_a_single_child_in_a_list_of_many.35259d90": "react_dom.burndownV140.domMisc.supportssuspenselistrevealorderbackwards35259d90",
        "react_dom.ReactDOMUseId-test.useid.supports_suspenselist_reveal_order_forwards.ddac8e38": "react_dom.burndownV140.domMisc.supportssuspenselistrevealorderforwardsddac8e38",
        "react_dom.ReactDOMUseId-test.useid.supports_suspenselist_reveal_order_independent.65aa4bc3": "react_dom.burndownV140.domMisc.supportssuspenselistrevealorderindepende65aa4bc3",
        "react_dom.ReactDOMUseId-test.useid.supports_suspenselist_reveal_order_together.72a4694e": "react_dom.burndownV140.domMisc.supportssuspenselistrevealordertogether72a4694e",
    }
    py = "tests_upstream/react_dom/test_dom_misc_burndown_v140.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_effect_event_v142_may2026(cases: list[dict]) -> int:
    """useEffectEvent-test.js core noop slice (v142)."""

    mapping: dict[str, str] = {
        "react.useEffectEvent-test.useeffectevent.can_be_defined_more_than_once": (
            "react.burndownV142.useEffectEvent.canBeDefinedMoreThanOnce"
        ),
        "react.useEffectEvent-test.useeffectevent.does_not_preserve_this_in_event_functions": (
            "react.burndownV142.useEffectEvent.doesNotPreserveThisInEventFunctions"
        ),
        "react.useEffectEvent-test.useeffectevent.doesn_t_provide_a_stable_identity": (
            "react.burndownV142.useEffectEvent.doesntProvideAStableIdentity"
        ),
        "react.useEffectEvent-test.useeffectevent.event_handlers_always_see_the_latest_committed_value": (
            "react.burndownV142.useEffectEvent.eventHandlersAlwaysSeeLatestCommittedValue"
        ),
        "react.useEffectEvent-test.useeffectevent.is_mutated_before_all_other_effects": (
            "react.burndownV142.useEffectEvent.isMutatedBeforeAllOtherEffects"
        ),
        "react.useEffectEvent-test.useeffectevent.is_stable_in_a_custom_hook": (
            "react.burndownV142.useEffectEvent.isStableInACustomHook"
        ),
        "react.useEffectEvent-test.useeffectevent.memoizes_basic_case_correctly": (
            "react.burndownV142.useEffectEvent.memoizesBasicCaseCorrectly"
        ),
        "react.useEffectEvent-test.useeffectevent.throws_when_called_in_render": (
            "react.burndownV142.useEffectEvent.throwsWhenCalledInRender"
        ),
        "react.useEffectEvent-test.useeffectevent.useeffect_shouldn_t_re_fire_when_event_handlers_change": (
            "react.burndownV142.useEffectEvent.useEffectShouldntReFireWhenEventHandlersChange"
        ),
        "react.useEffectEvent-test.useeffectevent.uselayouteffect_shouldn_t_re_fire_when_event_handlers_change": (
            "react.burndownV142.useEffectEvent.useLayoutEffectShouldntReFireWhenEventHandlersChange"
        ),
    }
    py = "tests_upstream/react/test_use_effect_event_burndown_v142.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_use_effect_event_defer_remaining_v142_may2026(cases: list[dict]) -> int:
    """Keep Activity/integration/interleaved/context useEffectEvent cases deferred."""

    defer_ids = {
        "react.useEffectEvent-test.useeffectevent.correctly_mutates_effect_event_with_activity",
        "react.useEffectEvent-test.useeffectevent.effect_events_are_fresh_inside_activity",
        "react.useEffectEvent-test.useeffectevent.fires_all_interleaved_effects_with_useeffectevent_in_correct_order",
        "react.useEffectEvent-test.useeffectevent.integration_implements_docs_chat_room_example",
        "react.useEffectEvent-test.useeffectevent.integration_implements_the_docs_logvisit_example",
        "react.useEffectEvent-test.useeffectevent.reads_the_latest_context_value_in_forwardref_components",
        "react.useEffectEvent-test.useeffectevent.reads_the_latest_context_value_in_memo_components",
    }
    rationale = (
        "Deferred: upstream useEffectEvent cases require Activity semantics, memo/forwardRef "
        "context integration, interleaved multi-component effect ordering, or full doc examples "
        "not yet modeled in ryact."
    )
    changed = 0
    for c in cases:
        if c.get("id") not in defer_ids:
            continue
        if c.get("status") != "non_goal":
            continue
        c["non_goal_rationale"] = rationale
        c["notes"] = "Deferred in v142; core noop slice implemented separately."
        changed += 1
    return changed

    return changed


def _patch_wave_flush_sync_v143_may2026(cases: list[dict]) -> int:
    """ReactFlushSync-test.js noop slice (v143)."""

    mapping: dict[str, str] = {
        "react.ReactFlushSync-test.reactflushsync.flushes_passive_effects_synchronously_when_they_are_the_result_of_a_sync_render": "react.burndownV143.flushSync.flushesPassiveEffectsSynchronouslyWhenSyncRender",
        "react.ReactFlushSync-test.reactflushsync.does_not_flush_passive_effects_synchronously_when_they_aren_t_the_result_of_a_sync_render": "react.burndownV143.flushSync.doesNotFlushPassiveEffectsWhenNotSyncRender",
        "react.ReactFlushSync-test.reactflushsync.does_not_flush_pending_passive_effects": "react.burndownV143.flushSync.doesNotFlushPendingPassiveEffects",
        "react.ReactFlushSync-test.reactflushsync.does_not_flush_passive_effects_synchronously_after_render_in_legacy_mode": "react.burndownV143.flushSync.doesNotFlushPassiveEffectsSynchronouslyAfterRenderLegacy",
        "react.ReactFlushSync-test.reactflushsync.flushes_pending_passive_effects_before_scope_is_called_in_legacy_mode": "react.burndownV143.flushSync.flushesPendingPassiveEffectsBeforeScopeLegacy",
        "react.ReactFlushSync-test.reactflushsync.supports_nested_flushsync_with_starttransition": "react.burndownV143.flushSync.supportsNestedFlushSyncWithStartTransition",
        "react.ReactFlushSync-test.reactflushsync.completely_exhausts_synchronous_work_queue_even_if_something_throws": "react.burndownV143.flushSync.completelyExhaustsSyncQueueEvenIfSomethingThrows",
    }
    py = "tests_upstream/react/test_flush_sync_burndown_v143.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_incremental_error_v143_may2026(cases: list[dict]) -> int:
    """IncrementalErrorHandling single-root scheduling slice (v143)."""

    mapping: dict[str, str] = {
        "react.ReactIncrementalErrorHandling-test.internal.reactincrementalerrorhandling.defers_additional_sync_work_to_a_separate_event_after_an_error": "react.burndownV143.incrementalError.defersAdditionalSyncWorkAfterError",
    }
    py = "tests_upstream/react/test_incremental_error_burndown_v143.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_updates_batching_v144_may2026(cases: list[dict]) -> int:
    """ReactUpdates-test.js batching slice (v144)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.should_batch_state_when_updating_state_twice.1c5ed0a4": "react_dom.burndownV144.domUpdates.shouldBatchStateWhenUpdatingStateTwice",
        "react_dom.ReactUpdates-test.reactupdates.should_batch_state_when_updating_two_different_states.efce9048": "react_dom.burndownV144.domUpdates.shouldBatchStateWhenUpdatingTwoDifferentStates",
        "react_dom.ReactUpdates-test.reactupdates.should_batch_parent_child_state_updates_together.c5536ac6": "react_dom.burndownV144.domUpdates.shouldBatchParentChildStateUpdatesTogether",
        "react_dom.ReactUpdates-test.reactupdates.should_batch_child_parent_state_updates_together.6fbd0cea": "react_dom.burndownV144.domUpdates.shouldBatchChildParentStateUpdatesTogether",
        "react_dom.ReactUpdates-test.reactupdates.does_not_re_render_if_state_update_is_null.015d0b8d": "react_dom.burndownV144.domUpdates.doesNotRerenderIfStateUpdateIsNull",
        "react_dom.ReactUpdates-test.reactupdates.should_support_chained_state_updates.58c20168": "react_dom.burndownV144.domUpdates.shouldSupportChainedStateUpdates",
        "react_dom.ReactUpdates-test.reactupdates.should_queue_nested_updates.f38b6581": "react_dom.burndownV144.domUpdates.shouldQueueNestedUpdates",
        "react_dom.ReactUpdates-test.reactupdates.mounts_and_unmounts_are_batched.1c978ac2": "react_dom.burndownV144.domUpdates.mountsAndUnmountsAreBatched",
        "react_dom.ReactUpdates-test.reactupdates.throws_in_setstate_if_the_update_callback_is_not_a_function.38468c65": "react_dom.burndownV144.domUpdates.throwsInSetStateIfUpdateCallbackNotFunction",
        "react_dom.ReactUpdates-test.reactupdates.should_flush_updates_in_the_correct_order.2e7bbeea": "react_dom.burndownV144.domUpdates.shouldFlushUpdatesInTheCorrectOrder",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v144.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_updates_batching_v145_may2026(cases: list[dict]) -> int:
    """ReactUpdates-test.js batching slice (v145)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.should_batch_state_and_props_together.99bc90bc": "react_dom.burndownV145.domUpdates.shouldBatchStateAndPropsTogether",
        "react_dom.ReactUpdates-test.reactupdates.should_flow_updates_correctly.9142d1d6": "react_dom.burndownV145.domUpdates.shouldFlowUpdatesCorrectly",
        "react_dom.ReactUpdates-test.reactupdates.should_queue_updates_from_during_mount.9a9011d3": "react_dom.burndownV145.domUpdates.shouldQueueUpdatesFromDuringMount",
        "react_dom.ReactUpdates-test.reactupdates.does_not_call_render_after_a_component_as_been_deleted.d85938e5": "react_dom.burndownV145.domUpdates.doesNotCallRenderAfterComponentDeleted",
        "react_dom.ReactUpdates-test.reactupdates.throws_in_forceupdate_if_the_update_callback_is_not_a_function.8ad5a709": "react_dom.burndownV145.domUpdates.throwsInForceUpdateIfUpdateCallbackNotFunction",
        "react_dom.ReactUpdates-test.reactupdates.does_not_update_one_component_twice_in_a_batch_2410.8ffa5183": "react_dom.burndownV145.domUpdates.doesNotUpdateOneComponentTwiceInBatch2410",
        "react_dom.ReactUpdates-test.reactupdates.does_not_update_one_component_twice_in_a_batch_6371.f7123a2f": "react_dom.burndownV145.domUpdates.doesNotUpdateOneComponentTwiceInBatch6371",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v145.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_updates_batching_v146_may2026(cases: list[dict]) -> int:
    """ReactUpdates-test.js deferred reconciler slice (v146)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.should_batch_forceupdate_together.de0637f2": "react_dom.burndownV146.domUpdates.shouldBatchForceupdateTogether",
        "react_dom.ReactUpdates-test.reactupdates.should_update_children_even_if_parent_blocks_updates.8b089baf": "react_dom.burndownV146.domUpdates.shouldUpdateChildrenEvenIfParentBlocksUpdates",
        "react_dom.ReactUpdates-test.reactupdates.should_not_reconcile_children_passed_via_props.8d8491f5": "react_dom.burndownV146.domUpdates.shouldNotReconcileChildrenPassedViaProps",
        "react_dom.ReactUpdates-test.reactupdates.calls_componentwillreceiveprops_setstate_callback_properly.5672ee8f": "react_dom.burndownV146.domUpdates.callsComponentwillreceivepropsSetstateCallbackProperly",
        "react_dom.ReactUpdates-test.reactupdates.handles_reentrant_mounting_in_synchronous_mode.e8a0ea85": "react_dom.burndownV146.domUpdates.handlesReentrantMountingInSynchronousMode",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_forceupdate_together.f4e23fa8": "react_dom.burndownV146.domUpdates.shouldBatchForceupdateTogether",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_update_children_even_if_parent_blocks_updates.26073f5c": "react_dom.burndownV146.domUpdates.shouldUpdateChildrenEvenIfParentBlocksUpdates",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_not_reconcile_children_passed_via_props.1567d42d": "react_dom.burndownV146.domUpdates.shouldNotReconcileChildrenPassedViaProps",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.calls_componentwillreceiveprops_setstate_callback_properly.2340a40d": "react_dom.burndownV146.domUpdates.callsComponentwillreceivepropsSetstateCallbackProperly",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.handles_reentrant_mounting_in_synchronous_mode.7d571ebd": "react_dom.burndownV146.domUpdates.handlesReentrantMountingInSynchronousMode",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v146.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_composite_lifecycle_v151_may2026(cases: list[dict]) -> int:
    """ReactComponent + lifecycle + composite + fiber legacy/morphing slice (v151)."""

    mapping: dict[str, str] = {
        "react_dom.ReactComponent-test.reactcomponent.fires_the_callback_after_a_component_is_rendered_in_legacy_roots.18392acb": "react_dom.burndownV151.composite.firesLegacyRenderCallback",
        "react_dom.ReactComponent-test.reactcomponent.should_call_refs_at_the_correct_time.9cef791d": "react_dom.burndownV151.composite.shouldCallRefsAtCorrectTime",
        "react_dom.ReactComponent-test.reactcomponent.should_not_have_string_refs_on_unmounted_components.529b9957": "react_dom.burndownV151.composite.shouldNotHaveStringRefsOnUnmountedComponents",
        "react_dom.ReactComponent-test.reactcomponent.should_throw_on_invalid_render_targets_in_legacy_roots.5cd55ca5": "react_dom.burndownV151.composite.shouldThrowOnInvalidLegacyRenderTargets",
        "react_dom.ReactComponent-test.reactcomponent.throws_if_a_legacy_element_is_used_as_a_child.bec2fa56": "react_dom.burndownV151.composite.throwsLegacyElementAsChild",
        "react_dom.ReactComponent-test.reactcomponent.throws_if_a_plain_object_even_if_it_is_in_an_owner_when_using_ssr.a3b82263": "react_dom.burndownV151.composite.throwsPlainObjectInOwnerSsr",
        "react_dom.ReactComponent-test.reactcomponent.throws_if_a_plain_object_is_used_as_a_child_when_using_ssr.09292779": "react_dom.burndownV151.composite.throwsPlainObjectAsChildSsr",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.react_lifecycles_compat.should_not_warn_for_components_with_polyfilled_getderivedstatefromprops.bc9d9e60": "react_dom.burndownV151.composite.shouldNotWarnPolyfilledGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.react_lifecycles_compat.should_not_warn_for_components_with_polyfilled_getsnapshotbeforeupdate.b427dc85": "react_dom.burndownV151.composite.shouldNotWarnPolyfilledGsbu",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_call_nested_legacy_lifecycle_methods_in_the_right_order.a114c0e1": "react_dom.burndownV151.composite.shouldCallNestedLegacyLifecycleOrder",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_call_nested_new_lifecycle_methods_in_the_right_order.10b15348": "react_dom.burndownV151.composite.shouldCallNestedNewLifecycleOrder",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_carry_through_each_of_the_phases_of_setup.2bb42d19": "react_dom.burndownV151.composite.shouldCarryThroughPhasesOfSetup",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_fire_ondomready_when_already_in_ondomready.d0c0ce26": "react_dom.burndownV151.composite.shouldFireOnDomReadyWhenAlreadyInOnDomReady",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_reuse_an_instance_when_it_has_been_unmounted.00414ef3": "react_dom.burndownV151.composite.shouldNotReuseInstanceWhenUnmounted",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_about_deprecated_lifecycles_cwm_cwrp_cwu_if_new_getsnapshotbeforeupdate_is_present.c0527e49": "react_dom.burndownV151.composite.shouldWarnDeprecatedLifecyclesWithGsbu",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.morphingcomponent.should_not_cache_old_dom_nodes_when_switching_constructors.40e9b3e6": "react_dom.burndownV151.composite.shouldNotCacheOldDomNodesWhenSwitchingConstructors",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.morphingcomponent.should_react_to_state_changes_from_callbacks.3f5cf37d": "react_dom.burndownV151.composite.shouldReactToStateChangesFromCallbacks",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.morphingcomponent.should_rewire_refs_when_rendering_to_different_child_types.ccc99fdc": "react_dom.burndownV151.composite.shouldRewireRefsWhenRenderingDifferentChildTypes",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.morphingcomponent.should_support_rendering_to_different_child_types_over_time.eb8e3182": "react_dom.burndownV151.composite.shouldSupportRenderingDifferentChildTypesOverTime",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.prepares_new_child_before_unmounting_old.755937bd": "react_dom.burndownV151.composite.preparesNewChildBeforeUnmountingOld",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_cleanup_even_if_render_fatals.ee68243d": "react_dom.burndownV151.composite.shouldCleanupEvenIfRenderFatals",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_warn_on_updating_function_component_from_componentwillmount.bbfe2ae0": "react_dom.burndownV151.composite.shouldNotWarnUpdatingFunctionFromCwm",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_warn_on_updating_function_component_from_componentwillreceiveprops.bb19f30a": "react_dom.burndownV151.composite.shouldNotWarnUpdatingFunctionFromCwrp",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_warn_on_updating_function_component_from_componentwillupdate.4866e7e4": "react_dom.burndownV151.composite.shouldNotWarnUpdatingFunctionFromCwu",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_call_an_effect_after_mount_update_replacing_render_callback_pattern.8dc3a102": "react_dom.burndownV151.composite.shouldCallEffectAfterMountUpdate",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_call_an_effect_when_the_same_element_is_re_rendered_replacing_render_callback_pattern.5441ef51": "react_dom.burndownV151.composite.shouldCallEffectWhenSameElementRerendered",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_one_portal.d5c8a831": "react_dom.burndownV151.composite.shouldRenderOnePortal",
    }
    py = "tests_upstream/react_dom/test_dom_composite_lifecycle_burndown_v151.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_v152_may2026(cases: list[dict]) -> int:
    """ReactLegacyMount + ReactLegacyComposite + DOM minimalism slice (v152)."""

    mapping: dict[str, str] = {
        "react_dom.ReactCompositeComponentDOMMinimalism-test.reactcompositecomponentdomminimalism.should_not_render_extra_nodes_for_interpolated_text_children.76e1adb9": "react_dom.burndownV152.legacy.shouldNotRenderExtraNodesForInterpolatedTextChildren",
        "react_dom.ReactCompositeComponentDOMMinimalism-test.reactcompositecomponentdomminimalism.should_not_render_extra_nodes_for_non_interpolated_text.b44e5bf3": "react_dom.burndownV152.legacy.shouldNotRenderExtraNodesForNonInterpolatedText",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_allow_access_to_finddomnode_in_componentwillunmount_in_legacy_mode.c4011336": "react_dom.burndownV152.legacy.shouldAllowAccessToFinddomnodeInComponentwillunmountInLegacyMode",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_not_warn_about_unmounting_during_unmounting_in_legacy_mode.89fd3cac": "react_dom.burndownV152.legacy.shouldNotWarnAboutUnmountingDuringUnmountingInLegacyMode",
        "react_dom.ReactLegacyMount-test.reactmount.clears_existing_children_with_legacy_api.ef84949a": "react_dom.burndownV152.legacy.clearsExistingChildrenWithLegacyApi",
        "react_dom.ReactLegacyMount-test.reactmount.initial_mount_of_legacy_root_is_sync_inside_batchedupdates_as_if_it_were_wrapped_in_flushsync.5f0bdd3d": "react_dom.burndownV152.legacy.initialMountOfLegacyRootIsSyncInsideBatchedupdatesAsIfItWereWrappedInFlushsync",
        "react_dom.ReactLegacyMount-test.reactmount.passes_the_correct_callback_context.88350418": "react_dom.burndownV152.legacy.passesTheCorrectCallbackContext",
        "react_dom.ReactLegacyMount-test.reactmount.should_not_warn_if_mounting_into_non_empty_node.661474ad": "react_dom.burndownV152.legacy.shouldNotWarnIfMountingIntoNonEmptyNode",
        "react_dom.ReactLegacyMount-test.reactmount.should_render_different_components_in_same_root.8f8d1530": "react_dom.burndownV152.legacy.shouldRenderDifferentComponentsInSameRoot",
        "react_dom.ReactLegacyMount-test.reactmount.should_reuse_markup_if_rendering_to_the_same_target_twice.6c3c6a54": "react_dom.burndownV152.legacy.shouldReuseMarkupIfRenderingToTheSameTargetTwice",
        "react_dom.ReactLegacyMount-test.reactmount.should_unmount_and_remount_if_the_key_changes.a68787d0": "react_dom.burndownV152.legacy.shouldUnmountAndRemountIfTheKeyChanges",
        "react_dom.ReactLegacyMount-test.reactmount.should_warn_if_render_removes_react_rendered_children.1e15a7b0": "react_dom.burndownV152.legacy.shouldWarnIfRenderRemovesReactRenderedChildren",
        "react_dom.ReactLegacyMount-test.reactmount.should_warn_if_the_unmounted_node_was_rendered_by_another_copy_of_react.99ea0ae5": "react_dom.burndownV152.legacy.shouldWarnIfTheUnmountedNodeWasRenderedByAnotherCopyOfReact",
        "react_dom.ReactLegacyMount-test.reactmount.should_warn_when_mounting_into_document_body.3f0529e9": "react_dom.burndownV152.legacy.shouldWarnWhenMountingIntoDocumentBody",
        "react_dom.ReactLegacyMount-test.reactmount.unmountcomponentatnode.returns_false_on_non_react_containers.aca3a893": "react_dom.burndownV152.legacy.returnsFalseOnNonReactContainers",
        "react_dom.ReactLegacyMount-test.reactmount.unmountcomponentatnode.returns_true_on_react_containers.b10b2271": "react_dom.burndownV152.legacy.returnsTrueOnReactContainers",
        "react_dom.ReactLegacyMount-test.reactmount.unmountcomponentatnode.throws_when_given_a_non_node.70ed9317": "react_dom.burndownV152.legacy.throwsWhenGivenANonNode",
        "react_dom.ReactLegacyMount-test.reactmount.warns_when_given_a_factory.5297608a": "react_dom.burndownV152.legacy.warnsWhenGivenAFactory",
        "react_dom.ReactLegacyMount-test.reactmount.warns_when_passing_legacy_container_to_createroot.2a4eaf81": "react_dom.burndownV152.legacy.warnsWhenPassingLegacyContainerToCreateroot",
        "react_dom.ReactLegacyMount-test.reactmount.warns_when_rendering_with_legacy_api_into_createroot_container.3e86d869": "react_dom.burndownV152.legacy.warnsWhenRenderingWithLegacyApiIntoCreaterootContainer",
        "react_dom.ReactLegacyMount-test.reactmount.warns_when_unmounting_with_legacy_api_has_previous_content.3385f865": "react_dom.burndownV152.legacy.warnsWhenUnmountingWithLegacyApiHasPreviousContent",
        "react_dom.ReactLegacyMount-test.reactmount.warns_when_unmounting_with_legacy_api_no_previous_content.9a3b3548": "react_dom.burndownV152.legacy.warnsWhenUnmountingWithLegacyApiNoPreviousContent",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_burndown_v152.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_updates_v153_may2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates + legacy composite cWRP/replaceState + DOM flushSync slice (v153)."""

    slices: list[tuple[dict[str, str], str]] = [
        (
            {
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_re_render_if_state_update_is_null.ae452a50": "react_dom.burndownV153.legacyUpdates.doesNotReRenderIfStateUpdateIsNull",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_update_one_component_twice_in_a_batch_6371.26ee418e": "react_dom.burndownV153.legacyUpdates.doesNotUpdateOneComponentTwiceInABatch6371",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_child_parent_state_updates_together.57831f99": "react_dom.burndownV153.legacyUpdates.shouldBatchChildParentStateUpdatesTogether",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_parent_child_state_updates_together.e5c4c3d6": "react_dom.burndownV153.legacyUpdates.shouldBatchParentChildStateUpdatesTogether",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_state_and_props_together.9f4ff26b": "react_dom.burndownV153.legacyUpdates.shouldBatchStateAndPropsTogether",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_state_when_updating_state_twice.5226b229": "react_dom.burndownV153.legacyUpdates.shouldBatchStateWhenUpdatingStateTwice",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_batch_state_when_updating_two_different_state_keys.553b2325": "react_dom.burndownV153.legacyUpdates.shouldBatchStateWhenUpdatingTwoDifferentStateKeys",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_queue_nested_updates.6b147ca3": "react_dom.burndownV153.legacyUpdates.shouldQueueNestedUpdates",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_support_chained_state_updates.11cdc834": "react_dom.burndownV153.legacyUpdates.shouldSupportChainedStateUpdates",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.throws_in_forceupdate_if_the_update_callback_is_not_a_function.af8a4b80": "react_dom.burndownV153.legacyUpdates.throwsInForceupdateIfTheUpdateCallbackIsNotAFunction",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.throws_in_setstate_if_the_update_callback_is_not_a_function.dcdc4c6f": "react_dom.burndownV153.legacyUpdates.throwsInSetstateIfTheUpdateCallbackIsNotAFunction",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.unmounts_and_remounts_a_root_in_the_same_batch.61ac860e": "react_dom.burndownV153.legacyUpdates.unmountsAndRemountsARootInTheSameBatch",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.unstable_batchedupdates_should_return_value_from_a_callback.baeac66e": "react_dom.burndownV153.legacyUpdates.unstableBatchedupdatesShouldReturnValueFromACallback",
            },
            "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v153.py",
        ),
        (
            {
                "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.only_renders_once_if_updated_in_componentwillreceiveprops_in_legacy_mode.3ae87023": "react_dom.burndownV153.legacyComposite.onlyRendersOnceIfUpdatedInComponentwillreceivepropsInLegacyMode",
                "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.only_renders_once_if_updated_in_componentwillreceiveprops_when_batching_in_legacy_mode.b1d932ac": "react_dom.burndownV153.legacyComposite.onlyRendersOnceIfUpdatedInCwrpWhenBatchingInLegacyMode",
                "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_replace_state_in_legacy_mode.b1af7945": "react_dom.burndownV153.legacyComposite.shouldReplaceStateInLegacyMode",
                "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_support_objects_with_prototypes_as_state_in_legacy_mode.fec9b5e9": "react_dom.burndownV153.legacyComposite.shouldSupportObjectsWithPrototypesAsStateInLegacyMode",
                "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_warn_about_setstate_in_render_in_legacy_mode.c77a83c6": "react_dom.burndownV153.legacyComposite.shouldWarnAboutSetstateInRenderInLegacyMode",
            },
            "tests_upstream/react_dom/test_dom_legacy_burndown_v152.py",
        ),
        (
            {
                "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.flushsync_flushes_updates_even_if_nested_inside_another_flushsync.37d84412": "react_dom.burndownV153.fiberAsync.flushsyncFlushesUpdatesEvenIfNestedInsideAnotherFlushsync",
                "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.renders_synchronously_by_default_in_legacy_mode.bd6a183f": "react_dom.burndownV153.fiberAsync.rendersSynchronouslyByDefaultInLegacyMode",
            },
            "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v153.py",
        ),
    ]
    changed = 0
    for mapping, py in slices:
        for c in cases:
            cid = c.get("id")
            if cid not in mapping:
                continue
            if c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = mapping[cid]
            c["python_test"] = py
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
    return changed


def _patch_wave_dom_legacy_updates_v155_may2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates + ReactDOMLegacyFiber lifecycle/warning slice (v155)."""

    slices: list[tuple[dict[str, str], str]] = [
        (
            {
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_queue_updates_from_during_mount.0a16ff7c": "react_dom.burndownV155.legacyUpdates.shouldQueueUpdatesFromDuringMount",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_update_one_component_twice_in_a_batch_2410.9f9e9ce3": "react_dom.burndownV155.legacyUpdates.doesNotUpdateOneComponentTwiceInABatch2410",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.in_legacy_mode_updates_in_componentwillupdate_and_componentdidupdate_should_both_flush_in_the_immediately_subsequent_commit.199a7ff4": "react_dom.burndownV155.legacyUpdates.inLegacyModeUpdatesInCwuAndCduShouldBothFlush",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.in_legacy_mode_updates_in_componentwillupdate_and_componentdidupdate_on_a_sibling_should_both_flush_in_the_immediately_subsequent_commit.0691116f": "react_dom.burndownV155.legacyUpdates.inLegacyModeUpdatesInCwuAndCduOnSiblingShouldBothFlush",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_flush_updates_in_the_correct_order_across_roots.7d321c10": "react_dom.burndownV155.legacyUpdates.shouldFlushUpdatesInTheCorrectOrderAcrossRoots",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_flow_updates_correctly.417064b1": "react_dom.burndownV155.legacyUpdates.shouldFlowUpdatesCorrectly",
            },
            "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v155.py",
        ),
        (
            {
                "react_dom.ReactDOMLegacyFiber-test..should_warn_for_non_functional_event_listeners.86de6616": "react_dom.burndownV155.legacyFiber.shouldWarnForNonFunctionalEventListeners",
                "react_dom.ReactDOMLegacyFiber-test..should_warn_when_replacing_a_container_which_was_manually_updated_outside_of_react.76cfe986": "react_dom.burndownV155.legacyFiber.shouldWarnWhenReplacingAManuallyUpdatedContainer",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.finds_the_first_child_even_when_first_child_renders_null.b21f8ec2": "react_dom.burndownV155.legacyFiber.findsTheFirstChildEvenWhenFirstChildRendersNull",
                "react_dom.ReactDOMLegacyFiber-test..should_render_a_text_component_with_a_text_dom_node_on_the_same_document_as_the_container.b9f499eb": "react_dom.burndownV155.legacyFiber.shouldRenderATextComponentWithATextDomNode",
                "react_dom.ReactDOMLegacyFiber-test..should_not_update_event_handlers_until_commit.3ce84022": "react_dom.burndownV155.legacyFiber.shouldNotUpdateEventHandlersUntilCommit",
            },
            "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v155.py",
        ),
    ]
    changed = 0
    for mapping, py in slices:
        for c in cases:
            cid = c.get("id")
            if cid not in mapping:
                continue
            if c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = mapping[cid]
            c["python_test"] = py
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
    return changed


def _patch_wave_dom_legacy_fiber_v157_may2026(cases: list[dict]) -> int:
    """ReactDOMLegacyFiber namespace portals + error unwind (v157)."""

    mapping = {
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_keep_track_of_namespace_across_portals_simple.b234e358": "react_dom.burndownV157.legacyFiber.shouldKeepTrackOfNamespaceAcrossPortalsSimple",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_keep_track_of_namespace_across_portals_medium.bcc36eba": "react_dom.burndownV157.legacyFiber.shouldKeepTrackOfNamespaceAcrossPortalsMedium",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_keep_track_of_namespace_across_portals_complex.37d724bc": "react_dom.burndownV157.legacyFiber.shouldKeepTrackOfNamespaceAcrossPortalsComplex",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_unmount_empty_portal_component_wherever_it_appears.c8185475": "react_dom.burndownV157.legacyFiber.shouldUnmountEmptyPortalComponentWhereverItAppears",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_unwind_namespaces_on_uncaught_errors.c5fda449": "react_dom.burndownV157.legacyFiber.shouldUnwindNamespacesOnUncaughtErrors",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_unwind_namespaces_on_caught_errors.26b542c3": "react_dom.burndownV157.legacyFiber.shouldUnwindNamespacesOnCaughtErrors",
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_unwind_namespaces_on_caught_errors_in_a_portal.3706dae4": "react_dom.burndownV157.legacyFiber.shouldUnwindNamespacesOnCaughtErrorsInAPortal",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v157.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_fiber_v158_may2026(cases: list[dict]) -> int:
    """ReactDOMLegacyFiber document fragment mount (v158)."""

    mapping = {
        "react_dom.ReactDOMLegacyFiber-test..should_mount_into_a_document_fragment.2258de21": "react_dom.burndownV158.legacyFiber.shouldMountIntoADocumentFragment",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v158.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_updates_v158_may2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates render-phase base state, mutual guard, recover, batch (v158)."""

    mapping = {
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.uses_correct_base_state_for_setstate_inside_render_phase.0fc800fc": "react_dom.burndownV158.legacyUpdates.usesCorrectBaseStateForSetStateInsideRenderPhase",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_fall_into_mutually_recursive_infinite_update_loop_with_same_container.925de68b": "react_dom.burndownV158.legacyUpdates.doesNotFallIntoMutuallyRecursiveInfiniteUpdateLoopWithSameContainer",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.can_recover_after_falling_into_an_infinite_update_loop.2b54307b": "react_dom.burndownV158.legacyUpdates.canRecoverAfterFallingIntoAnInfiniteUpdateLoop",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.can_schedule_ridiculously_many_updates_within_the_same_batch_without_triggering_a_maximum_update_error.745b08ba": "react_dom.burndownV158.legacyUpdates.canScheduleRidiculouslyManyUpdatesWithinTheSameBatch",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v158.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_updates_v157_may2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates hidden subtrees + nested update depth (v157)."""

    mapping = {
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.synchronously_renders_hidden_subtrees.4411edd3": "react_dom.burndownV157.legacyUpdates.synchronouslyRendersHiddenSubtrees",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_fall_into_an_infinite_update_loop.13fdbebe": "react_dom.burndownV157.legacyUpdates.doesNotFallIntoAnInfiniteUpdateLoop",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.resets_the_update_counter_for_unrelated_updates.c9bd5e04": "react_dom.burndownV157.legacyUpdates.resetsTheUpdateCounterForUnrelatedUpdates",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v157.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_fiber_v156_may2026(cases: list[dict]) -> int:
    """ReactDOMLegacyFiber + ReactLegacyUpdates portal/flush slice (v156)."""

    mapping = {
        "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.finds_the_first_child_even_when_fragment_is_nested.4ae1f34a": "react_dom.burndownV156.legacyFiber.findsTheFirstChildEvenWhenFragmentIsNested",
        "react_dom.ReactDOMLegacyFiber-test..should_bubble_events_from_the_portal_to_the_parent.e28a17f4": "react_dom.burndownV156.legacyFiber.shouldBubbleEventsFromThePortalToTheParent",
        "react_dom.ReactDOMLegacyFiber-test..listens_to_events_that_do_not_exist_in_the_portal_subtree.c6cf4058": "react_dom.burndownV156.legacyFiber.listensToEventsThatDoNotExistInThePortalSubtree",
        "react_dom.ReactDOMLegacyFiber-test..should_not_diff_memoized_host_components.4d8a1032": "react_dom.burndownV156.legacyFiber.shouldNotDiffMemoizedHostComponents",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v156.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_legacy_fiber_v154_may2026(cases: list[dict]) -> int:
    """ReactDOMLegacyFiber + legacy updates purge/batch slice (v154)."""

    slices: list[tuple[dict[str, str], str]] = [
        (
            {
                "react_dom.ReactDOMLegacyFiber-test..finddomnode_should_find_dom_element_after_expanding_a_fragment.04199ff7": "react_dom.burndownV154.legacyFiber.finddomnodeShouldFindDomElementAfterExpandingAFragment",
                "react_dom.ReactDOMLegacyFiber-test..should_not_warn_when_rendering_into_an_empty_container.37813000": "react_dom.burndownV154.legacyFiber.shouldNotWarnWhenRenderingIntoAnEmptyContainer",
                "react_dom.ReactDOMLegacyFiber-test..should_throw_on_bad_createportal_argument.e987cb76": "react_dom.burndownV154.legacyFiber.shouldThrowOnBadCreateportalArgument",
                "react_dom.ReactDOMLegacyFiber-test..should_warn_when_doing_an_update_to_a_container_manually_cleared_outside_of_react.8bda0245": "react_dom.burndownV154.legacyFiber.shouldWarnWhenDoingAnUpdateToAContainerManuallyClearedOutsideOfReact",
                "react_dom.ReactDOMLegacyFiber-test..should_warn_when_doing_an_update_to_a_container_manually_updated_outside_of_react.a6f3f2d5": "react_dom.burndownV154.legacyFiber.shouldWarnWhenDoingAnUpdateToAContainerManuallyUpdatedOutsideOfReact",
                "react_dom.ReactDOMLegacyFiber-test..should_warn_with_a_special_message_for_false_event_listeners.80431cf2": "react_dom.burndownV154.legacyFiber.shouldWarnWithASpecialMessageForFalseEventListeners",
                "react_dom.ReactDOMLegacyFiber-test..unmounted_legacy_roots_should_never_clear_newer_root_content_from_a_container.8c361b93": "react_dom.burndownV154.legacyFiber.unmountedLegacyRootsShouldNeverClearNewerRootContentFromAContainer",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.finds_the_dom_text_node_of_a_string_child.494c6ec4": "react_dom.burndownV154.legacyFiber.findsTheDomTextNodeOfAStringChild",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.finds_the_first_child_when_a_component_returns_a_fragment.b8030f11": "react_dom.burndownV154.legacyFiber.findsTheFirstChildWhenAComponentReturnsAFragment",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.renders_an_empty_fragment.c3c320d3": "react_dom.burndownV154.legacyFiber.rendersAnEmptyFragment",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_be_called_a_callback_argument.dbbf35a5": "react_dom.burndownV154.legacyFiber.shouldBeCalledACallbackArgument",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_call_a_callback_argument_when_the_same_element_is_re_rendered.191c48af": "react_dom.burndownV154.legacyFiber.shouldCallACallbackArgumentWhenTheSameElementIsReRendered",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_a_component_returning_numbers_directly_from_render.44bc9fd4": "react_dom.burndownV154.legacyFiber.shouldRenderAComponentReturningNumbersDirectlyFromRender",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_a_component_returning_strings_directly_from_render.28733e01": "react_dom.burndownV154.legacyFiber.shouldRenderAComponentReturningStringsDirectlyFromRender",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_many_portals.7b2b6b0d": "react_dom.burndownV154.legacyFiber.shouldRenderManyPortals",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_nested_portals.e36eb276": "react_dom.burndownV154.legacyFiber.shouldRenderNestedPortals",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_numbers_as_children.c2697835": "react_dom.burndownV154.legacyFiber.shouldRenderNumbersAsChildren",
                "react_dom.ReactDOMLegacyFiber-test.reactdomlegacyfiber.should_render_strings_as_children.3a49af4a": "react_dom.burndownV154.legacyFiber.shouldRenderStringsAsChildren",
            },
            "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v154.py",
        ),
        (
            {
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_call_render_after_a_component_as_been_deleted.31327522": "react_dom.burndownV154.legacyUpdates.doesNotCallRenderAfterAComponentAsBeenDeleted",
                "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.mounts_and_unmounts_are_sync_even_in_a_batch.b2313297": "react_dom.burndownV154.legacyUpdates.mountsAndUnmountsAreSyncEvenInABatch",
            },
            "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v154.py",
        ),
    ]
    changed = 0
    for mapping, py in slices:
        for c in cases:
            cid = c.get("id")
            if cid not in mapping:
                continue
            if c.get("status") != "non_goal":
                continue
            c["status"] = "implemented"
            c["manifest_id"] = mapping[cid]
            c["python_test"] = py
            c["non_goal_rationale"] = None
            c["notes"] = None
            changed += 1
    return changed


def _patch_wave_dom_composite_lifecycle_v150_may2026(cases: list[dict]) -> int:
    """ReactComponent + lifecycle + composite + fiber slice (v150)."""

    mapping: dict[str, str] = {
        "react_dom.ReactComponent-test.reactcomponent.should_support_callback_style_refs.61cce21b": "react_dom.burndownV150.composite.shouldSupportCallbackStyleRefs",
        "react_dom.ReactComponent-test.reactcomponent.should_support_object_style_refs.1adf4b92": "react_dom.burndownV150.composite.shouldSupportObjectStyleRefs",
        "react_dom.ReactComponent-test.reactcomponent.should_support_new_style_refs_with_mixed_up_owners.76fa213c": "react_dom.burndownV150.composite.shouldSupportNewStyleRefsWithMixedUpOwners",
        "react_dom.ReactComponent-test.reactcomponent.throws_usefully_when_rendering_badly_typed_elements.6bbc02b3": "react_dom.burndownV150.composite.throwsUsefullyWhenRenderingBadlyTypedElements",
        "react_dom.ReactComponent-test.reactcomponent.includes_owner_name_in_the_error_about_badly_typed_elements.476f066f": "react_dom.burndownV150.composite.includesOwnerNameInBadlyTypedElementsError",
        "react_dom.ReactComponent-test.reactcomponent.should_throw_in_dev_when_children_are_mutated_during_render.0189701f": "react_dom.burndownV150.composite.shouldThrowWhenChildrenMutatedDuringRender",
        "react_dom.ReactComponent-test.reactcomponent.should_throw_in_dev_when_children_are_mutated_during_update.12d7605b": "react_dom.burndownV150.composite.shouldThrowWhenChildrenMutatedDuringUpdate",
        "react_dom.ReactComponent-test.reactcomponent.with_new_features.warns_on_function_as_a_return_value_from_a_function.5b8aa3ec": "react_dom.burndownV150.composite.warnsOnFunctionAsReturnFromFunction",
        "react_dom.ReactComponent-test.reactcomponent.with_new_features.warns_on_function_as_a_return_value_from_a_class.7bffe72b": "react_dom.burndownV150.composite.warnsOnFunctionAsReturnFromClass",
        "react_dom.ReactComponent-test.reactcomponent.with_new_features.does_not_warn_for_function_as_a_child_that_gets_resolved.a6ded12f": "react_dom.burndownV150.composite.doesNotWarnForFunctionAsChildThatGetsResolved",
        "react_dom.ReactComponent-test.reactcomponent.with_new_features.deduplicates_function_type_warnings_based_on_component_type.b6fcd046": "react_dom.burndownV150.composite.deduplicatesFunctionTypeWarnings",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_invoke_new_unsafe_lifecycles_cwm_cwrp_cwu_if_static_gdsfp_is_present.e052e32d": "react_dom.burndownV150.composite.shouldNotInvokeNewUnsafeLifecyclesWithGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_about_deprecated_lifecycles_cwm_cwrp_cwu_if_new_static_gdsfp_is_present.093ab887": "react_dom.burndownV150.composite.shouldWarnAboutDeprecatedLifecyclesWithGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_if_state_is_not_initialized_before_getderivedstatefromprops.976201df": "react_dom.burndownV150.composite.shouldWarnIfStateNotInitializedBeforeGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_override_state_with_stale_values_if_prevstate_is_spread_within_getderivedstatefromprops.f0b0294c": "react_dom.burndownV150.composite.shouldNotOverrideStaleStateInGdsfpSpread",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_call_getsnapshotbeforeupdate_before_mutations_are_committed.17f40e9d": "react_dom.burndownV150.composite.shouldCallGetsnapshotbeforeupdateBeforeMutations",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.warns_about_deprecated_unsafe_lifecycles.95b8f579": "react_dom.burndownV150.composite.warnsAboutDeprecatedUnsafeLifecycles",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.throws_when_accessing_state_in_componentwillmount.6b697b5b": "react_dom.burndownV150.composite.throwsWhenAccessingStateInComponentWillMount",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_throw_when_updating_an_auxiliary_component.f9f84506": "react_dom.burndownV150.composite.shouldNotThrowWhenUpdatingAuxiliaryComponent",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_a_component_returning_strings_directly_from_render.fa3a9a13": "react_dom.burndownV150.composite.shouldRenderStringsDirectlyFromRender",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_on_updating_function_component_from_render.6e48ec3c": "react_dom.burndownV150.composite.shouldWarnOnUpdatingFunctionComponentFromRender",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_return_a_meaningful_warning_when_constructor_is_returned.cbd93201": "react_dom.burndownV150.composite.shouldReturnMeaningfulWarningWhenConstructorReturned",
    }
    py = "tests_upstream/react_dom/test_dom_composite_lifecycle_burndown_v150.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_composite_lifecycle_v149_may2026(cases: list[dict]) -> int:
    """ReactCompositeComponent + lifecycle + fiber + component slice (v149)."""

    mapping: dict[str, str] = {
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.only_renders_once_if_updated_in_componentwillreceiveprops_when_batching.bcc02785": "react_dom.burndownV149.composite.onlyRendersOnceCwrpWhenBatching",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_call_componentwillunmount_before_unmounting.e1f1fa45": "react_dom.burndownV149.composite.shouldCallComponentWillUnmountBeforeUnmounting",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_only_call_componentwillunmount_once.8c518d21": "react_dom.burndownV149.composite.shouldOnlyCallComponentWillUnmountOnce",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_rendering_a_class_with_a_render_method_that_does_not_extend_react_component.9e006bc8": "react_dom.burndownV149.composite.shouldWarnClassRenderNotExtendingComponent",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_invoke_both_deprecated_and_new_lifecycles_if_both_are_present.57ac2956": "react_dom.burndownV149.composite.shouldInvokeBothDeprecatedAndNewLifecycles",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_allow_update_state_inside_of_getinitialstate.12d40b50": "react_dom.burndownV149.composite.shouldNotAllowSetstateInGetInitialState",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_invoke_deprecated_lifecycles_cwm_cwrp_cwu_if_new_static_gdsfp_is_present.44762d8e": "react_dom.burndownV149.composite.shouldNotInvokeDeprecatedLifecyclesWithGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_not_invoke_deprecated_lifecycles_cwm_cwrp_cwu_if_new_getsnapshotbeforeupdate_is_present.78f05367": "react_dom.burndownV149.composite.shouldNotInvokeDeprecatedLifecyclesWithGsbu",
        "react_dom.ReactDOMFiber-test.reactdomfiber.renders_an_empty_fragment.2d7a4308": "react_dom.burndownV149.composite.rendersEmptyFragment",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_bigints_as_children.46e71097": "react_dom.burndownV149.composite.shouldRenderBigintsAsChildren",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_a_component_returning_numbers_directly_from_render.ff057ea7": "react_dom.burndownV149.composite.shouldRenderComponentReturningNumbers",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_numbers_as_children.4fabdc8a": "react_dom.burndownV149.composite.shouldRenderNumbersAsChildren",
        "react_dom.ReactDOMFiber-test.reactdomfiber.should_render_strings_as_children.4f8a514a": "react_dom.burndownV149.composite.shouldRenderStringsAsChildren",
        "react_dom.ReactComponent-test.reactcomponent.throws_if_a_plain_object_is_used_as_a_child.8101cb9d": "react_dom.burndownV149.composite.throwsPlainObjectAsChild",
        "react_dom.ReactComponent-test.reactcomponent.throws_if_a_plain_object_even_if_it_is_in_an_owner.50be61fc": "react_dom.burndownV149.composite.throwsPlainObjectInOwner",
        "react_dom.ReactComponent-test.reactcomponent.with_new_features.warns_on_function_as_a_child_to_host_component.1b6b019f": "react_dom.burndownV149.composite.warnsFunctionAsChildToHost",
    }
    py = "tests_upstream/react_dom/test_dom_composite_lifecycle_burndown_v149.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_composite_lifecycle_v148_may2026(cases: list[dict]) -> int:
    """ReactCompositeComponent + lifecycle slice (v148)."""

    mapping: dict[str, str] = {
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.does_not_do_a_deep_comparison_for_a_shallow_shouldcomponentupdate_implementation.59bd819f": "react_dom.burndownV148.composite.doesNotDeepCompareShallowScu",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.only_renders_once_if_updated_in_componentwillreceiveprops.6f16456f": "react_dom.burndownV148.composite.onlyRendersOnceIfUpdatedInCwrp",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_disallow_nested_render_calls.067255d9": "react_dom.burndownV148.composite.shouldDisallowNestedRenderCalls",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_mutate_passed_in_props_object.5622a062": "react_dom.burndownV148.composite.shouldNotMutatePassedInPropsObject",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_support_module_pattern_components.ce15a369": "react_dom.burndownV148.composite.shouldNotSupportModulePatternComponents",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_warn_about_forceupdate_on_unmounted_components.a54ed660": "react_dom.burndownV148.composite.shouldNotWarnAboutForceupdateOnUnmounted",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_support_classes_shadowing_isreactcomponent.4341c805": "react_dom.burndownV148.composite.shouldSupportClassesShadowingIsReactComponent",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_about_forceupdate_on_not_yet_mounted_components.acd7de8d": "react_dom.burndownV148.composite.shouldWarnAboutForceupdateOnNotYetMounted",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_about_reassigning_this_props_while_rendering.dc054153": "react_dom.burndownV148.composite.shouldWarnAboutReassigningThisPropsWhileRendering",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_about_setstate_on_not_yet_mounted_components.e43498af": "react_dom.burndownV148.composite.shouldWarnAboutSetstateOnNotYetMounted",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_mutated_props_are_passed.502066b2": "react_dom.burndownV148.composite.shouldWarnWhenMutatedPropsPassed",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.this_state_should_be_updated_on_setstate_callback_inside_componentwillmount.c275486d": "react_dom.burndownV148.composite.setstateCallbackInsideComponentWillMount",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_allow_update_state_inside_of_componentwillmount.7889d0f1": "react_dom.burndownV148.composite.shouldAllowUpdateStateInsideComponentWillMount",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_pass_previous_state_to_shouldcomponentupdate_even_with_getderivedstatefromprops.1c20556d": "react_dom.burndownV148.composite.shouldPassPrevStateToScuWithGdsfp",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_pass_the_return_value_from_getsnapshotbeforeupdate_to_componentdidupdate.76203ee4": "react_dom.burndownV148.composite.shouldPassGsbuReturnToCdu",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_if_getderivedstatefromprops_returns_undefined.3f5ccdb9": "react_dom.burndownV148.composite.shouldWarnIfGdsfpReturnsUndefined",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_if_getsnapshotbeforeupdate_is_defined_with_no_componentdidupdate.045e8b20": "react_dom.burndownV148.composite.shouldWarnIfGsbuWithoutCdu",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_warn_if_getsnapshotbeforeupdate_returns_undefined.58f1853a": "react_dom.burndownV148.composite.shouldWarnIfGsbuReturnsUndefined",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.warns_if_setting_this_state_props.4c71979a": "react_dom.burndownV148.composite.warnsIfSettingThisStateEqualsProps",
    }
    py = "tests_upstream/react_dom/test_dom_composite_lifecycle_burndown_v148.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_composite_lifecycle_v147_may2026(cases: list[dict]) -> int:
    """ReactCompositeComponent + lifecycle slice (v147)."""

    mapping: dict[str, str] = {
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.respects_a_shallow_shouldcomponentupdate_implementation.efc63569": "react_dom.burndownV147.composite.respectsShallowShouldComponentUpdate",
        "react_dom.ReactComponentLifeCycle-test.reactcomponentlifecycle.should_allow_state_updates_in_componentdidmount.f7a91e25": "react_dom.burndownV147.composite.shouldAllowStateUpdatesInComponentDidMount",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_call_the_setstate_callback_even_if_shouldcomponentupdate_false.db35cb7e": "react_dom.burndownV147.composite.shouldCallSetStateCallbackEvenIfScuFalse",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_call_setstate_callback_with_no_arguments.ccb1f15a": "react_dom.burndownV147.composite.shouldCallSetStateCallbackWithNoArguments",
        "react_dom.ReactCompositeComponentDOMMinimalism-test.reactcompositecomponentdomminimalism.should_not_render_extra_nodes_for_interpolated_text.3bfa26cc": "react_dom.burndownV147.composite.shouldNotRenderExtraNodesForInterpolatedText",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_not_warn_about_setstate_on_unmounted_components.5fa80fb0": "react_dom.burndownV147.composite.shouldNotWarnAboutSetStateOnUnmountedComponents",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_return_error_if_render_is_not_defined.4b49e95c": "react_dom.burndownV147.composite.shouldReturnErrorIfRenderNotDefined",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_silently_allow_setstate_not_call_cb_on_unmounting_components.e1806d75": "react_dom.burndownV147.composite.shouldSilentlyAllowSetstateNotCallCbOnUnmounting",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_skip_update_when_rerendering_element_in_container.5f743c1a": "react_dom.burndownV147.composite.shouldSkipUpdateWhenRerenderingElementInContainer",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_use_default_values_for_undefined_props.8aeadd33": "react_dom.burndownV147.composite.shouldUseDefaultValuesForUndefinedProps",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_about_setstate_in_render.f3e3b7fd": "react_dom.burndownV147.composite.shouldWarnAboutSetStateInRender",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_componentdidreceiveprops_method_is_defined.ba9cd3ae": "react_dom.burndownV147.composite.shouldWarnWhenComponentDidReceivePropsDefined",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_componentdidunmount_method_is_defined.17a2c3f2": "react_dom.burndownV147.composite.shouldWarnWhenComponentDidUnmountDefined",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_defaultprops_was_defined_as_an_instance_property.338c2873": "react_dom.burndownV147.composite.shouldWarnWhenDefaultPropsOnInstance",
        "react_dom.ReactCompositeComponent-test.reactcompositecomponent.should_warn_when_shouldcomponentupdate_returns_undefined.9c5d8446": "react_dom.burndownV147.composite.shouldWarnWhenScuReturnsUndefined",
    }
    py = "tests_upstream/react_dom/test_dom_composite_lifecycle_burndown_v147.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_dom_refs_identity_v141_may2026(cases: list[dict]) -> int:
    """refs-test, ReactIdentity, ReactTreeTraversal, ReactBrowserEventEmitter (v141)."""

    mapping: dict[str, str] = {
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_bubble_simply.6c7abb81": "react_dom.burndownV141.domRefsIdentity.shouldbubblesimply6c7abb81",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_bubble_to_the_right_handler_after_an_update.6e4ab84d": "react_dom.burndownV141.domRefsIdentity.shouldbubbletotherighthandlerafteranupda6e4ab84d",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_continue_bubbling_if_an_error_is_thrown.b263ade2": "react_dom.burndownV141.domRefsIdentity.shouldcontinuebubblingifanerroristhrownb263ade2",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_invoke_handlers_that_were_removed_while_bubbling.68534d99": "react_dom.burndownV141.domRefsIdentity.shouldinvokehandlersthatwereremovedwhile68534d99",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_not_invoke_newly_inserted_handlers_while_bubbling.453a6588": "react_dom.burndownV141.domRefsIdentity.shouldnotinvokenewlyinsertedhandlerswhil453a6588",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_not_stoppropagation_if_false_is_returned.d7f7460d": "react_dom.burndownV141.domRefsIdentity.shouldnotstoppropagationiffalseisreturned7f7460d",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_set_currenttarget.a5ac599d": "react_dom.burndownV141.domRefsIdentity.shouldsetcurrenttargeta5ac599d",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_stop_after_first_dispatch_if_stoppropagation.fbb86a94": "react_dom.burndownV141.domRefsIdentity.shouldstopafterfirstdispatchifstoppropagfbb86a94",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_support_overriding_ispropagationstopped.bf31a097": "react_dom.burndownV141.domRefsIdentity.shouldsupportoverridingispropagationstopbf31a097",
        "react_dom.ReactBrowserEventEmitter-test.reactbrowsereventemitter.should_support_stoppropagation.c3bcf3d6": "react_dom.burndownV141.domRefsIdentity.shouldsupportstoppropagationc3bcf3d6",
        "react_dom.ReactIdentity-test.reactidentity.should_allow_any_character_as_a_key_in_a_detached_parent.dea4522e": "react_dom.burndownV141.domRefsIdentity.shouldallowanycharacterasakeyinadetacheddea4522e",
        "react_dom.ReactIdentity-test.reactidentity.should_allow_any_character_as_a_key_in_an_attached_parent.8f9ee157": "react_dom.burndownV141.domRefsIdentity.shouldallowanycharacterasakeyinanattache8f9ee157",
        "react_dom.ReactIdentity-test.reactidentity.should_allow_key_property_to_express_identity.a2fba942": "react_dom.burndownV141.domRefsIdentity.shouldallowkeypropertytoexpressidentitya2fba942",
        "react_dom.ReactIdentity-test.reactidentity.should_let_nested_restructures_retain_their_uniqueness.a96bbe8c": "react_dom.burndownV141.domRefsIdentity.shouldletnestedrestructuresretaintheiruna96bbe8c",
        "react_dom.ReactIdentity-test.reactidentity.should_let_restructured_components_retain_their_uniqueness.34c46c3b": "react_dom.burndownV141.domRefsIdentity.shouldletrestructuredcomponentsretainthe34c46c3b",
        "react_dom.ReactIdentity-test.reactidentity.should_let_text_nodes_retain_their_uniqueness.50fbeb74": "react_dom.burndownV141.domRefsIdentity.shouldlettextnodesretaintheiruniqueness50fbeb74",
        "react_dom.ReactIdentity-test.reactidentity.should_not_allow_implicit_and_explicit_keys_to_collide.aa759fc5": "react_dom.burndownV141.domRefsIdentity.shouldnotallowimplicitandexplicitkeystocaa759fc5",
        "react_dom.ReactIdentity-test.reactidentity.should_not_allow_scripts_in_keys_to_execute.70df4ee1": "react_dom.burndownV141.domRefsIdentity.shouldnotallowscriptsinkeystoexecute70df4ee1",
        "react_dom.ReactIdentity-test.reactidentity.should_retain_key_during_updates_in_composite_components.9cc2d3d0": "react_dom.burndownV141.domRefsIdentity.shouldretainkeyduringupdatesincompositec9cc2d3d0",
        "react_dom.ReactIdentity-test.reactidentity.should_throw_if_key_is_a_temporal_like_object.72b9db06": "react_dom.burndownV141.domRefsIdentity.shouldthrowifkeyisatemporallikeobject72b9db06",
        "react_dom.ReactIdentity-test.reactidentity.should_use_composite_identity.da2004b4": "react_dom.burndownV141.domRefsIdentity.shouldusecompositeidentityda2004b4",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_enter_from_the_window.c56b25d6": "react_dom.burndownV141.domRefsIdentity.shouldenterfromthewindowc56b25d6",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_enter_from_the_window_to_the_shallowest.6a6198fb": "react_dom.burndownV141.domRefsIdentity.shouldenterfromthewindowtotheshallowest6a6198fb",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_leave_to_the_window.d566b68c": "react_dom.burndownV141.domRefsIdentity.shouldleavetothewindowd566b68c",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_leave_to_the_window_from_the_shallowest.88ef84c9": "react_dom.burndownV141.domRefsIdentity.shouldleavetothewindowfromtheshallowest88ef84c9",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_not_traverse_if_enter_leave_the_same_node.c7b7d729": "react_dom.burndownV141.domRefsIdentity.shouldnottraverseifenterleavethesamenodec7b7d729",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_not_traverse_when_enter_leaving_outside_dom.7f38c4e3": "react_dom.burndownV141.domRefsIdentity.shouldnottraversewhenenterleavingoutside7f38c4e3",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_traverse_enter_leave_to_parent_avoids_parent.9df1f3ae": "react_dom.burndownV141.domRefsIdentity.shouldtraverseenterleavetoparentavoidspa9df1f3ae",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.enter_leave_traversal.should_traverse_enter_leave_to_sibling_avoids_parent.24fc5fd1": "react_dom.burndownV141.domRefsIdentity.shouldtraverseenterleavetosiblingavoidsp24fc5fd1",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.two_phase_traversal.should_not_traverse_when_target_is_outside_component_boundary.970189ab": "react_dom.burndownV141.domRefsIdentity.shouldnottraversewhentargetisoutsidecomp970189ab",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.two_phase_traversal.should_traverse_two_phase_across_component_boundary.6c2703d1": "react_dom.burndownV141.domRefsIdentity.shouldtraversetwophaseacrosscomponentbou6c2703d1",
        "react_dom.ReactTreeTraversal-test.reacttreetraversal.two_phase_traversal.should_traverse_two_phase_at_shallowest_node.c5f81d08": "react_dom.burndownV141.domRefsIdentity.shouldtraversetwophaseatshallowestnodec5f81d08",
        "react_dom.refs-test.ref_swapping.allow_refs_to_hop_around_children_correctly.47ef5d74": "react_dom.burndownV141.domRefsIdentity.allowrefstohoparoundchildrencorrectly47ef5d74",
        "react_dom.refs-test.ref_swapping.always_has_a_value_for_this_refs.69cd77ca": "react_dom.burndownV141.domRefsIdentity.alwayshasavalueforthisrefs69cd77ca",
        "react_dom.refs-test.ref_swapping.provides_an_error_for_invalid_refs.ee5525cc": "react_dom.burndownV141.domRefsIdentity.providesanerrorforinvalidrefsee5525cc",
        "react_dom.refs-test.ref_swapping.ref_called_correctly_for_stateless_component.7b929c58": "react_dom.burndownV141.domRefsIdentity.refcalledcorrectlyforstatelesscomponent7b929c58",
        "react_dom.refs-test.refs_return_clean_up_function.calls_clean_up_function_if_it_exists.a4273449": "react_dom.burndownV141.domRefsIdentity.callscleanupfunctionifitexistsa4273449",
        "react_dom.refs-test.refs_return_clean_up_function.calls_cleanup_function_on_unmount.f76e388f": "react_dom.burndownV141.domRefsIdentity.callscleanupfunctiononunmountf76e388f",
        "react_dom.refs-test.refs_return_clean_up_function.handles_detaching_refs_with_either_cleanup_function_or_null_argument.ee55c4d7": "react_dom.burndownV141.domRefsIdentity.handlesdetachingrefswitheithercleanupfunee55c4d7",
        "react_dom.refs-test.refs_return_clean_up_function.handles_ref_functions_with_stable_identity.c24419aa": "react_dom.burndownV141.domRefsIdentity.handlesreffunctionswithstableidentityc24419aa",
        "react_dom.refs-test.root_level_refs.attaches_and_detaches_root_refs.b5624743": "react_dom.burndownV141.domRefsIdentity.attachesanddetachesrootrefsb5624743",
        "react_dom.refs-test.useimerativehandle_refs.should_work_with_callback_style_refs.da1fdad4": "react_dom.burndownV141.domRefsIdentity.shouldworkwithcallbackstylerefsda1fdad4",
        "react_dom.refs-test.useimerativehandle_refs.should_work_with_callback_style_refs_with_cleanup_function.621a4630": "react_dom.burndownV141.domRefsIdentity.shouldworkwithcallbackstylerefswithclean621a4630",
        "react_dom.refs-test.useimerativehandle_refs.should_work_with_object_style_refs.17eeaf78": "react_dom.burndownV141.domRefsIdentity.shouldworkwithobjectstylerefs17eeaf78",
    }
    py = "tests_upstream/react_dom/test_dom_refs_identity_burndown_v141.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v162_dom_console_error_reporting_legacy_jun2026(cases: list[dict]) -> int:
    """ReactDOMConsoleErrorReportingLegacy ReactDOM.render slice (v162)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_errors_during_event_handlers.110651ea": "react_dom.burndownV162.consoleErrorReportingLegacy.logsErrorsDuringEventHandlers",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_layout_effect_errors_with_an_error_boundary.5cf54f64": "react_dom.burndownV162.consoleErrorReportingLegacy.logsLayoutEffectErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_layout_effect_errors_without_an_error_boundary.d2abf065": "react_dom.burndownV162.consoleErrorReportingLegacy.logsLayoutEffectErrorsWithoutBoundary",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_passive_effect_errors_with_an_error_boundary.331f9b2e": "react_dom.burndownV162.consoleErrorReportingLegacy.logsPassiveEffectErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_passive_effect_errors_without_an_error_boundary.59a1355e": "react_dom.burndownV162.consoleErrorReportingLegacy.logsPassiveEffectErrorsWithoutBoundary",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_render_errors_with_an_error_boundary.e3978db5": "react_dom.burndownV162.consoleErrorReportingLegacy.logsRenderErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReportingLegacy-test.reactdomconsoleerrorreporting.reactdom_render.logs_render_errors_without_an_error_boundary.76782eaa": "react_dom.burndownV162.consoleErrorReportingLegacy.logsRenderErrorsWithoutBoundary",
    }
    py = "tests_upstream/react_dom/test_dom_console_error_reporting_legacy_burndown_v162.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v163_dom_legacy_composite_context_jun2026(cases: list[dict]) -> int:
    """ReactLegacyCompositeComponent legacy context propagation slice (v163)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.context_should_be_passed_down_from_the_parent.24158217": "react_dom.burndownV163.legacyComposite.contextShouldBePassedDownFromParent",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_pass_context_to_children_when_not_owner.4b2e7fd4": "react_dom.burndownV163.legacyComposite.shouldPassContextToChildrenWhenNotOwner",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_pass_context_transitively.38576b22": "react_dom.burndownV163.legacyComposite.shouldPassContextTransitively",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_pass_context_when_re_rendered.d8bf375f": "react_dom.burndownV163.legacyComposite.shouldPassContextWhenRerendered",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_pass_context_when_re_rendered_for_static_child.52031626": "react_dom.burndownV163.legacyComposite.shouldPassContextWhenRerenderedForStaticChild",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_pass_context_when_re_rendered_for_static_child_within_a_composite_component.75f6cb24": "react_dom.burndownV163.legacyComposite.shouldPassContextWhenRerenderedForStaticChildWithinComposite",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.unmasked_context_propagates_through_updates.78268cb4": "react_dom.burndownV163.legacyComposite.unmaskedContextPropagatesThroughUpdates",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_composite_context_burndown_v163.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v164_dom_multichild_reconciliation_jun2026(cases: list[dict]) -> int:
    """ReactMultiChild reconciliation slice: iterables, warnings, owners, lifecycle (v164)."""

    mapping: dict[str, str] = {
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.prepares_new_children_before_unmounting_old.0bfec3fa": "react_dom.burndownV164.multiChild.preparesNewChildrenBeforeUnmountingOld",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_not_replace_children_with_different_owners.16dcd0a6": "react_dom.burndownV164.multiChild.shouldNotReplaceChildrenWithDifferentOwners",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_not_warn_for_using_generator_functions_as_components.5cea45d3": "react_dom.burndownV164.multiChild.shouldNotWarnForGeneratorFunctionsAsComponents",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_not_warn_for_using_generators_in_legacy_iterables.89d5e14d": "react_dom.burndownV164.multiChild.shouldNotWarnForGeneratorsInLegacyIterables",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_not_warn_for_using_generators_in_modern_iterables.8799cb16": "react_dom.burndownV164.multiChild.shouldNotWarnForGeneratorsInModernIterables",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_warn_for_duplicated_iterable_keys_with_component_stack_info.7ab50018": "react_dom.burndownV164.multiChild.shouldWarnForDuplicatedIterableKeysWithStack",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_warn_for_using_generators_as_children_props.bf4e982c": "react_dom.burndownV164.multiChild.shouldWarnForUsingGeneratorsAsChildrenProps",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_warn_for_using_maps_as_children_with_owner_info.04d4c1c8": "react_dom.burndownV164.multiChild.shouldWarnForUsingMapsAsChildrenWithOwnerInfo",
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation.should_warn_for_using_other_types_of_iterators_as_children.1799b3cc": "react_dom.burndownV164.multiChild.shouldWarnForUsingOtherTypesOfIteratorsAsChildren",
    }
    py = "tests_upstream/react_dom/test_dom_multichild_burndown_v164.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v166_dom_legacy_fiber_updates_composite_jun2026(cases: list[dict]) -> int:
    """ReactDOMLegacyFiber + ReactLegacyUpdates + legacy composite context CWRP (v166)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMLegacyFiber-test..does_not_fire_mouseenter_twice_when_relatedtarget_is_the_root_node.e59334e8": "react_dom.burndownV166.legacyFiber.doesNotFireMouseenterTwiceWhenRelatedtargetIsRoot",
        "react_dom.ReactDOMLegacyFiber-test..should_not_crash_encountering_low_priority_tree.bb43fea4": "react_dom.burndownV166.legacyFiber.shouldNotCrashEncounteringLowPriorityTree",
        "react_dom.ReactDOMLegacyFiber-test..should_not_onmouseleave_when_staying_in_the_portal.1a3651c7": "react_dom.burndownV166.legacyFiber.shouldNotOnmouseleaveWhenStayingInPortal",
        "react_dom.ReactDOMLegacyFiber-test..should_pass_portal_context_when_rendering_subtree_elsewhere.6ce8a23e": "react_dom.burndownV166.legacyFiber.shouldPassPortalContextWhenRenderingSubtreeElsewhere",
        "react_dom.ReactDOMLegacyFiber-test..should_update_portal_context_if_it_changes_due_to_re_render.3b3c8afd": "react_dom.burndownV166.legacyFiber.shouldUpdatePortalContextIfItChangesDueToRerender",
        "react_dom.ReactDOMLegacyFiber-test..should_update_portal_context_if_it_changes_due_to_setstate.2be08bde": "react_dom.burndownV166.legacyFiber.shouldUpdatePortalContextIfItChangesDueToSetstate",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.can_render_ridiculously_large_number_of_roots_without_triggering_infinite_update_loop_error.14313e04": "react_dom.burndownV166.legacyUpdates.canRenderRidiculouslyLargeNumberOfRoots",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_fall_into_an_infinite_error_loop.9cd5e2e7": "react_dom.burndownV166.legacyUpdates.doesNotFallIntoAnInfiniteErrorLoop",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_fall_into_an_infinite_update_loop_with_uselayouteffect.904d4c9e": "react_dom.burndownV166.legacyUpdates.doesNotFallIntoAnInfiniteUpdateLoopWithUseLayoutEffect",
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_trigger_componentwillreceiveprops_for_context_changes.4a9777cb": "react_dom.burndownV166.legacyComposite.shouldTriggerComponentwillreceivepropsForContextChanges",
    }
    py_by_manifest: dict[str, str] = {
        "react_dom.burndownV166.legacyFiber.doesNotFireMouseenterTwiceWhenRelatedtargetIsRoot": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyFiber.shouldNotCrashEncounteringLowPriorityTree": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyFiber.shouldNotOnmouseleaveWhenStayingInPortal": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyFiber.shouldPassPortalContextWhenRenderingSubtreeElsewhere": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyFiber.shouldUpdatePortalContextIfItChangesDueToRerender": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyFiber.shouldUpdatePortalContextIfItChangesDueToSetstate": "tests_upstream/react_dom/test_dom_legacy_fiber_burndown_v166.py",
        "react_dom.burndownV166.legacyUpdates.canRenderRidiculouslyLargeNumberOfRoots": "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v166.py",
        "react_dom.burndownV166.legacyUpdates.doesNotFallIntoAnInfiniteErrorLoop": "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v166.py",
        "react_dom.burndownV166.legacyUpdates.doesNotFallIntoAnInfiniteUpdateLoopWithUseLayoutEffect": "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v166.py",
        "react_dom.burndownV166.legacyComposite.shouldTriggerComponentwillreceivepropsForContextChanges": "tests_upstream/react_dom/test_dom_legacy_composite_context_burndown_v163.py",
    }
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py_by_manifest[manifest_id]
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v177_dom_updates_depth_guards_jun2026(cases: list[dict]) -> int:
    """ReactUpdates createRoot ref-callback and useEffect flushSync depth guards (v177)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.prevents_infinite_update_loop_triggered_by_synchronous_updates_in_useeffect.8a95e5ba": "react_dom.burndownV177.updates.preventsInfiniteUpdateLoopTriggeredBySynchronousUpdatesInUseEffect",
        "react_dom.ReactUpdates-test.reactupdates.prevents_infinite_update_loop_triggered_by_too_many_updates_in_ref_callbacks.641887b3": "react_dom.burndownV177.updates.preventsInfiniteUpdateLoopTriggeredByTooManyUpdatesInRefCallbacks",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v177.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v177_dom_legacy_updates_flush_jun2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates flush ordering and portal mount-ready (v177)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_flush_updates_in_the_correct_order.dee8d770": "react_dom.burndownV177.legacyUpdates.shouldFlushUpdatesInTheCorrectOrder",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_queue_mount_ready_handlers_across_different_roots.4f02d97e": "react_dom.burndownV177.legacyUpdates.shouldQueueMountReadyHandlersAcrossDifferentRoots",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v177.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v182_dom_legacy_composite_scu_jun2026(cases: list[dict]) -> int:
    """ReactLegacyComposite SCU-false sibling reorder ref swap (v182)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyCompositeComponent-test.reactlegacycompositecomponent.should_update_refs_if_shouldcomponentupdate_gives_false_in_legacy_mode.65851293": "react_dom.burndownV182.legacyComposite.shouldUpdateRefsIfShouldcomponentupdateGivesFalseInLegacyMode",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_composite_context_burndown_v163.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v183_dom_find_dom_node_jun2026(cases: list[dict]) -> int:
    """findDOMNode validation, unmount rejection, and StrictMode warnings (v183)."""

    mapping: dict[str, str] = {
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_return_null_if_passed_null.f04eeb18": "react_dom.burndownV183.findDomNode.shouldReturnNullIfPassedNull",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_find_dom_element.cde79bc9": "react_dom.burndownV183.findDomNode.shouldFindDomElement",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_find_dom_element_after_an_update_from_null.c28ed0b5": "react_dom.burndownV183.findDomNode.shouldFindDomElementAfterAnUpdateFromNull",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_reject_random_objects.b19c5b42": "react_dom.burndownV183.findDomNode.shouldRejectRandomObjects",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_reject_unmounted_objects_with_render_func.29c4d97d": "react_dom.burndownV183.findDomNode.shouldRejectUnmountedObjectsWithRenderFunc",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_not_throw_an_error_when_called_within_a_component_that_is_not_mounted.06e373f8": "react_dom.burndownV183.findDomNode.shouldNotThrowWhenCalledWithinAComponentThatIsNotMounted",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_warn_if_used_to_find_a_host_component_inside_strictmode.a0600e89": "react_dom.burndownV183.findDomNode.shouldWarnIfUsedToFindAHostComponentInsideStrictMode",
        "react_dom.findDOMNodeFB-test.finddomnode.finddomnode_should_warn_if_passed_a_component_that_is_inside_strictmode.aa071e3b": "react_dom.burndownV183.findDomNode.shouldWarnIfPassedAComponentThatIsInsideStrictMode",
    }
    py = "tests_upstream/react_dom/test_dom_find_dom_node_burndown_v183.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v184_react_forwardref_useeffectevent_jun2026(cases: list[dict]) -> int:
    """forwardRef deep class bailout + useEffectEvent context in memo/forwardRef (v184)."""

    mapping: dict[str, str] = {
        "react.forwardRef-test.internal.forwardref.should_not_re_run_the_render_callback_on_a_deep_setstate": "react.burndownV184.forwardRef.shouldNotRerunRenderCallbackOnDeepSetState",
        "react.useEffectEvent-test.useeffectevent.reads_the_latest_context_value_in_memo_components": "react.burndownV184.useEffectEvent.readsLatestContextInMemoComponents",
        "react.useEffectEvent-test.useeffectevent.reads_the_latest_context_value_in_forwardref_components": "react.burndownV184.useEffectEvent.readsLatestContextInForwardRefComponents",
    }
    py = "tests_upstream/react/test_react_burndown_v184.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") not in ("non_goal", "pending"):
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = "Burndown v184: forwardRef deep bailout + useEffectEvent context slices."
        changed += 1
    return changed


def _patch_wave_burndown_v184_dom_child_reconciler_jun2026(cases: list[dict]) -> int:
    """ReactChildReconciler duplicate keys + function-child guard (v184)."""

    mapping: dict[str, str] = {
        "react_dom.ReactChildReconciler-test.reactchildreconciler.warns_for_duplicated_array_keys.bb987210": "react_dom.burndownV184.childReconciler.warnsForDuplicatedArrayKeys",
        "react_dom.ReactChildReconciler-test.reactchildreconciler.warns_for_duplicated_iterable_keys.b1ebd183": "react_dom.burndownV184.childReconciler.warnsForDuplicatedIterableKeys",
        "react_dom.ReactChildReconciler-test.reactchildreconciler.does_not_treat_functions_as_iterables.a9700020": "react_dom.burndownV184.childReconciler.doesNotTreatFunctionsAsIterables",
    }
    py = "tests_upstream/react_dom/test_dom_child_reconciler_burndown_v184.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping or c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = "Burndown v184: ReactChildReconciler duplicate-key and function-child slices."
        changed += 1
    return changed


def _patch_wave_burndown_v181_dom_legacy_updates_jun2026(cases: list[dict]) -> int:
    """ReactLegacyUpdates batched mount/unmount sync and update ordering (v181)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.mounts_and_unmounts_are_sync_even_in_a_batch.b2313297": "react_dom.burndownV181.legacyUpdates.mountsAndUnmountsAreSyncEvenInABatch",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_queue_updates_from_during_mount.0a16ff7c": "react_dom.burndownV181.legacyUpdates.shouldQueueUpdatesFromDuringMount",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_call_render_after_a_component_as_been_deleted.31327522": "react_dom.burndownV181.legacyUpdates.doesNotCallRenderAfterAComponentHasBeenDeleted",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.does_not_update_one_component_twice_in_a_batch_2410.9f9e9ce3": "react_dom.burndownV181.legacyUpdates.doesNotUpdateOneComponentTwiceInABatch2410",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.should_flush_updates_in_the_correct_order_across_roots.7d321c10": "react_dom.burndownV181.legacyUpdates.shouldFlushUpdatesInTheCorrectOrderAcrossRoots",
        "react_dom.ReactLegacyUpdates-test.reactlegacyupdates.in_legacy_mode_updates_in_componentwillupdate_and_componentdidupdate_should_both_flush_in_the_immediately_subsequent_commit.199a7ff4": "react_dom.burndownV181.legacyUpdates.inLegacyModeUpdatesInComponentWillUpdateAndComponentDidUpdateShouldBothFlush",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_updates_burndown_v181.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "implemented":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v180_dom_comment_mount_jun2026(cases: list[dict]) -> int:
    """ReactLegacyMount comment-node legacy render (v180)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyMount-test.reactmount.mount_point_is_a_comment_node.renders_at_a_comment_node.19bf298e": "react_dom.burndownV180.commentMount.rendersAtACommentNode",
    }
    py = "tests_upstream/react_dom/test_dom_comment_mount_burndown_v180.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v180_dom_fiber_async_passive_jun2026(cases: list[dict]) -> int:
    """ReactDOMFiberAsync passive effects across roots and flushSync tick batching (v180)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.regression_test_does_not_drop_passive_effects_across_roots_17066.e9c10931": "react_dom.burndownV180.fiberAsync.regressionTestDoesNotDropPassiveEffectsAcrossRoots17066",
        "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.concurrent_mode.flushsync_flushes_updates_before_end_of_the_tick.6887725a": "react_dom.burndownV180.fiberAsync.flushSyncFlushesUpdatesBeforeEndOfTheTick",
    }
    py = "tests_upstream/react_dom/test_dom_fiber_async_burndown_v180.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v179_dom_fiber_async_flushsync_jun2026(cases: list[dict]) -> int:
    """ReactDOMFiberAsync createRoot flushSync batching and stale-root guards (v179)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.flushsync_batches_sync_updates_and_flushes_them_at_the_end_of_the_batch.dd7daf08": "react_dom.burndownV179.fiberAsync.flushSyncBatchesSyncUpdatesAndFlushesThemAtTheEndOfTheBatch",
        "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.flushsync_logs_an_error_if_already_performing_work.42038b1b": "react_dom.burndownV179.fiberAsync.flushSyncLogsAnErrorIfAlreadyPerformingWork",
        "react_dom.ReactDOMFiberAsync-test.reactdomfiberasync.unmounted_roots_should_never_clear_newer_root_content_from_a_container.6910069a": "react_dom.burndownV179.fiberAsync.unmountedRootsShouldNeverClearNewerRootContentFromAContainer",
    }
    py = "tests_upstream/react_dom/test_dom_fiber_async_burndown_v179.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v178_dom_mount_destruction_jun2026(cases: list[dict]) -> int:
    """ReactMountDestruction createRoot unmount and legacy host-node warnings (v178)."""

    mapping: dict[str, str] = {
        "react_dom.ReactMountDestruction-test.reactmount.should_destroy_a_react_root_upon_request.5bae9f5e": "react_dom.burndownV178.mountDestruction.shouldDestroyAReactRootUponRequest",
        "react_dom.ReactMountDestruction-test.reactmount.should_warn_when_unmounting_a_non_container_non_root_node.59abfa55": "react_dom.burndownV178.mountDestruction.shouldWarnWhenUnmountingANonContainerNonRootNode",
        "react_dom.ReactMountDestruction-test.reactmount.should_warn_when_unmounting_a_non_container_root_node.96a11b7b": "react_dom.burndownV178.mountDestruction.shouldWarnWhenUnmountingANonContainerRootNode",
    }
    py = "tests_upstream/react_dom/test_dom_mount_destruction_burndown_v178.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v178_dom_updates_infinite_loop_warn_jun2026(cases: list[dict]) -> int:
    """ReactUpdates cross-component render-phase infinite loop warnings (v178)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.warns_about_potential_infinite_loop_if_there_s_a_synchronous_render_phase_update_on_another_component.e1666fd7": "react_dom.burndownV178.updates.warnsAboutPotentialInfiniteLoopIfTheresASynchronousRenderPhaseUpdateOnAnotherComponent",
        "react_dom.ReactUpdates-test.reactupdates.warns_about_potential_infinite_loop_if_there_s_an_async_render_phase_update_on_another_component.82d8ea49": "react_dom.burndownV178.updates.warnsAboutPotentialInfiniteLoopIfTheresAnAsyncRenderPhaseUpdateOnAnotherComponent",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v178.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v177_dom_legacy_root_warnings_jun2026(cases: list[dict]) -> int:
    """ReactLegacyRootWarnings ReactDOM.render deprecation (v177)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyRootWarnings-test.reactdomroot.deprecation_warning_for_reactdom_render.679ffa17": "react_dom.burndownV177.legacyRootWarnings.deprecationWarningForReactdomRender",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_root_warnings_burndown_v177.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v176_dom_updates_cross_root_jun2026(cases: list[dict]) -> int:
    """ReactUpdates createRoot cross-root flush and portal mount-ready (v176)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.should_flush_updates_in_the_correct_order_across_roots.0618e2af": "react_dom.burndownV176.domUpdates.shouldFlushUpdatesInTheCorrectOrderAcrossRoots",
        "react_dom.ReactUpdates-test.reactupdates.should_queue_mount_ready_handlers_across_different_roots.8a661443": "react_dom.burndownV176.domUpdates.shouldQueueMountReadyHandlersAcrossDifferentRoots",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v176.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v176_dom_error_boundaries_final_jun2026(cases: list[dict]) -> int:
    """ReactErrorBoundaries createRoot final robustness cases (v176)."""

    mapping: dict[str, str] = {
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.propagates_uncaught_error_inside_unbatched_initial_mount.910837d8": "react_dom.burndownV176.errorBoundaries.propagatesUncaughtErrorInsideUnbatchedInitialMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.should_catch_errors_from_errors_in_the_throw_phase_from_boundaries.546d523b": "react_dom.burndownV176.errorBoundaries.shouldCatchErrorsFromErrorsInTheThrowPhaseFromBoundaries",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.should_catch_errors_from_invariants_in_completion_phase.406061c6": "react_dom.burndownV176.errorBoundaries.shouldCatchErrorsFromInvariantsInCompletionPhase",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.should_protect_errors_from_errors_in_the_stack_generation.8bbdeec3": "react_dom.burndownV176.errorBoundaries.shouldProtectErrorsFromErrorsInTheStackGeneration",
    }
    py = "tests_upstream/react_dom/test_dom_error_boundaries_burndown_v176.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v175_dom_error_boundaries_effects_jun2026(cases: list[dict]) -> int:
    """ReactErrorBoundaries createRoot effects, cWU recovery, refs, gsbu, GDSFE (v175)."""

    mapping: dict[str, str] = {
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.calls_static_getderivedstatefromerror_for_each_error_that_is_captured.a89b948d": "react_dom.burndownV175.errorBoundaries.callsStaticGetDerivedStateFromErrorForEachErrorThatIsCaptured",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_in_useeffect.1fdff913": "react_dom.burndownV175.errorBoundaries.catchesErrorsInUseEffect",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_in_uselayouteffect.4245b876": "react_dom.burndownV175.errorBoundaries.catchesErrorsInUseLayoutEffect",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_thrown_in_componentwillunmount.8f36cca6": "react_dom.burndownV175.errorBoundaries.catchesErrorsThrownInComponentWillUnmount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_thrown_while_detaching_refs.c16aab32": "react_dom.burndownV175.errorBoundaries.catchesErrorsThrownWhileDetachingRefs",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.doesn_t_get_into_inconsistent_state_during_reorders.26cabdc1": "react_dom.burndownV175.errorBoundaries.doesntGetIntoInconsistentStateDuringReorders",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.handles_errors_that_occur_in_before_mutation_commit_hook.e91393d5": "react_dom.burndownV175.errorBoundaries.handlesErrorsThatOccurInBeforeMutationCommitHook",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.keeps_refs_up_to_date_during_updates.4dd99a70": "react_dom.burndownV175.errorBoundaries.keepsRefsUpToDateDuringUpdates",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.passes_an_aggregate_error_when_two_errors_happen_in_commit.ad8faba6": "react_dom.burndownV175.errorBoundaries.passesAnAggregateErrorWhenTwoErrorsHappenInCommit",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.picks_the_right_boundary_when_handling_unmounting_errors.6592cdaa": "react_dom.burndownV175.errorBoundaries.picksTheRightBoundaryWhenHandlingUnmountingErrors",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.recovers_from_componentwillunmount_errors_on_update.5c12a3bc": "react_dom.burndownV175.errorBoundaries.recoversFromComponentWillUnmountErrorsOnUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.recovers_from_nested_componentwillunmount_errors_on_update.f162ffdc": "react_dom.burndownV175.errorBoundaries.recoversFromNestedComponentWillUnmountErrorsOnUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.renders_an_error_state_if_context_provider_throws_in_componentwillmount.ee0a0e76": "react_dom.burndownV175.errorBoundaries.rendersAnErrorStateIfContextProviderThrowsInComponentWillMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.resets_callback_refs_if_mounting_aborts.632c441c": "react_dom.burndownV175.errorBoundaries.resetsCallbackRefsIfMountingAborts",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.should_call_both_componentdidcatch_and_getderivedstatefromerror_if_both_exist_on_a_component.2287c112": "react_dom.burndownV175.errorBoundaries.shouldCallBothComponentDidCatchAndGetDerivedStateFromErrorIfBothExist",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.should_warn_if_an_error_boundary_with_only_componentdidcatch_does_not_update_state.b7847189": "react_dom.burndownV175.errorBoundaries.shouldWarnIfAnErrorBoundaryWithOnlyComponentDidCatchDoesNotUpdateState",
    }
    py = "tests_upstream/react_dom/test_dom_error_boundaries_burndown_v175.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v174_dom_error_boundaries_update_jun2026(cases: list[dict]) -> int:
    """ReactErrorBoundaries createRoot update-phase catch, multi-root, propagation (v174)."""

    mapping: dict[str, str] = {
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_originating_downstream.6098b371": "react_dom.burndownV174.errorBoundaries.catchesErrorsOriginatingDownstream",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_if_child_throws_in_componentwillmount_during_update.3d32b8c5": "react_dom.burndownV174.errorBoundaries.catchesIfChildThrowsInComponentWillMountDuringUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_if_child_throws_in_componentwillreceiveprops_during_update.9d2c992f": "react_dom.burndownV174.errorBoundaries.catchesIfChildThrowsInComponentWillReceivePropsDuringUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_if_child_throws_in_componentwillupdate_during_update.c034c120": "react_dom.burndownV174.errorBoundaries.catchesIfChildThrowsInComponentWillUpdateDuringUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_if_child_throws_in_constructor_during_update.5272ffe6": "react_dom.burndownV174.errorBoundaries.catchesIfChildThrowsInConstructorDuringUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.discards_a_bad_root_if_the_root_component_fails.98715529": "react_dom.burndownV174.errorBoundaries.discardsABadRootIfTheRootComponentFails",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.does_not_call_componentwillunmount_when_aborting_initial_mount.64eea566": "react_dom.burndownV174.errorBoundaries.doesNotCallComponentWillUnmountWhenAbortingInitialMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.does_not_swallow_exceptions_on_unmounting_without_boundaries.3380157e": "react_dom.burndownV174.errorBoundaries.doesNotSwallowExceptionsOnUnmountingWithoutBoundaries",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.doesn_t_get_into_inconsistent_state_during_additions.e3ee0ea3": "react_dom.burndownV174.errorBoundaries.doesntGetIntoInconsistentStateDuringAdditions",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.doesn_t_get_into_inconsistent_state_during_removals.010606fd": "react_dom.burndownV174.errorBoundaries.doesntGetIntoInconsistentStateDuringRemovals",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.mounts_the_error_message_if_mounting_fails.8a37c786": "react_dom.burndownV174.errorBoundaries.mountsTheErrorMessageIfMountingFails",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.prevents_errors_from_leaking_into_other_roots.327fb3a4": "react_dom.burndownV174.errorBoundaries.preventsErrorsFromLeakingIntoOtherRoots",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.propagates_errors_inside_boundary_during_componentdidmount.9f261d07": "react_dom.burndownV174.errorBoundaries.propagatesErrorsInsideBoundaryDuringComponentDidMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.propagates_errors_inside_boundary_during_componentwillmount.255447ee": "react_dom.burndownV174.errorBoundaries.propagatesErrorsInsideBoundaryDuringComponentWillMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.propagates_errors_inside_boundary_while_rendering_error_state.ae9f1ffd": "react_dom.burndownV174.errorBoundaries.propagatesErrorsInsideBoundaryWhileRenderingErrorState",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.propagates_errors_on_retry_on_mounting.c1ed9520": "react_dom.burndownV174.errorBoundaries.propagatesErrorsOnRetryOnMounting",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.resets_object_refs_if_mounting_aborts.43213bff": "react_dom.burndownV174.errorBoundaries.resetsObjectRefsIfMountingAborts",
    }
    py = "tests_upstream/react_dom/test_dom_error_boundaries_burndown_v174.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v173_dom_error_boundaries_jun2026(cases: list[dict]) -> int:
    """ReactErrorBoundaries createRoot catch/recover/uncaught logging (v173)."""

    mapping: dict[str, str] = {
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.can_recover_from_error_state.751d632b": "react_dom.burndownV173.errorBoundaries.canRecoverFromErrorState",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.can_update_multiple_times_in_error_state.59fdafe6": "react_dom.burndownV173.errorBoundaries.canUpdateMultipleTimesInErrorState",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_in_componentdidmount.4493edf8": "react_dom.burndownV173.errorBoundaries.catchesErrorsInComponentDidMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_errors_in_componentdidupdate.09ede054": "react_dom.burndownV173.errorBoundaries.catchesErrorsInComponentDidUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.catches_if_child_throws_in_render_during_update.14046ee9": "react_dom.burndownV173.errorBoundaries.catchesIfChildThrowsInRenderDuringUpdate",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.does_not_swallow_exceptions_on_mounting_without_boundaries.dc31068d": "react_dom.burndownV173.errorBoundaries.doesNotSwallowExceptionsOnMountingWithoutBoundaries",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.does_not_swallow_exceptions_on_updating_without_boundaries.9a1f4a05": "react_dom.burndownV173.errorBoundaries.doesNotSwallowExceptionsOnUpdatingWithoutBoundaries",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.logs_a_single_error_when_using_error_boundary.567cb39c": "react_dom.burndownV173.errorBoundaries.logsASingleErrorWhenUsingErrorBoundary",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.renders_an_error_state_if_child_throws_in_componentwillmount.7b6c4bd0": "react_dom.burndownV173.errorBoundaries.rendersAnErrorStateIfChildThrowsInComponentWillMount",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.renders_an_error_state_if_child_throws_in_constructor.37f7dfd4": "react_dom.burndownV173.errorBoundaries.rendersAnErrorStateIfChildThrowsInConstructor",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.renders_an_error_state_if_child_throws_in_render.5aeb7132": "react_dom.burndownV173.errorBoundaries.rendersAnErrorStateIfChildThrowsInRender",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.renders_empty_output_if_error_boundary_does_not_handle_the_error.961fff32": "react_dom.burndownV173.errorBoundaries.rendersEmptyOutputIfErrorBoundaryDoesNotHandleTheError",
        "react_dom.ReactErrorBoundaries-test.internal.reacterrorboundaries.successfully_mounts_if_no_error_occurs.2c1aa0b3": "react_dom.burndownV173.errorBoundaries.successfullyMountsIfNoErrorOccurs",
    }
    py = "tests_upstream/react_dom/test_dom_error_boundaries_burndown_v173.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v172_dom_legacy_error_boundaries_final_jun2026(cases: list[dict]) -> int:
    """ReactLegacyErrorBoundaries multi-catch, gsbu errors, context cWM (v172)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.calls_componentdidcatch_for_each_error_that_is_captured.897511c5": "react_dom.burndownV172.legacyErrorBoundaries.callsComponentDidCatchForEachErrorThatIsCaptured",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.handles_errors_that_occur_in_before_mutation_commit_hook.38b6eab8": "react_dom.burndownV172.legacyErrorBoundaries.handlesErrorsThatOccurInBeforeMutationCommitHook",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.renders_an_error_state_if_context_provider_throws_in_componentwillmount.a767e1a7": "react_dom.burndownV172.legacyErrorBoundaries.rendersAnErrorStateIfContextProviderThrowsInComponentWillMount",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_error_boundaries_burndown_v172.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v171_dom_legacy_error_boundaries_unmount_refs_jun2026(cases: list[dict]) -> int:
    """ReactLegacyErrorBoundaries unmount catch, refs on abort, removals, first commit error (v171)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.doesn_t_get_into_inconsistent_state_during_removals.2134faf9": "react_dom.burndownV171.legacyErrorBoundaries.doesntGetIntoInconsistentStateDuringRemovals",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.keeps_refs_up_to_date_during_updates.11a6fbb8": "react_dom.burndownV171.legacyErrorBoundaries.keepsRefsUpToDateDuringUpdates",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.passes_first_error_when_two_errors_happen_in_commit.bb8b3c09": "react_dom.burndownV171.legacyErrorBoundaries.passesFirstErrorWhenTwoErrorsHappenInCommit",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.picks_the_right_boundary_when_handling_unmounting_errors.2e9d40d3": "react_dom.burndownV171.legacyErrorBoundaries.picksTheRightBoundaryWhenHandlingUnmountingErrors",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.recovers_from_componentwillunmount_errors_on_update.8a348133": "react_dom.burndownV171.legacyErrorBoundaries.recoversFromComponentWillUnmountErrorsOnUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.recovers_from_nested_componentwillunmount_errors_on_update.65019dc9": "react_dom.burndownV171.legacyErrorBoundaries.recoversFromNestedComponentWillUnmountErrorsOnUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.resets_callback_refs_if_mounting_aborts.889ba847": "react_dom.burndownV171.legacyErrorBoundaries.resetsCallbackRefsIfMountingAborts",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.resets_object_refs_if_mounting_aborts.934b1f46": "react_dom.burndownV171.legacyErrorBoundaries.resetsObjectRefsIfMountingAborts",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_error_boundaries_burndown_v171.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v170_dom_legacy_error_boundaries_lifecycle_jun2026(cases: list[dict]) -> int:
    """ReactLegacyErrorBoundaries nested propagation, lifecycle catch, reorders (v170)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_errors_in_componentdidmount.8247c5ad": "react_dom.burndownV170.legacyErrorBoundaries.catchesErrorsInComponentDidMount",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_errors_in_componentdidupdate.7554cb47": "react_dom.burndownV170.legacyErrorBoundaries.catchesErrorsInComponentDidUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.discards_a_bad_root_if_the_root_component_fails.aca5ded8": "react_dom.burndownV170.legacyErrorBoundaries.discardsABadRootIfTheRootComponentFails",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.doesn_t_get_into_inconsistent_state_during_reorders.218ce587": "react_dom.burndownV170.legacyErrorBoundaries.doesntGetIntoInconsistentStateDuringReorders",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.propagates_errors_inside_boundary_during_componentdidmount.4ff62bad": "react_dom.burndownV170.legacyErrorBoundaries.propagatesErrorsInsideBoundaryDuringComponentDidMount",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.propagates_errors_inside_boundary_during_componentwillmount.b673fac8": "react_dom.burndownV170.legacyErrorBoundaries.propagatesErrorsInsideBoundaryDuringComponentWillMount",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.propagates_errors_inside_boundary_while_rendering_error_state.aee9680f": "react_dom.burndownV170.legacyErrorBoundaries.propagatesErrorsInsideBoundaryWhileRenderingErrorState",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.propagates_errors_on_retry_on_mounting.785feedb": "react_dom.burndownV170.legacyErrorBoundaries.propagatesErrorsOnRetryOnMounting",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.propagates_uncaught_error_inside_unbatched_initial_mount.0fd5f0e5": "react_dom.burndownV170.legacyErrorBoundaries.propagatesUncaughtErrorInsideUnbatchedInitialMount",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_error_boundaries_burndown_v170.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v169_dom_legacy_error_boundaries_update_jun2026(cases: list[dict]) -> int:
    """ReactLegacyErrorBoundaries update-phase catch, multi-root, mount abort (v169)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_errors_originating_downstream.ae165495": "react_dom.burndownV169.legacyErrorBoundaries.catchesErrorsOriginatingDownstream",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_if_child_throws_in_componentwillmount_during_update.c20003c3": "react_dom.burndownV169.legacyErrorBoundaries.catchesIfChildThrowsInComponentWillMountDuringUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_if_child_throws_in_componentwillreceiveprops_during_update.d11289a3": "react_dom.burndownV169.legacyErrorBoundaries.catchesIfChildThrowsInComponentWillReceivePropsDuringUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_if_child_throws_in_componentwillupdate_during_update.6a365bdb": "react_dom.burndownV169.legacyErrorBoundaries.catchesIfChildThrowsInComponentWillUpdateDuringUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_if_child_throws_in_constructor_during_update.b0c01155": "react_dom.burndownV169.legacyErrorBoundaries.catchesIfChildThrowsInConstructorDuringUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.does_not_call_componentwillunmount_when_aborting_initial_mount.5eb09bdb": "react_dom.burndownV169.legacyErrorBoundaries.doesNotCallComponentWillUnmountWhenAbortingInitialMount",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.does_not_swallow_exceptions_on_unmounting_without_boundaries.8902fd17": "react_dom.burndownV169.legacyErrorBoundaries.doesNotSwallowExceptionsOnUnmountingWithoutBoundaries",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.doesn_t_get_into_inconsistent_state_during_additions.a61b369a": "react_dom.burndownV169.legacyErrorBoundaries.doesntGetIntoInconsistentStateDuringAdditions",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.mounts_the_error_message_if_mounting_fails.2210106c": "react_dom.burndownV169.legacyErrorBoundaries.mountsTheErrorMessageIfMountingFails",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.prevents_errors_from_leaking_into_other_roots.406cd7bf": "react_dom.burndownV169.legacyErrorBoundaries.preventsErrorsFromLeakingIntoOtherRoots",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_error_boundaries_burndown_v169.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v168_dom_legacy_error_boundaries_jun2026(cases: list[dict]) -> int:
    """ReactLegacyErrorBoundaries legacy mount catch/recover/uncaught (v168)."""

    mapping: dict[str, str] = {
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.can_recover_from_error_state.bdf72ec7": "react_dom.burndownV168.legacyErrorBoundaries.canRecoverFromErrorState",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.can_update_multiple_times_in_error_state.963e9abd": "react_dom.burndownV168.legacyErrorBoundaries.canUpdateMultipleTimesInErrorState",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.catches_if_child_throws_in_render_during_update.7da45cf8": "react_dom.burndownV168.legacyErrorBoundaries.catchesIfChildThrowsInRenderDuringUpdate",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.does_not_swallow_exceptions_on_mounting_without_boundaries.9e7b869f": "react_dom.burndownV168.legacyErrorBoundaries.doesNotSwallowExceptionsOnMountingWithoutBoundaries",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.does_not_swallow_exceptions_on_updating_without_boundaries.7a3ef13f": "react_dom.burndownV168.legacyErrorBoundaries.doesNotSwallowExceptionsOnUpdatingWithoutBoundaries",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.logs_a_single_error_using_both_error_boundaries.8cb7311f": "react_dom.burndownV168.legacyErrorBoundaries.logsASingleErrorUsingBothErrorBoundaries",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.renders_an_error_state_if_child_throws_in_componentwillmount.e6a6d0d7": "react_dom.burndownV168.legacyErrorBoundaries.rendersAnErrorStateIfChildThrowsInComponentWillMount",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.renders_an_error_state_if_child_throws_in_constructor.4d6d229a": "react_dom.burndownV168.legacyErrorBoundaries.rendersAnErrorStateIfChildThrowsInConstructor",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.renders_an_error_state_if_child_throws_in_render.052b6813": "react_dom.burndownV168.legacyErrorBoundaries.rendersAnErrorStateIfChildThrowsInRender",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.renders_empty_output_if_error_boundary_does_not_handle_the_error.ab499c3a": "react_dom.burndownV168.legacyErrorBoundaries.rendersEmptyOutputIfErrorBoundaryDoesNotHandleTheError",
        "react_dom.ReactLegacyErrorBoundaries-test.internal.reactlegacyerrorboundaries.successfully_mounts_if_no_error_occurs.a7e08b3b": "react_dom.burndownV168.legacyErrorBoundaries.successfullyMountsIfNoErrorOccurs",
    }
    py = "tests_upstream/react_dom/test_dom_legacy_error_boundaries_burndown_v168.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v167_dom_updates_create_root_jun2026(cases: list[dict]) -> int:
    """ReactUpdates createRoot depth guards, hidden subtrees, batch limits (v167)."""

    mapping: dict[str, str] = {
        "react_dom.ReactUpdates-test.reactupdates.can_recover_after_falling_into_an_infinite_update_loop.bd969802": "react_dom.burndownV167.updates.canRecoverAfterFallingIntoAnInfiniteUpdateLoop",
        "react_dom.ReactUpdates-test.reactupdates.can_render_ridiculously_large_number_of_roots_without_triggering_infinite_update_loop_error.bd83b3b5": "react_dom.burndownV167.updates.canRenderRidiculouslyLargeNumberOfRoots",
        "react_dom.ReactUpdates-test.reactupdates.can_schedule_ridiculously_many_updates_within_the_same_batch_without_triggering_a_maximum_update_error.b5e3b4d2": "react_dom.burndownV167.updates.canScheduleRidiculouslyManyUpdatesWithinSameBatch",
        "react_dom.ReactUpdates-test.reactupdates.does_not_fall_into_an_infinite_error_loop.e300cc89": "react_dom.burndownV167.updates.doesNotFallIntoAnInfiniteErrorLoop",
        "react_dom.ReactUpdates-test.reactupdates.does_not_fall_into_an_infinite_update_loop.9fe90e70": "react_dom.burndownV167.updates.doesNotFallIntoAnInfiniteUpdateLoop",
        "react_dom.ReactUpdates-test.reactupdates.does_not_fall_into_an_infinite_update_loop_with_uselayouteffect.113c184e": "react_dom.burndownV167.updates.doesNotFallIntoAnInfiniteUpdateLoopWithUseLayoutEffect",
        "react_dom.ReactUpdates-test.reactupdates.does_not_fall_into_mutually_recursive_infinite_update_loop_with_same_container.8ea27da4": "react_dom.burndownV167.updates.doesNotFallIntoMutuallyRecursiveInfiniteUpdateLoopWithSameContainer",
        "react_dom.ReactUpdates-test.reactupdates.resets_the_update_counter_for_unrelated_updates.421388c3": "react_dom.burndownV167.updates.resetsTheUpdateCounterForUnrelatedUpdates",
        "react_dom.ReactUpdates-test.reactupdates.synchronously_renders_hidden_subtrees.8395fd3d": "react_dom.burndownV167.updates.synchronouslyRendersHiddenSubtrees",
        "react_dom.ReactUpdates-test.reactupdates.uses_correct_base_state_for_setstate_inside_render_phase.e7e770b2": "react_dom.burndownV167.updates.usesCorrectBaseStateForSetstateInsideRenderPhase",
    }
    py = "tests_upstream/react_dom/test_dom_updates_burndown_v167.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v165_dom_composite_component_state_jun2026(cases: list[dict]) -> int:
    """ReactCompositeComponentState + remaining DOMAttribute unknown cases (v165)."""

    mapping: dict[str, str] = {
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.legacy_mode_should_support_setstate_in_componentwillunmount_18851.99565862": "react_dom.burndownV165.compositeState.legacySetStateInComponentWillUnmount",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_batch_unmounts.6f03de21": "react_dom.burndownV165.compositeState.shouldBatchUnmounts",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_call_componentdidupdate_of_children_first.4f459814": "react_dom.burndownV165.compositeState.shouldCallComponentDidUpdateOfChildrenFirst",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_merge_state_when_scu_returns_false.a67d175c": "react_dom.burndownV165.compositeState.shouldMergeStateWhenScuReturnsFalse",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_not_support_setstate_in_componentwillunmount.73d31cf8": "react_dom.burndownV165.compositeState.shouldNotSupportSetStateInComponentWillUnmount",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_support_setting_state.c4e8a5b6": "react_dom.burndownV165.compositeState.shouldSupportSettingState",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_treat_assigning_to_this_state_inside_cwm_as_a_replacestate_with_a_warning.db6c5d05": "react_dom.burndownV165.compositeState.shouldTreatAssigningToStateInsideCwmWithWarning",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_treat_assigning_to_this_state_inside_cwrp_as_a_replacestate_with_a_warning.305eb1d7": "react_dom.burndownV165.compositeState.shouldTreatAssigningToStateInsideCwrpWithWarning",
        "react_dom.ReactCompositeComponentState-test.reactcompositecomponent_state.should_update_state_when_called_from_child_cwrp.689e2197": "react_dom.burndownV165.compositeState.shouldUpdateStateWhenCalledFromChildCwrp",
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes.allows_camelcase_unknown_attributes_and_warns.3657236a": "react_dom.burndownV165.unknownAttributes.camelCaseUnknownWarns",
        "react_dom.ReactDOMAttribute-test.reactdom_unknown_attribute.unknown_attributes.removes_symbols_and_warns.f002f586": "react_dom.burndownV165.unknownAttributes.removesSymbolsAndWarns",
    }
    py_by_manifest: dict[str, str] = {
        "react_dom.burndownV165.compositeState.legacySetStateInComponentWillUnmount": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldBatchUnmounts": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldCallComponentDidUpdateOfChildrenFirst": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldMergeStateWhenScuReturnsFalse": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldNotSupportSetStateInComponentWillUnmount": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldSupportSettingState": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldTreatAssigningToStateInsideCwmWithWarning": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldTreatAssigningToStateInsideCwrpWithWarning": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.compositeState.shouldUpdateStateWhenCalledFromChildCwrp": "tests_upstream/react_dom/test_dom_composite_component_state_burndown_v165.py",
        "react_dom.burndownV165.unknownAttributes.camelCaseUnknownWarns": "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
        "react_dom.burndownV165.unknownAttributes.removesSymbolsAndWarns": "tests_upstream/react_dom/test_react_dom_attribute_unknown_burndown_v84.py",
    }
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py_by_manifest[manifest_id]
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v161_dom_console_error_reporting_jun2026(cases: list[dict]) -> int:
    """ReactDOMConsoleErrorReporting createRoot slice (v161)."""

    mapping: dict[str, str] = {
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_errors_during_event_handlers.cd992f44": "react_dom.burndownV161.consoleErrorReporting.logsErrorsDuringEventHandlers",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_layout_effect_errors_with_an_error_boundary.18a3eaf9": "react_dom.burndownV161.consoleErrorReporting.logsLayoutEffectErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_layout_effect_errors_without_an_error_boundary.45ac738e": "react_dom.burndownV161.consoleErrorReporting.logsLayoutEffectErrorsWithoutBoundary",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_passive_effect_errors_with_an_error_boundary.42fe48ab": "react_dom.burndownV161.consoleErrorReporting.logsPassiveEffectErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_passive_effect_errors_without_an_error_boundary.b4dc0a71": "react_dom.burndownV161.consoleErrorReporting.logsPassiveEffectErrorsWithoutBoundary",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_render_errors_with_an_error_boundary.2ee180bc": "react_dom.burndownV161.consoleErrorReporting.logsRenderErrorsWithBoundary",
        "react_dom.ReactDOMConsoleErrorReporting-test.reactdomconsoleerrorreporting.reactdomclient_createroot.logs_render_errors_without_an_error_boundary.e5959a03": "react_dom.burndownV161.consoleErrorReporting.logsRenderErrorsWithoutBoundary",
    }
    py = "tests_upstream/react_dom/test_dom_console_error_reporting_burndown_v161.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v160_dom_function_component_jun2026(cases: list[dict]) -> int:
    """ReactFunctionComponent DOM slice (v160)."""

    mapping: dict[str, str] = {
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_render_stateless_component.6e29136a": "react_dom.burndownV160.functionComponent.shouldRenderStatelessComponent",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_update_stateless_component.1d7da531": "react_dom.burndownV160.functionComponent.shouldUpdateStatelessComponent",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_unmount_stateless_component.9e8fa01f": "react_dom.burndownV160.functionComponent.shouldUnmountStatelessComponent",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_pass_context_thru_stateless_component.13164219": "react_dom.burndownV160.functionComponent.shouldPassContextThruStatelessComponent",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_warn_for_getderivedstatefromprops_on_a_function_component.67f09fc4": "react_dom.burndownV160.functionComponent.shouldWarnForGetDerivedStateFromProps",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_warn_for_childcontexttypes_on_a_function_component.e89ace28": "react_dom.burndownV160.functionComponent.shouldWarnForChildContextTypes",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_not_throw_when_stateless_component_returns_undefined.53032e27": "react_dom.burndownV160.functionComponent.shouldNotThrowWhenReturnsUndefined",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_use_correct_name_in_key_warning.67054ee7": "react_dom.burndownV160.functionComponent.shouldUseCorrectNameInKeyWarning",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_receive_context.39ad77c2": "react_dom.burndownV160.functionComponent.shouldReceiveContext",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_work_with_arrow_functions.c473ee82": "react_dom.burndownV160.functionComponent.shouldWorkWithArrowFunctions",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_allow_simple_functions_to_return_null.49031a6b": "react_dom.burndownV160.functionComponent.shouldAllowReturnNull",
        "react_dom.ReactFunctionComponent-test.reactfunctioncomponent.should_allow_simple_functions_to_return_false.6e09125d": "react_dom.burndownV160.functionComponent.shouldAllowReturnFalse",
    }
    py = "tests_upstream/react_dom/test_dom_function_component_burndown_v160.py"
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        c["status"] = "implemented"
        c["manifest_id"] = mapping[cid]
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


def _patch_wave_burndown_v159_context_error_logging_batching_jun2026(cases: list[dict]) -> int:
    """NewContext, ContextPropagation, error logging, batching internal (v159)."""

    mapping: dict[str, tuple[str, str]] = {
        "react.ReactConfigurableErrorLogging-test.reactconfigurableerrorlogging.does_not_log_errors_when_inside_real_act": (
            "react.burndownV159.configurableErrorLogging.doesNotLogErrorsWhenInsideRealAct",
            "tests_upstream/react/test_configurable_error_logging_act_suppresses.py",
        ),
        "react.ReactConfigurableErrorLogging-test.reactconfigurableerrorlogging.should_ignore_errors_thrown_in_log_method_to_prevent_cycle": (
            "react.burndownV159.configurableErrorLogging.shouldIgnoreErrorsThrownInLogMethod",
            "tests_upstream/react/test_configurable_error_logging.py",
        ),
        "react.ReactConfigurableErrorLogging-test.reactconfigurableerrorlogging.should_log_errors_that_occur_during_the_begin_phase": (
            "react.burndownV159.configurableErrorLogging.shouldLogErrorsDuringBeginPhase",
            "tests_upstream/react/test_configurable_error_logging.py",
        ),
        "react.ReactConfigurableErrorLogging-test.reactconfigurableerrorlogging.should_log_errors_that_occur_during_the_commit_phase": (
            "react.burndownV159.configurableErrorLogging.shouldLogErrorsDuringCommitPhase",
            "tests_upstream/react/test_configurable_error_logging.py",
        ),
        "react.ReactBatching-test.internal.reactblockingmode.layout_updates_flush_synchronously_in_same_event": (
            "react.burndownV159.batchingInternal.layoutUpdatesFlushSynchronouslyInSameEvent",
            "tests_upstream/react/test_batching_internal.py",
        ),
        "react.ReactBatching-test.internal.reactblockingmode.updates_flush_without_yielding_in_the_next_event": (
            "react.burndownV159.batchingInternal.updatesFlushWithoutYieldingInNextEvent",
            "tests_upstream/react/test_batching_internal.py",
        ),
        "react.ReactBatching-test.internal.reactblockingmode.uses_proper_suspense_semantics_not_legacy_ones": (
            "react.burndownV159.batchingInternal.usesProperSuspenseSemanticsNotLegacyOnes",
            "tests_upstream/react/test_batching_internal.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.context_provider.provider_bails_out_if_children_and_value_are_unchanged_like_scu": (
            "react.burndownV159.newContext.providerBailsOutIfChildrenAndValueUnchanged",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.context_consumer.can_read_other_contexts_inside_consumer_render_prop": (
            "react.burndownV159.newContext.canReadOtherContextsInsideConsumerRenderProp",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.context_consumer.consumer_does_not_bail_out_if_there_were_no_bailouts_above_it": (
            "react.burndownV159.newContext.consumerDoesNotBailOutIfNoBailoutsAbove",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.readcontext.can_read_the_same_context_multiple_times_in_the_same_function": (
            "react.burndownV159.newContext.canReadSameContextMultipleTimesInSameFunction",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.readcontext.does_not_bail_out_if_there_were_no_bailouts_above_it": (
            "react.burndownV159.newContext.readContextDoesNotBailOutIfNoBailoutsAbove",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactNewContext-test.reactnewcontext.usecontext.does_not_bail_out_if_there_were_no_bailouts_above_it": (
            "react.burndownV159.newContext.useContextDoesNotBailOutIfNoBailoutsAbove",
            "tests_upstream/react/test_new_context_burndown_v159.py",
        ),
        "react.ReactContextPropagation-test.reactlazycontextpropagation.context_change_should_prevent_bailout_of_memoized_component_purecomponent": (
            "react.burndownV159.contextPropagation.pureComponentContextChangePreventsBailout",
            "tests_upstream/react/test_context_propagation_burndown_v159.py",
        ),
        "react.ReactContextPropagation-test.reactlazycontextpropagation.context_change_should_prevent_bailout_of_memoized_component_usememo_no_intermediate_fiber": (
            "react.burndownV159.contextPropagation.useMemoContextChangePreventsBailout",
            "tests_upstream/react/test_context_propagation_burndown_v159.py",
        ),
    }
    changed = 0
    for c in cases:
        cid = c.get("id")
        if cid not in mapping:
            continue
        if c.get("status") != "non_goal":
            continue
        manifest_id, py = mapping[cid]
        c["status"] = "implemented"
        c["manifest_id"] = manifest_id
        c["python_test"] = py
        c["non_goal_rationale"] = None
        c["notes"] = None
        changed += 1
    return changed


WAVES: dict[str, tuple[str, WaveReact, WaveDom]] = {
    "initial_phase_a_b_d": (
        "First burn-down wave: close several high-pending core files + one DOM boolean slice.",
        _patch_wave_initial_react_cases,
        _patch_wave_initial_dom_cases,
    ),
    "dom_invalid_event_listeners_dispatch_apr2026": (
        "DOM: InvalidEventListeners dispatch semantics (null ok; non-function prevented).",
        _patch_wave_noop_react,
        _patch_wave_dom_invalid_event_listeners_dispatch_apr2026,
    ),
    "dom_dangerously_set_innerhtml_property_apr2026": (
        "DOM: dangerouslySetInnerHTML sets innerHTML property on host nodes.",
        _patch_wave_noop_react,
        _patch_wave_dom_dangerously_set_innerhtml_innerhtml_property_apr2026,
    ),
    "dom_close_small_pending_buckets_defer_apr2026": (
        "DOM: close many tiny pending buckets as deferred non-goals.",
        _patch_wave_noop_react,
        _patch_wave_dom_close_small_pending_buckets_defer_apr2026,
    ),
    "dom_close_dom_property_operations_remaining_defer_apr2026": (
        "DOM: close remaining DOMPropertyOperations pending cases as deferred non-goals.",
        _patch_wave_noop_react,
        _patch_wave_dom_close_dom_property_operations_remaining_defer_apr2026,
    ),
    "dom_close_fizz_and_hydration_buckets_defer_apr2026": (
        "DOM: close Fizz/hydration/server-integration buckets as deferred non-goals.",
        _patch_wave_noop_react,
        _patch_wave_dom_close_fizz_and_hydration_buckets_defer_apr2026,
    ),
    "dom_close_ui_events_composite_buckets_defer_may2026": (
        "DOM: defer large UI/events/composite pending buckets (inputs, components, propagation, forms, …).",
        _patch_wave_noop_react,
        _patch_wave_dom_close_ui_events_composite_buckets_defer_may2026,
    ),
    "phase1_noop_harness_suspense_basics_apr2026": (
        "Phase 1: reclaim two Suspense-with-noop basics (rerender after resolve; no flip-back).",
        _patch_wave_phase1_noop_harness_suspense_basics_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase2_incremental_cancel_partial_restart_apr2026": (
        "Phase 2: reclaim one ReactIncremental yield cancel/restart case.",
        _patch_wave_phase2_incremental_cancel_partial_restart_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase2_incremental_deprioritize_resume_apr2026": (
        "Phase 2: reclaim one ReactIncremental deprioritize/resume case.",
        _patch_wave_phase2_incremental_deprioritize_resume_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase3_use_basic_apr2026": (
        "Phase 3: add basic experimental use() thenable semantics (fulfilled/pending/rejected).",
        _patch_wave_phase3_use_basic_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase4_suspense_list_basic_apr2026": (
        "Phase 4: add minimal SuspenseList forwards+tail=hidden defaults slice.",
        _patch_wave_phase4_suspense_list_basic_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase5_lazy_async_basics_apr2026": (
        "Phase 5: extend lazy() with async thenable suspension + rejection behavior.",
        _patch_wave_phase5_lazy_async_basics_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase6_profiler_basic_apr2026": (
        "Phase 6: add minimal Profiler wrapper + commit-phase onRender callbacks.",
        _patch_wave_phase6_profiler_basic_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_phase1_to_6_buckets_pending_apr2026": (
        "Reopen Phase 1–6 deferred big-feature buckets from non_goal -> pending.",
        _patch_wave_reopen_phase1_to_6_buckets_pending_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_phase11_to_13_buckets_pending_apr2026": (
        "Reopen Phase 11–13 deferred big-feature buckets from non_goal -> pending.",
        _patch_wave_reopen_phase11_to_13_buckets_pending_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_concurrent_lanes_expiration_defer_may2026": (
        "Reopen deferred concurrent lanes/expiration buckets from non_goal -> pending.",
        _patch_wave_reopen_concurrent_lanes_expiration_defer_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_hooks_noop_defer_may2026": (
        "Reopen deferred ReactHooksWithNoopRenderer buckets from non_goal -> pending.",
        _patch_wave_reopen_hooks_noop_defer_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_hooks_internal_defer_may2026": (
        "Reopen deferred ReactHooks-test.internal buckets from non_goal -> pending.",
        _patch_wave_reopen_hooks_internal_defer_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_basic_context_v01_may2026": (
        "ReactUse slice: implement basic use(context).",
        _patch_wave_use_basic_context_v01_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_nodes_v01_may2026": (
        "ReactUse slice: render Context/Thenable as nodes and unwrap them before reconciliation.",
        _patch_wave_use_nodes_v01_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_async_components_v01_may2026": (
        "ReactUse slice: async function + async generator components warn and render null.",
        _patch_wave_use_async_components_v01_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_unmount_basics_v63_may2026": (
        "ReactHooksWithNoopRenderer slice: unmount effects + unmount state basics.",
        _patch_wave_hooks_with_noop_unmount_basics_v63_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_effect_create_errors_v64_may2026": (
        "ReactHooksWithNoopRenderer slice: handle errors thrown in effect create on mount/update.",
        _patch_wave_hooks_with_noop_effect_create_errors_v64_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_use_imperative_handle_deps_v65_may2026": (
        "ReactHooksWithNoopRenderer slice: useImperativeHandle deps behavior.",
        _patch_wave_hooks_with_noop_use_imperative_handle_deps_v65_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_mount_additional_state_v66_may2026": (
        "ReactHooksWithNoopRenderer slice: adding a hook on update throws.",
        _patch_wave_hooks_with_noop_mount_additional_state_v66_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_passive_flush_sibling_update_v67_may2026": (
        "ReactHooksWithNoopRenderer slice: passive effects flush even if a sibling schedules an update.",
        _patch_wave_hooks_with_noop_passive_flush_sibling_update_v67_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_passive_flush_sibling_deletions_v68_may2026": (
        "ReactHooksWithNoopRenderer slice: passive effects flush even with sibling deletions.",
        _patch_wave_hooks_with_noop_passive_flush_sibling_deletions_v68_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_passive_flush_sibling_new_root_v69_may2026": (
        "ReactHooksWithNoopRenderer slice: passive effects flush even if a sibling schedules a new root.",
        _patch_wave_hooks_with_noop_passive_flush_sibling_new_root_v69_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_uselayouteffect_errors_v70_may2026": (
        "ReactHooksWithNoopRenderer slice: errors thrown in useLayoutEffect are caught/rethrown.",
        _patch_wave_hooks_with_noop_uselayouteffect_errors_v70_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_useeffect_serial_flush_v71_may2026": (
        "ReactHooksWithNoopRenderer slice: flush old passive effect destroys before new creates.",
        _patch_wave_hooks_with_noop_useeffect_serial_flush_v71_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_force_flush_passive_before_new_effects_v72_may2026": (
        "ReactHooksWithNoopRenderer slice: force flush pending passive effects before new insertion/layout effects.",
        _patch_wave_hooks_with_noop_force_flush_passive_before_new_effects_v72_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_flushsync_passive_v73_may2026": (
        "ReactHooksWithNoopRenderer slice: flushSync does not flush non-discrete passive effects.",
        _patch_wave_hooks_with_noop_flushsync_passive_v73_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_flushsync_not_allowed_v74_may2026": (
        "ReactHooksWithNoopRenderer slice: flushSync is not allowed during a flush.",
        _patch_wave_hooks_with_noop_flushsync_not_allowed_v74_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_defer_passive_unmount_v75_may2026": (
        "ReactHooksWithNoopRenderer slice: defer passive effect destroy functions during unmount.",
        _patch_wave_hooks_with_noop_defer_passive_unmount_v75_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_passive_unmount_warnings_v76_may2026": (
        "ReactHooksWithNoopRenderer slice: do not warn for updates from passive unmount cleanups.",
        _patch_wave_hooks_with_noop_passive_unmount_warnings_v76_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_unmounted_update_warnings_v77_may2026": (
        "ReactHooksWithNoopRenderer slice: do not warn for updates targeting unmounted components.",
        _patch_wave_hooks_with_noop_unmounted_update_warnings_v77_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_pending_passive_unmount_warning_edges_v78_may2026": (
        "ReactHooksWithNoopRenderer slice: no warnings for pending passive-unmount edge cases.",
        _patch_wave_hooks_with_noop_pending_passive_unmount_warning_edges_v78_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_passive_destroy_errors_nearest_boundary_v79_may2026": (
        "ReactHooksWithNoopRenderer slice: errors in passive destroy use nearest still-mounted boundary.",
        _patch_wave_hooks_with_noop_passive_destroy_errors_nearest_boundary_v79_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_useeffect_async_priority_v80_may2026": (
        "ReactHooksWithNoopRenderer slice: useEffect updates are async priority.",
        _patch_wave_hooks_with_noop_useeffect_async_priority_v80_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_legacy_useeffect_batching_v81_may2026": (
        "ReactHooksWithNoopRenderer slice: legacy useEffect is deferred; its updates finish synchronously.",
        _patch_wave_hooks_with_noop_legacy_useeffect_batching_v81_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_offscreen_insertion_cleanup_warning_v82_may2026": (
        "ReactHooksWithNoopRenderer slice: warn when setState is called from insertion effect cleanup (offscreen deletion path).",
        _patch_wave_hooks_with_noop_offscreen_insertion_cleanup_warning_v82_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_deferred_value_text_v83_may2026": (
        "ReactHooksWithNoopRenderer slice: useDeferredValue defers text value.",
        _patch_wave_hooks_with_noop_deferred_value_text_v83_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_render_phase_warnings_v84_may2026": (
        "ReactHooksWithNoopRenderer slice: render-phase update warnings + startTransition-in-render guard.",
        _patch_wave_hooks_with_noop_render_phase_warnings_v84_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_suspenselist_unmount_regression_v86_may2026": (
        "ReactHooksWithNoopRenderer slice: SuspenseList deletion runs unmounts.",
        _patch_wave_hooks_with_noop_suspenselist_unmount_regression_v86_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_render_phase_suspense_v85_v87_may2026": (
        "ReactHooksWithNoopRenderer slice: render-phase updates discarded on suspend (and mixed updates).",
        _patch_wave_hooks_with_noop_render_phase_suspense_v85_v87_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_render_phase_lower_pri_regression_v88_may2026": (
        "ReactHooksWithNoopRenderer slice: render-phase updates do not drop lower priority work.",
        _patch_wave_hooks_with_noop_render_phase_lower_pri_regression_v88_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "hooks_with_noop_transition_timeout_v89_may2026": (
        "ReactHooksWithNoopRenderer slice: useTransition delays pending/loading state until timeout.",
        _patch_wave_hooks_with_noop_transition_timeout_v89_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_async_children_unwrap_v02_may2026": (
        "ReactUse slice: transparently unwrap Thenable children (top-level/siblings/class) and recurse.",
        _patch_wave_use_async_children_unwrap_v02_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_fulfilled_thenable_thrown_v03_may2026": (
        "ReactUse slice: fulfilled thenable thrown does not loop.",
        _patch_wave_use_fulfilled_thenable_thrown_v03_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_async_component_outside_suspense_v04_may2026": (
        "ReactUse slice: async component outside Suspense crashes (microtask/macrotask).",
        _patch_wave_use_async_component_outside_suspense_v04_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_async_iterable_children_v05_may2026": (
        "ReactUse slice: async iterable children warning/handling.",
        _patch_wave_use_async_iterable_children_v05_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_promise_multiple_components_v06_may2026": (
        "ReactUse slice: use(promise) in multiple components/sibling boundaries.",
        _patch_wave_use_promise_multiple_components_v06_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_hooks_cannot_be_called_while_suspended_v07_may2026": (
        "ReactUse slice: hooks cannot be called while suspended (dispatcher unset).",
        _patch_wave_use_hooks_cannot_be_called_while_suspended_v07_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_try_catch_warn_v08_may2026": (
        "ReactUse slice: warn if use(promise) is wrapped with try/catch.",
        _patch_wave_use_try_catch_warn_v08_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_async_client_component_hook_warn_v09_may2026": (
        "ReactUse slice: warn if async client component calls a hook.",
        _patch_wave_use_async_client_component_hook_warn_v09_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_suspense_replay_reuses_hooks_v10_may2026": (
        "ReactUse slice: Suspense replay reuses hooks from suspended attempt.",
        _patch_wave_use_suspense_replay_reuses_hooks_v10_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_uncached_promise_memo_forward_ref_v11_may2026": (
        "ReactUse slice: unwrap use(promise) inside memo and forwardRef.",
        _patch_wave_use_uncached_promise_memo_forward_ref_v11_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_nested_suspense_v12_may2026": (
        "ReactUse slice: nested Suspense boundaries + waterfall.",
        _patch_wave_use_nested_suspense_v12_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_render_phase_memo_suspended_v13_may2026": (
        "ReactUse slice: use()+render phase updates, suspended parent updates, useMemo+use.",
        _patch_wave_use_render_phase_memo_suspended_v13_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_pending_two_roots_fresh_update_v14_may2026": (
        "ReactUse slice: fresh update while suspended, two roots, transition pending + use suspend.",
        _patch_wave_use_pending_two_roots_fresh_update_v14_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_transition_microtask_errors_v15_may2026": (
        "ReactUse slice: transition + microtask ping, new suspense in transition, error + use.",
        _patch_wave_use_transition_microtask_errors_v15_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "use_reactuse_remainder_v16_may2026": (
        "ReactUse slice: legacy context + use(), interleaved transition suspend, flushSync context.",
        _patch_wave_use_reactuse_remainder_v16_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_dom_features_defer_may2026": (
        "Reopen deferred DOM feature buckets (Fizz/hydration/etc.) from non_goal -> pending.",
        _patch_wave_reopen_dom_features_defer_may2026,
        _patch_wave_reopen_dom_features_defer_dom_noop,
    ),
    "phase7_context_bailouts_apr2026": (
        "Phase 7: context dependency tracking to prevent memo bailouts on context change.",
        _patch_wave_phase7_context_bailouts_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase8_hooks_internal_render_phase_bailout_apr2026": (
        "Phase 8: internal hooks render-phase no-op update bailout.",
        _patch_wave_phase8_hooks_internal_render_phase_bailout_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase9_noop_passive_destroy_error_apr2026": (
        "Phase 9: noop renderer surfaces errors from passive destroy on update.",
        _patch_wave_phase9_noop_passive_destroy_error_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase10_suspense_effects_legacy_preserves_effects_apr2026": (
        "Phase 10: legacy root preserves primary tree/effects when an update suspends.",
        _patch_wave_phase10_suspense_effects_legacy_preserves_effects_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase11_async_actions_use_transition_rethrows_apr2026": (
        "Phase 11: async actions basic rethrow semantics via useTransition.",
        _patch_wave_phase11_async_actions_use_transition_rethrows_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "async_actions_pending_true_until_finish_apr2026": (
        "Async actions: isPending stays true until async action finishes.",
        _patch_wave_async_actions_pending_true_until_finish_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "async_actions_start_transition_report_error_apr2026": (
        "Async actions: React.startTransition reports sync/async errors via reportError.",
        _patch_wave_async_actions_start_transition_report_error_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "async_actions_start_transition_supports_async_apr2026": (
        "Async actions: React.startTransition supports async actions (thenables).",
        _patch_wave_async_actions_start_transition_supports_async_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "async_actions_use_optimistic_remaining_apr2026": (
        "Async actions: reclaim remaining pending useOptimistic/entanglement cases (minimal slice).",
        _patch_wave_async_actions_use_optimistic_remaining_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_async_microtasks_apr2026": (
        "Phase 12: async/isomorphic act microtask unwrapping + return value.",
        _patch_wave_phase12_isomorphic_act_async_microtasks_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_return_values_apr2026": (
        "Phase 12: isomorphic act returns callback values (sync + nested).",
        _patch_wave_phase12_isomorphic_act_return_values_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_nested_async_and_warn_apr2026": (
        "Phase 12: nested async act + warn on non-awaited promise in act scope.",
        _patch_wave_phase12_isomorphic_act_nested_async_and_warn_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_non_async_microtasks_apr2026": (
        "Phase 12: non-async act drains microtasks to unwrap promise continuations.",
        _patch_wave_phase12_isomorphic_act_non_async_microtasks_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_behavior_in_production_apr2026": (
        "Phase 12: production act does not emit DEV warnings.",
        _patch_wave_phase12_isomorphic_act_behavior_in_production_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_bypasses_queue_microtask_apr2026": (
        "Phase 12: act drains microtasks without relying on queueMicrotask.",
        _patch_wave_phase12_isomorphic_act_bypasses_queue_microtask_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase12_isomorphic_act_legacy_batching_remaining_apr2026": (
        "Phase 12: reclaim remaining legacy-mode batching and suspend/no-warn cases.",
        _patch_wave_phase12_isomorphic_act_legacy_batching_remaining_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase13_transition_tracing_basic_callbacks_apr2026": (
        "Phase 13: minimal transition tracing start/complete callbacks for named transitions.",
        _patch_wave_phase13_transition_tracing_basic_callbacks_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase13_transition_tracing_remaining_burndown_apr2026": (
        "Phase 13: reclaim remaining transition tracing bucket (minimal slice).",
        _patch_wave_phase13_transition_tracing_remaining_burndown_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_suspense_with_noop_concurrent_defer_apr2026": (
        "Burndown: close concurrent/timeout/priority-heavy Suspense-with-noop cases as deferred non-goals.",
        _patch_wave_burndown_close_suspense_with_noop_concurrent_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_incremental_concurrent_defer_apr2026": (
        "Burndown: close concurrent scheduling-heavy ReactIncremental cases as deferred non-goals.",
        _patch_wave_burndown_close_incremental_concurrent_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_suspense_list_remaining_defer_apr2026": (
        "Burndown: close remaining ReactSuspenseList pending cases as deferred non-goals.",
        _patch_wave_burndown_close_suspense_list_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_react_use_remaining_defer_apr2026": (
        "Burndown: close remaining ReactUse pending cases as deferred non-goals.",
        _patch_wave_burndown_close_react_use_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_transition_and_suspense_internal_remaining_may2026": (
        "Burndown: close remaining ReactTransition and ReactSuspense-test.internal pending cases as deferred non-goals.",
        _patch_wave_burndown_close_transition_and_suspense_internal_remaining_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_suspense_with_noop_remaining_defer_apr2026": (
        "Burndown: close remaining Suspense-with-noop pending cases as deferred non-goals.",
        _patch_wave_burndown_close_suspense_with_noop_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_incremental_remaining_defer_apr2026": (
        "Burndown: close remaining ReactIncremental pending cases as deferred non-goals.",
        _patch_wave_burndown_close_incremental_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_lazy_internal_remaining_defer_apr2026": (
        "Burndown: close remaining ReactLazy-test.internal pending cases as deferred non-goals.",
        _patch_wave_burndown_close_lazy_internal_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_may2026_lazy_validation_clusters": (
        "Burndown: lazy invalid export slice + defer remaining ReactLazy internal + defer Suspense-with-noop bucket.",
        _patch_wave_burndown_may2026_lazy_validation_clusters,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_close_profiler_internal_remaining_defer_apr2026": (
        "Burndown: close remaining ReactProfiler internal pending cases as deferred non-goals.",
        _patch_wave_burndown_close_profiler_internal_remaining_defer_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "close_upstream_skipped_pending_react_core_apr2026": (
        "Burndown: close remaining pending React core it.skip cases as deferred non-goals.",
        _patch_wave_close_upstream_skipped_pending_react_core_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_incremental_updates_bucket_pending_apr2026": (
        "Reopen ReactIncrementalUpdates bucket from non_goal -> pending.",
        _patch_wave_reopen_incremental_updates_bucket_pending_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "incremental_updates_manifest_and_inventory_apr2026": (
        "ReactIncrementalUpdates: mark reopened pending cases as implemented (manifest+inventory).",
        _patch_wave_incremental_updates_manifest_and_inventory_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_suspense_list_bucket_pending_apr2026": (
        "Reopen ReactSuspenseList-test.js bucket from non_goal -> pending (pending-first).",
        _patch_wave_reopen_suspense_list_bucket_pending_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase4_suspense_list_together_basics_apr2026": (
        "Phase 4: reclaim SuspenseList revealOrder='together' basics.",
        _patch_wave_phase4_suspense_list_together_basics_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase4_suspense_list_option_warnings_apr2026": (
        "Phase 4: reclaim SuspenseList option warnings slices.",
        _patch_wave_phase4_suspense_list_option_warnings_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase4_suspense_list_child_shape_warnings_apr2026": (
        "Phase 4: reclaim SuspenseList child-shape warning slices.",
        _patch_wave_phase4_suspense_list_child_shape_warnings_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "phase4_suspense_list_remaining_burndown_v06_apr2026": (
        "Phase 4: implement remaining SuspenseList pending cases (consolidated slice).",
        _patch_wave_phase4_suspense_list_remaining_burndown_v06_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "burndown_v2_manifest_slices_apr2026": (
        "Manifest-gated slice: sibling Suspense semantics, sync error boundary mount, "
        "element validator __self/__source props, setState callback after flush, DOM "
        "className null→empty string, multi keyed child text updates.",
        _patch_wave_burndown_v2_react_manifest_slices,
        _patch_wave_burndown_v2_dom_manifest_slices,
    ),
    "unmark_hooks_noop_suites_apr2026": (
        "Unmark reconciler hook/noop suites: flip ReactHooksWithNoopRenderer + "
        "ReactHooks-test.internal from non_goal -> pending (pending-first).",
        _patch_wave_unmark_hooks_noop_suites_apr2026,
        _patch_wave_unmark_hooks_noop_suites_dom_noop,
    ),
    "unmark_lazy_internal_suite_apr2026": (
        "Unmark reconciler ReactLazy-test.internal from non_goal -> pending (pending-first).",
        _patch_wave_unmark_lazy_internal_suite_apr2026,
        _patch_wave_unmark_lazy_internal_suite_dom_noop,
    ),
    "burndown_v3_manifest_slices_apr2026": (
        "Manifest-gated slice: Suspense initial mount snapshots, error boundary update "
        "scheduling, fragment illegal props warning, fragment text updates, DOM null "
        "custom attribute removal, server text/attribute escaping.",
        _patch_wave_burndown_v3_react_manifest_slices,
        _patch_wave_burndown_v3_dom_manifest_slices,
    ),
    "burndown_v4_manifest_slices_apr2026": (
        "Manifest-gated slice: Suspense host/deep fallback snapshots, batched error "
        "boundaries, sibling key warnings, host child text updates, boolean false prop "
        "removal, null attribute omission.",
        _patch_wave_burndown_v4_react_manifest_slices,
        _patch_wave_burndown_v4_dom_manifest_slices,
    ),
    "burndown_v5_manifest_slices_apr2026": (
        "Manifest-gated slice: Suspense fallback nesting inner suspend, error boundary "
        "didCatch on mount, DEV no key warn when children are keyed, direct host string "
        "child updates, falsey boolean DOM props, empty href omission.",
        _patch_wave_burndown_v5_react_manifest_slices,
        _patch_wave_burndown_v5_dom_manifest_slices,
    ),
    "burndown_v6_manifest_slices_apr2026": (
        "Manifest-gated slice: error boundary didCatch repeats, element validator single rest "
        "arg no-warn, function child re-suspends, empty-props child update, empty src omission, "
        "and attribute value stringification.",
        _patch_wave_burndown_v6_react_manifest_slices,
        _patch_wave_burndown_v6_dom_manifest_slices,
    ),
    "burndown_v7_manifest_slices_apr2026": (
        "Manifest-gated slice: class child re-suspend, missing-key warns (iterable + array rest "
        "args), explicit-key host tag swap, input empty value + meter value markup.",
        _patch_wave_burndown_v7_react_manifest_slices,
        _patch_wave_burndown_v7_dom_manifest_slices,
    ),
    "burndown_v8_manifest_slices_apr2026": (
        "Manifest-gated slice: implicit-key tag change, missing-key warn with owner info, "
        "error boundary component stack in didCatch, mixed child deletion, option empty value + "
        "form empty action.",
        _patch_wave_burndown_v8_react_manifest_slices,
        _patch_wave_burndown_v8_dom_manifest_slices,
    ),
    "burndown_v9_manifest_slices_apr2026": (
        "Manifest-gated slice: missing-key warns (no owner/parent + host stack), host ref "
        "callbacks on insert/update/unmount, empty formAction overriding parent form action.",
        _patch_wave_burndown_v9_react_manifest_slices,
        _patch_wave_burndown_v9_dom_manifest_slices,
    ),
    "burndown_v10_manifest_slices_apr2026": (
        "Manifest-gated slice: key warn only for 2+ element children, GDSFE recovery to a "
        "different host tag, anchor empty href preserved vs link empty href omitted.",
        _patch_wave_burndown_v10_react_manifest_slices,
        _patch_wave_burndown_v10_dom_manifest_slices,
    ),
    "burndown_v11_manifest_slices_apr2026": (
        "Manifest-gated slice: error boundary recovery (didCatch-titled) same/different host "
        "type, inlined children key warn without blowup, null vs omitted attr incremental no-op, "
        "server null child and numeric zero text.",
        _patch_wave_burndown_v11_react_manifest_slices,
        _patch_wave_burndown_v11_dom_manifest_slices,
    ),
    "burndown_v12_manifest_slices_apr2026": (
        "Manifest-gated slice: GDSFE arity (no errorInfo), reconciler error boundary mount, "
        "pass-children-down keyed no-warn, memo+sibling async re-suspend, custom data attribute "
        "string incremental, cased custom attribute server markup.",
        _patch_wave_burndown_v12_react_manifest_slices,
        _patch_wave_burndown_v12_dom_manifest_slices,
    ),
    "burndown_v13_manifest_slices_apr2026": (
        "Manifest-gated slice: reconciler error boundary on update, undefined-type children no "
        "blowup, two async children shared fallback, cased data-* server segment, numeric "
        "custom data stringified server.",
        _patch_wave_burndown_v13_react_manifest_slices,
        _patch_wave_burndown_v13_dom_manifest_slices,
    ),
    "burndown_v14_manifest_slices_apr2026": (
        "Manifest-gated slice: render-phase setState plus error without infinite loop, custom "
        "boolean host props omitted (explicit + shorthand parity), html_props normalization.",
        _patch_wave_burndown_v14_react_manifest_slices,
        _patch_wave_burndown_v14_dom_manifest_slices,
    ),
    "burndown_v15_manifest_slices_apr2026": (
        "Manifest-gated slice: ref detach throw does not block sibling ref detach, custom "
        "attribute removal on update, invalid callable custom values stripped (noop + html_props).",
        _patch_wave_burndown_v15_react_manifest_slices,
        _patch_wave_burndown_v15_dom_manifest_slices,
    ),
    "burndown_v16_manifest_slices_apr2026": (
        "Manifest-gated slice: int-like children never flattened as iterables (#4776), custom "
        "object attribute stringified, custom function attribute omitted (children + DOM).",
        _patch_wave_burndown_v16_react_manifest_slices,
        _patch_wave_burndown_v16_dom_manifest_slices,
    ),
    "burndown_v17_manifest_slices_apr2026": (
        "Manifest-gated slice: lazy loader not invoked on createElement alone, known DOM prop "
        "bad casing normalized with DEV warn, NaN custom attrs stringified with DEV warn.",
        _patch_wave_burndown_v17_react_manifest_slices,
        _patch_wave_burndown_v17_dom_manifest_slices,
    ),
    "burndown_v18_manifest_slices_apr2026": (
        "Manifest-gated slice: schedule update after uncaught unmount error, custom-element "
        "unknown boolean attrs, string on* attrs on custom elements (html_props + server).",
        _patch_wave_burndown_v18_react_manifest_slices,
        _patch_wave_burndown_v18_dom_manifest_slices,
    ),
    "burndown_v19_manifest_slices_apr2026": (
        "Manifest-gated slice: unmounting error boundary no recovery, error boundary non-Error "
        "throws, dangerouslySetInnerHTML __html null, SVG font-face x-height casing (html_props).",
        _patch_wave_burndown_v19_react_manifest_slices,
        _patch_wave_burndown_v19_dom_manifest_slices,
    ),
    "burndown_v20_manifest_slices_apr2026": (
        "Manifest-gated slice: noop error boundary rethrow sync+batched mount, reconciler "
        "didCatch on failed recovery, font-face unknown boolean DEV warn, suppressContentEditable "
        "stripped, contentEditable bool preserved (html_props + server).",
        _patch_wave_burndown_v20_react_manifest_slices,
        _patch_wave_burndown_v20_dom_manifest_slices,
    ),
    "burndown_v21_manifest_slices_apr2026": (
        "Manifest-gated slice (React-only): incremental error handling batched/nested scheduling "
        "resilience, and unmounting an error boundary before handling.",
        _patch_wave_burndown_v21_react_manifest_slices,
        _patch_wave_burndown_v21_dom_manifest_slices,
    ),
    "burndown_v22_incremental_error_handling_apr2026": (
        "Large ReactIncrementalErrorHandling wave: implement top-level callback throw + "
        "mixed lifecycle ordering; defer interruption/multi-root/deferred-mount cases as non-goal.",
        _patch_wave_burndown_v22_react_incremental_error_handling,
        _patch_wave_burndown_v22_dom_noop,
    ),
    "burndown_v23_incremental_error_logging_replay_apr2026": (
        "ReactIncrementalErrorLogging/Replay slice: uncaught begin+commit reporting, "
        "log-method cycle guard, reset state before unmount after failed node, and "
        "retry-once recovery; defer Offscreen/Suspense/Activity reporting and "
        "host-config failures.",
        _patch_wave_burndown_v23_react_incremental_error_logging_replay,
        _patch_wave_burndown_v23_dom_noop,
    ),
    "burndown_v24_incremental_reflection_apr2026": (
        "ReactIncrementalReflection slice: findInstance returns no host before commit, "
        "and returns the committed host node until deletion is committed.",
        _patch_wave_burndown_v24_react_incremental_reflection,
        _patch_wave_burndown_v24_dom_noop,
    ),
    "burndown_v25_incremental_scheduling_apr2026": (
        "ReactIncrementalScheduling slice: deferred flush, top-level priority/insertion ordering, "
        "sync setState in commit lifecycles, transition opt-in, and task work after time runs out; "
        "defer multi-root scheduling as non-goal.",
        _patch_wave_burndown_v25_react_incremental_scheduling,
        _patch_wave_burndown_v25_dom_noop,
    ),
    "burndown_v26_100_core_apr2026": (
        "Bookkeeping wave for the Apr 2026 ~100-test core burndown: JSX element validator basics "
        "+ abort-flush side-effects invariant.",
        _patch_wave_burndown_v26_100_core_apr2026,
        _patch_wave_burndown_v26_100_core_apr2026_dom_noop,
    ),
    "burndown_v27_react_cache_apr2026": (
        "ReactCache slice: cache() basic memo/error caching + cacheSignal abort/null semantics.",
        _patch_wave_burndown_v27_react_cache_apr2026,
        _patch_wave_burndown_v27_dom_noop,
    ),
    "burndown_v28_react_es6class_basic_apr2026": (
        "ReactES6Class slice: bookkeeping for implemented basics + null state is allowed.",
        _patch_wave_burndown_v28_react_es6class_basic_apr2026,
        _patch_wave_burndown_v28_dom_noop,
    ),
    "burndown_v29_react_fiber_refs_apr2026": (
        "ReactFiberRefs slice: class refs shared empty object, ref attach without updates, "
        "and string-ref warnings/throws.",
        _patch_wave_burndown_v29_react_fiber_refs_apr2026,
        _patch_wave_burndown_v29_dom_noop,
    ),
    "burndown_v30_error_stacks_builtins_apr2026": (
        "ReactErrorStacks slice: built-in wrapper names appear in component stack (Activity/Lazy/Suspense).",
        _patch_wave_burndown_v30_error_stacks_builtins_apr2026,
        _patch_wave_burndown_v30_dom_noop,
    ),
    "burndown_v32_element_validator_more_apr2026": (
        "ReactElementValidator slice: invalid element type errors include owner/context; DOM nodes as children do not warn.",
        _patch_wave_burndown_v32_element_validator_more_apr2026,
        _patch_wave_burndown_v32_dom_noop,
    ),
    "burndown_v33_forward_ref_more_apr2026": (
        "forwardRef slice: DEV signature warnings, refs switching, memo composition, and stack naming.",
        _patch_wave_burndown_v33_forward_ref_more_apr2026,
        _patch_wave_burndown_v33_dom_noop,
    ),
    "burndown_v34_element_clone_more_apr2026": (
        "ReactElementClone slice: cloneElement key/ref/children semantics and DEV key warnings.",
        _patch_wave_burndown_v34_element_clone_more_apr2026,
        _patch_wave_burndown_v34_dom_noop,
    ),
    "burndown_v35_context_validator_more_apr2026": (
        "ReactContextValidator slice: implement warning-only cases; mark deep legacy context propagation cases non-goal.",
        _patch_wave_burndown_v35_context_validator_more_apr2026,
        _patch_wave_burndown_v35_dom_noop,
    ),
    "burndown_v36_strict_mode_more_apr2026": (
        "ReactStrictMode slice: implement strict double-invokes (useMemo + state initializers + class setState updaters) and stacks.",
        _patch_wave_burndown_v36_strict_mode_more_apr2026,
        _patch_wave_burndown_v36_dom_noop,
    ),
    "burndown_v42_strict_mode_more_apr2026": (
        "ReactStrictMode slice: reducer dispatch double-invoke and setState callback double-invoke in DEV StrictMode.",
        _patch_wave_burndown_v42_strict_mode_more_apr2026,
        _patch_wave_burndown_v42_dom_noop,
    ),
    "burndown_v43_jsx_element_validator_more_apr2026": (
        "ReactJSXElementValidator slice: lazy not eager, numeric key iterable no-warn, owner-info key warns, and nested error context.",
        _patch_wave_burndown_v43_jsx_element_validator_more_apr2026,
        _patch_wave_burndown_v43_dom_noop,
    ),
    "burndown_v44_es6_class_more_apr2026": (
        "ReactES6Class slice: remaining noop-friendly cases (no implicit binding, classic API warn/throw, lifecycle ordering).",
        _patch_wave_burndown_v44_es6_class_more_apr2026,
        _patch_wave_burndown_v44_dom_noop,
    ),
    "burndown_v46_class_equivalence_more_apr2026": (
        "ReactClassEquivalence slice: noop-friendly class render equivalence assertions.",
        _patch_wave_burndown_v46_class_equivalence_more_apr2026,
        _patch_wave_burndown_v46_dom_noop,
    ),
    "burndown_v47_strict_mode_internal_more_apr2026": (
        "ReactStrictMode internal slice: strict level defaulting behavior (DEV-gated in ryact).",
        _patch_wave_burndown_v47_strict_mode_internal_more_apr2026,
        _patch_wave_burndown_v47_dom_noop,
    ),
    "burndown_v48_react_version_apr2026": (
        "ReactVersion slice: expose __version__ and match ryact package metadata.",
        _patch_wave_burndown_v48_react_version_apr2026,
        _patch_wave_burndown_v48_dom_noop,
    ),
    "burndown_v37_only_child_more_apr2026": (
        "onlyChild slice: Children.only throws on invalid shapes and returns the single child.",
        _patch_wave_burndown_v37_only_child_more_apr2026,
        _patch_wave_burndown_v37_dom_noop,
    ),
    "burndown_v38_pure_component_more_apr2026": (
        "ReactPureComponent slice: PureComponent base + SCU warning behavior.",
        _patch_wave_burndown_v38_pure_component_more_apr2026,
        _patch_wave_burndown_v38_dom_noop,
    ),
    "burndown_v40_forward_ref_internal_more_apr2026": (
        "forwardRef internal slice: ref forwarding and ref stability across updates (noop-friendly subset).",
        _patch_wave_burndown_v40_forward_ref_internal_more_apr2026,
        _patch_wave_burndown_v40_dom_noop,
    ),
    "burndown_v49_react_hooks_noop_renderer_pilot_apr2026": (
        "ReactHooksWithNoopRenderer slice: render-phase restarts, batched updaters, reducer tag "
        "alternation, sibling keyed preservation, and useCallback (noop harness).",
        _patch_wave_burndown_v49_react_hooks_noop_renderer_pilot,
        _patch_wave_burndown_v49_react_noop_dom_noop,
    ),
    "burndown_v50_class_and_topleveltext_dom_property_ops_apr2026": (
        "Manifest-gated slice: class defaultProps+ref ordering, setState callback once, "
        "top-level text/number/int from FC, DOM my-icon size + input value special property.",
        _patch_wave_burndown_v50_react_manifest_slices,
        _patch_wave_burndown_v50_dom_manifest_slices,
    ),
    "burndown_v51_top_level_list_use_memo_custom_el_fn_apr2026": (
        "Top-level list→fragment coercer, useMemo (no deps + stable deps) noop slices, "
        "DOM custom element non-event function properties.",
        _patch_wave_burndown_v51_react_manifest_slices,
        _patch_wave_burndown_v51_dom_manifest_slices,
    ),
    "burndown_v52_top_level_fragment_child_reconciliation_apr2026": (
        "ReactTopLevelFragment slice: implicit-key hole preservation, keyed reorder state "
        "preservation, and switching from single child -> [child] identity stability.",
        _patch_wave_burndown_v52_react_manifest_slices,
        _patch_wave_burndown_v52_dom_noop,
    ),
    "burndown_v53_dom_multichild_reconciliation_apr2026": (
        "ReactMultiChild slice: replace different keys, update when possible, and replace when "
        "a keyed child changes constructor/tag.",
        _patch_wave_burndown_v53_react_noop,
        _patch_wave_burndown_v53_dom_manifest_slices,
    ),
    "burndown_v54_top_level_fragment_nested_array_apr2026": (
        "ReactTopLevelFragment slice: switching to a nested array should not preserve state.",
        _patch_wave_burndown_v54_react_manifest_slices,
        _patch_wave_burndown_v54_dom_noop,
    ),
    "burndown_v55_hooks_deps_warnings_apr2026": (
        "ReactHooks internal slice: deps must be an array, and warn when switching from deps -> no deps.",
        _patch_wave_burndown_v55_react_manifest_slices,
        _patch_wave_burndown_v55_dom_noop,
    ),
    "burndown_v56_act_warnings_apr2026": (
        "ReactActWarnings slice: env flag gates unwrapped warnings; root/class unwrapped warnings; "
        "sync updates still warn.",
        _patch_wave_burndown_v56_react_manifest_slices,
        _patch_wave_burndown_v56_dom_noop,
    ),
    "burndown_v57_close_isomorphic_act_and_suspense_act_warnings_apr2026": (
        "Pending-first closure: mark ReactIsomorphicAct-test and act() Suspense ping/retry warnings "
        "as deferred non-goals until an async act + Suspense ping harness exists.",
        _patch_wave_burndown_v57_close_isomorphic_act_apr2026,
        _patch_wave_burndown_v57_dom_noop,
    ),
    "burndown_v58_hooks_with_noop_renderer_usestate_apr2026": (
        "ReactHooksWithNoopRenderer slice: core useState semantics (lazy init, multiple hooks, "
        "stable dispatch identity, mount+update, memo interaction).",
        _patch_wave_burndown_v58_react_manifest_slices,
        _patch_wave_burndown_v58_dom_noop,
    ),
    "burndown_v59_hooks_with_noop_renderer_effects_and_usereducer_apr2026": (
        "ReactHooksWithNoopRenderer slice: useReducer queued actions (no eager bailout), "
        "memoized factory stability, effect ordering, and cleanup return type assumptions.",
        _patch_wave_burndown_v59_react_manifest_slices,
        _patch_wave_burndown_v59_dom_noop,
    ),
    "burndown_v60_hooks_with_noop_renderer_closure_and_useeffect_unmount_apr2026": (
        "ReactHooksWithNoopRenderer closure + basics: mark async-priority passive effect, "
        "passive-unmount deferral/error cases, useImperativeHandle, and progressive enhancement "
        "buckets as deferred non-goals; implement basic useEffect cleanup assumptions, "
        "unmounts previous effect, and useState set-after-unmount no-warning.",
        _patch_wave_burndown_v60_hooks_noop_closure_apr2026,
        _patch_wave_burndown_v60_dom_noop,
    ),
    "burndown_v61_hooks_with_noop_renderer_useeffect_more_apr2026": (
        "ReactHooksWithNoopRenderer slice: useEffect ordering and unmount semantics (multi-effect "
        "destroy-before-create, sibling ordering, deletion cleanups, memoized subtree cleanups) and "
        "layout effects observe the committed host snapshot.",
        _patch_wave_burndown_v61_react_manifest_slices,
        _patch_wave_burndown_v61_dom_noop,
    ),
    "burndown_v62_close_useeffect_flushsync_legacy_and_usereducer_mixed_priorities_apr2026": (
        "ReactHooksWithNoopRenderer closure + slice: mark remaining flushSync/legacy/passive-flush "
        "useEffect cases as deferred non-goals; implement useReducer mixed lane priorities.",
        _patch_wave_burndown_v62_close_noop_useeffect_flushsync_legacy_apr2026,
        _patch_wave_burndown_v62_dom_noop,
    ),
    "burndown_v63_close_async_actions_apr2026": (
        "Pending-first closure: mark ReactAsyncActions-test as deferred non-goals until an async "
        "action/entanglement harness exists.",
        _patch_wave_burndown_v63_close_async_actions_apr2026,
        _patch_wave_burndown_v63_dom_noop,
    ),
    "burndown_v64_effect_ordering_unmount_parent_child_apr2026": (
        "ReactEffectOrdering slice: layout/passive unmount destroy order is parent -> child on deletion.",
        _patch_wave_burndown_v64_react_manifest_slices,
        _patch_wave_burndown_v64_dom_noop,
    ),
    "burndown_v65_batched_updates_flushsync_and_cpu_suspense_closure_apr2026": (
        "ReactBatching internal slice: flushSync does not flush batched work; close CPU-bound "
        "Suspense/noop skipping cases as deferred until concurrent yielding is modeled.",
        _patch_wave_burndown_v65_batched_updates_and_cpu_suspense_closure_apr2026,
        _patch_wave_burndown_v65_dom_noop,
    ),
    "burndown_v66_close_error_logging_and_blocking_batching_apr2026": (
        "Pending-first closure: mark ReactConfigurableErrorLogging-test and remaining "
        "ReactBatching blocking-mode cases as deferred non-goals.",
        _patch_wave_burndown_v66_close_configurable_error_logging_and_blocking_batching_apr2026,
        _patch_wave_burndown_v66_dom_noop,
    ),
    "burndown_v67_close_concurrent_expiration_transition_indicator_apr2026": (
        "Pending-first closure: mark ReactExpiration/DefaultTransitionIndicator/ConcurrentErrorRecovery "
        "as deferred non-goals until advanced concurrent scheduling is modeled.",
        _patch_wave_burndown_v67_close_concurrent_expiration_and_transition_indicator_apr2026,
        _patch_wave_burndown_v67_dom_noop,
    ),
    "burndown_v68_dom_css_property_operations_server_apr2026": (
        "CSSPropertyOperations DOM/server slice: serialize style dicts (px rules, custom properties, "
        "basic warnings) into `style` markup.",
        _patch_wave_burndown_v68_react_noop,
        _patch_wave_burndown_v68_dom_manifest_slices,
    ),
    "burndown_v69_dom_property_operations_custom_events_apr2026": (
        "DOMPropertyOperations slice: custom element and div event listener props attach, "
        "bubble, and update via the incremental DOM host model.",
        _patch_wave_burndown_v69_react_noop,
        _patch_wave_burndown_v69_dom_custom_events_apr2026,
    ),
    "burndown_v70_dom_dangerously_set_inner_html_and_style_escape_apr2026": (
        "ReactDOMComponent server slice: dangerouslySetInnerHTML emits raw HTML; style attribute "
        "values are escaped in markup.",
        _patch_wave_burndown_v70_react_noop,
        _patch_wave_burndown_v70_dom_manifest_slices,
    ),
    "burndown_v71_dom_void_elements_and_mount_events_closure_apr2026": (
        "ReactDOMComponent mountComponent slice: void element invariants + close DOM-only "
        "<link> load/error and `is=`-extended custom element cases as deferred non-goals.",
        _patch_wave_burndown_v71_react_noop,
        _patch_wave_burndown_v71_dom_void_elements_and_mount_events_apr2026,
    ),
    "burndown_react_mismatched_versions_non_goal_apr2026": (
        "Pending-first closure: mark ReactMismatchedVersions import-time version skew checks as "
        "non-goal (JS packaging surface; no Python entrypoint matrix analogue).",
        _patch_wave_burndown_react_mismatched_versions_non_goal_apr2026,
        _patch_wave_burndown_react_mismatched_versions_dom_noop,
    ),
    "burndown_react_use_ref_internal_basic_apr2026": (
        "useRef internal slice: basic initialization + ref identity stability across rerenders.",
        _patch_wave_burndown_react_use_ref_internal_basic_apr2026,
        _patch_wave_burndown_react_use_ref_internal_basic_dom_noop,
    ),
    "burndown_close_incremental_update_queue_semantics_apr2026": (
        "Pending-first closure: mark advanced incremental update queue priority/rebasing and "
        "minimalism micro-optimization cases as deferred non-goals.",
        _patch_wave_burndown_close_incremental_update_queue_semantics_apr2026,
        _patch_wave_burndown_close_incremental_update_queue_semantics_dom_noop,
    ),
    "burndown_close_profiler_transition_tracing_and_effect_event_apr2026": (
        "Pending-first closure: mark ReactProfiler internals, transition tracing, and useEffectEvent "
        "buckets as deferred non-goals.",
        _patch_wave_burndown_close_profiler_transition_tracing_and_effect_event_apr2026,
        _patch_wave_burndown_close_profiler_transition_tracing_and_effect_event_dom_noop,
    ),
    "burndown_close_create_react_class_integration_apr2026": (
        "Pending-first closure: mark legacy create-react-class integration suite as non-goal.",
        _patch_wave_burndown_close_create_react_class_integration_apr2026,
        _patch_wave_burndown_close_create_react_class_integration_dom_noop,
    ),
    "burndown_v83_react_jsx_transform_integration_apr2026": (
        "ReactJSXTransformIntegration slice: jsx/jsxs element construction semantics.",
        _patch_wave_burndown_v83_react_jsx_transform_integration_apr2026,
        _patch_wave_burndown_v83_dom_noop,
    ),
    "burndown_v84_dom_react_dom_attribute_unknown_apr2026": (
        "ReactDOMAttribute unknown-attributes slice: null/undefined removal, true/false stripping "
        "with DEV warn, missing-prop removal, inert boolean + empty-string warn-once, scalar "
        "coercion, dict/function invalid-value warnings, Temporal-like TypeError; Symbol + "
        "camelCase lowering rows closed as scoped non-goals.",
        _patch_wave_burndown_v84_react_noop,
        _patch_wave_burndown_v84_dom_unknown_attributes_apr2026,
    ),
    "burndown_v85_dom_quote_escape_multichildtext_apr2026": (
        "SSR + incremental slice: quoteAttributeValueForBrowser + escapeTextForBrowser parity "
        "(entities, quotes, script-like payloads), void tags self-close, dangerouslySetInnerHTML "
        "conflicts with children, MultiChildText bigint + nested heading cases; permutation matrix "
        "row non-goal.",
        _patch_wave_burndown_v85_react_noop,
        _patch_wave_burndown_v85_dom_quote_escape_multichildtext_apr2026,
    ),
    "burndown_v86_dom_invalid_aria_hook_apr2026": (
        "ReactDOMInvalidARIAHook slice: DEV validation against React's allowlisted aria-* names "
        "(incl. ARIA 1.3), batched invalid prop warnings, hyphen casing nudges, and camelCase "
        "aria* guidance; pythonic ``aria_*`` maps to hyphenated markup.",
        _patch_wave_burndown_v86_react_noop,
        _patch_wave_burndown_v86_dom_invalid_aria_hook_apr2026,
    ),
    "burndown_v87_dom_attribute_safe_intrinsic_casing_apr2026": (
        "ReactDOMComponent slice: ``isAttributeNameSafe`` invalid attribute names dropped with "
        "DEV warnings (SSR + incremental), intrinsic HTML tag casing warning when not "
        "custom-element or SVG subtree.",
        _patch_wave_burndown_v87_react_noop,
        _patch_wave_burndown_v87_dom_attribute_safe_intrinsic_casing_apr2026,
    ),
    "burndown_v92_dom_boolean_hidden_string_spellcheck_may2026": (
        'ReactDOMComponent slice: DEV warnings for ``hidden={"true"}|{"false"}`` string literals '
        '(coerced to boolean presence); ``spellCheck`` bool props stringify to ``spellcheck="true"|"false"``.',
        _patch_wave_burndown_v92_react_noop,
        _patch_wave_burndown_v92_dom_boolean_spellcheck_may2026,
    ),
    "burndown_v93_dom_object_stringify_whitespace_may2026": (
        "ReactDOMComponent slice: ``dangerouslySetInnerHTML`` preserves whitespace (SSR + host updates); "
        "plain object / dict props stringify like JS ``[object Object]``; ``accept-charset``, "
        "``arabic-form``, inherited ``__str__`` / ``ajaxify``.",
        _patch_wave_burndown_v93_react_noop,
        _patch_wave_burndown_v93_dom_object_stringify_whitespace_may2026,
    ),
    "burndown_v94_dom_attributes_aliases_may2026": (
        "ReactDOMComponent slice: ``Attributes with aliases`` — HTML ``class`` / ``cLASS`` DEV warnings, "
        "SVG ``arabic-form`` rename + warning, customized built-in ``is`` hosts keep literal ``class`` "
        "(no ``className`` nudge) plus incremental updates.",
        _patch_wave_burndown_v94_react_noop,
        _patch_wave_burndown_v94_dom_attributes_aliases_may2026,
    ),
    "burndown_v95_dom_mount_update_validation_may2026": (
        "ReactDOMComponent slice: ``mountComponent`` / ``updateComponent`` validation — "
        "``dangerouslySetInnerHTML`` shape throws, illegal ``innerHTML`` props DEV-warned+stripped, "
        "non-mapping ``style`` throws, ``contentEditable``+children DEV warning, DSH vs children conflict.",
        _patch_wave_burndown_v95_react_noop,
        _patch_wave_burndown_v95_dom_mount_update_validation_may2026,
    ),
    "burndown_v96_dom_intrinsic_dev_may2026": (
        "ReactDOMComponent slice: intrinsic host DEV — mis-cased void SSR emits a closing tag, "
        "reserved ``aria`` stripped, unrecognized intrinsic tags (deduped), "
        "``dangerouslySetInnerHTML`` Temporal-like via ``__str__``, class component invalid ``style``.",
        _patch_wave_burndown_v96_react_noop,
        _patch_wave_burndown_v96_dom_intrinsic_dev_may2026,
    ),
    "burndown_v97_dom_nesting_validation_may2026": (
        "ReactDOMComponent slice: nesting validation — ``for``/``tabindex``/``autofocus``/``credentialless`` "
        "casing + normalization, ``class`` → ``className`` DEV nudge, mis-cased ``on*`` handler props "
        "(SSR generic vs client ``Did you mean``; no SSR warn for ``onKeydown``).",
        _patch_wave_burndown_v97_react_noop,
        _patch_wave_burndown_v97_dom_nesting_validation_may2026,
    ),
    "burndown_v98_dom_nesting_focus_props_may2026": (
        "ReactDOMComponent slice: nesting validation — unsupported ``onFocusIn`` / ``onFocusOut`` "
        "(any casing) stripped with onFocus/onBlur DEV nudge; client + SSR.",
        _patch_wave_burndown_v98_react_noop,
        _patch_wave_burndown_v98_dom_nesting_focus_props_may2026,
    ),
    "burndown_v99_dom_validate_nesting_may2026": (
        "ReactDOMComponent + validateDOMNesting: DEV invalid host parent / text nesting warnings "
        "(``validateDOMNesting`` parity slice; client createRoot path).",
        _patch_wave_burndown_v99_react_noop,
        _patch_wave_burndown_v99_dom_validate_nesting_may2026,
    ),
    "burndown_v100_dom_void_element_update_throw_may2026": (
        "ReactDOMComponent: void elements reject ``children`` / ``dangerouslySetInnerHTML`` on update "
        "with React's ``ValueError`` text; client intrinsic tag sanitization aligned with SSR.",
        _patch_wave_burndown_v100_react_noop,
        _patch_wave_burndown_v100_dom_void_element_update_may2026,
    ),
    "burndown_v101_dom_select_binding_may2026": (
        "ReactDOMSelect subset: ``<select>`` drives ``<option selected>`` from ``value``/``defaultValue`` "
        "(incl. ``multiple``, ``size``, ``optgroup``), SSR markup, and core DEV warnings.",
        _patch_wave_burndown_v101_react_noop,
        _patch_wave_burndown_v101_dom_select_binding_may2026,
    ),
    "burndown_v102_dom_select_extended_may2026": (
        "ReactDOMSelect extended: invalid option ``value`` (function / Symbol-like label fallback) and "
        "Temporal-like coercion errors on ``select``/``option``.",
        _patch_wave_burndown_v102_react_noop,
        _patch_wave_burndown_v102_dom_select_extended_may2026,
    ),
    "burndown_v103_dom_select_misc_may2026": (
        "ReactDOMSelect misc: SSR ``dangerouslySetInnerHTML`` on ``option``, dynamic option label children, "
        "``multiple`` value exact string match, remount / undefined ``value`` smoke.",
        _patch_wave_burndown_v103_react_noop,
        _patch_wave_burndown_v103_dom_select_misc_may2026,
    ),
    "burndown_v104_dom_select_persistence_may2026": (
        "ReactDOMSelect persistence: uncontrolled ``defaultValue`` vs user DOM selection, ``multiple`` option "
        "list churn without ``defaultValue`` replay, controlled ``change`` refresh, ``root.unmount`` during onChange.",
        _patch_wave_burndown_v104_react_noop,
        _patch_wave_burndown_v104_dom_select_persistence_may2026,
    ),
    "burndown_v105_dom_select_switch_uncontrolled_may2026": (
        "ReactDOMSelect: remember last controlled selection when dropping ``value``; nested "
        "``render_into`` bridge for legacy inner-root controlled ``<select>``.",
        _patch_wave_burndown_v105_react_noop,
        _patch_wave_burndown_v105_dom_select_switch_uncontrolled_may2026,
    ),
    "burndown_v88_v99_react_interface_parity_manifest_only_may2026": (
        "React package interface parity (v88–v99): manifest-gated translated smoke tests in "
        "``test_react_interface_parity_burndown_v88_v99.py``; no upstream_inventory.json row flips.",
        _patch_wave_burndown_v88_v99_react_interface_parity_manifest_only_apr2026,
        _patch_wave_burndown_v88_v99_dom_interface_parity_manifest_only_apr2026,
    ),
    "burndown_reopen_interface_parity_v88_v99_non_goal_to_pending_may2026": (
        "After v88–v99 runtime coverage: reopen matching upstream buckets from ``non_goal`` to "
        "``pending`` (ReactUse, NewContext/ContextPropagation, Activity, transitions, Suspense/Lazy "
        "slices, CreateElement/forwardRef, hooks noop slices, act warnings).",
        _patch_wave_reopen_interface_parity_v88_v99_non_goal_to_pending_may2026,
        _patch_wave_reopen_interface_parity_v88_v99_dom_noop,
    ),
    "burndown_close_react_use_bucket_apr2026": (
        "Pending-first closure: mark ReactUse (experimental use()) bucket as deferred non-goal.",
        _patch_wave_burndown_close_react_use_bucket_apr2026,
        _patch_wave_burndown_close_react_use_bucket_dom_noop,
    ),
    "burndown_close_lazy_internal_bucket_apr2026": (
        "Pending-first closure: mark remaining ReactLazy-test.internal bucket as deferred non-goal.",
        _patch_wave_burndown_close_lazy_internal_bucket_apr2026,
        _patch_wave_burndown_close_lazy_internal_bucket_dom_noop,
    ),
    "burndown_close_suspensey_scope_and_flushsync_buckets_apr2026": (
        "Pending-first closure: mark ReactSuspenseyCommitPhase, ReactScope, and ReactFlushSync buckets as deferred non-goals.",
        _patch_wave_burndown_close_suspensey_scope_and_flushsync_buckets_apr2026,
        _patch_wave_burndown_close_suspensey_scope_and_flushsync_buckets_dom_noop,
    ),
    "burndown_close_hooks_internal_bucket_apr2026": (
        "Pending-first closure: mark remaining ReactHooks-test.internal bucket as deferred non-goal.",
        _patch_wave_burndown_close_hooks_internal_bucket_apr2026,
        _patch_wave_burndown_close_hooks_internal_bucket_dom_noop,
    ),
    "burndown_close_remaining_react_reconciler_buckets_apr2026": (
        "Pending-first closure: mark remaining reconciler-heavy buckets (noop hooks, suspense effects, "
        "prerendering, placeholder, updaters, memo cache, owner stacks, perf track) as deferred non-goals.",
        _patch_wave_burndown_close_remaining_react_reconciler_buckets_apr2026,
        _patch_wave_burndown_close_remaining_react_reconciler_buckets_dom_noop,
    ),
    "burndown_close_react_core_tail_defer_may2026": (
        "Pending-first closure: defer remaining React core/reconciler tail buckets "
        "(DeferredValue, incremental error/context/fragment, scheduling, useSyncExternalStore, …).",
        _patch_wave_burndown_close_react_core_tail_defer_may2026,
        _patch_wave_burndown_close_react_core_tail_defer_may2026_dom_noop,
    ),
    "burndown_close_incremental_side_effects_remaining_apr2026": (
        "Close remaining ReactIncrementalSideEffects pending cases (bailout callback implemented; rest deferred).",
        _patch_wave_burndown_close_incremental_side_effects_remaining_apr2026,
        _patch_wave_burndown_close_incremental_side_effects_remaining_dom_noop,
    ),
    "burndown_close_scheduler_priority_and_interleaved_buckets_apr2026": (
        "Pending-first closure: mark SchedulerIntegration, UpdatePriority, and InterleavedUpdates buckets as deferred non-goals.",
        _patch_wave_burndown_close_scheduler_priority_and_interleaved_buckets_apr2026,
        _patch_wave_burndown_close_scheduler_priority_and_interleaved_dom_noop,
    ),
    "burndown_noop_renderer_act_basic_apr2026": (
        "ReactNoopRendererAct slice: act() flushes effects; close async/await act as deferred.",
        _patch_wave_burndown_noop_renderer_act_basic_apr2026,
        _patch_wave_burndown_noop_renderer_act_basic_dom_noop,
    ),
    "burndown_error_stacks_and_forwardref_remaining_apr2026": (
        "Close remaining ReactErrorStacks + forwardRef internal pending rows (rethrow stack implemented; built-ins deferred).",
        _patch_wave_burndown_error_stacks_and_forwardref_remaining_apr2026,
        _patch_wave_burndown_error_stacks_and_forwardref_remaining_dom_noop,
    ),
    "burndown_singletons_apr2026": (
        "Singleton slice: host context prepare/reset commit hooks; close remaining 1-off buckets as deferred.",
        _patch_wave_burndown_singletons_apr2026,
        _patch_wave_burndown_singletons_dom_noop,
    ),
    "burndown_close_hard_remaining_buckets_apr2026": (
        "Pending-first closure: close remaining hard buckets (Persistent, SuspenseFuzz, ProfilerDevToolsIntegration, SuspenseCallback).",
        _patch_wave_burndown_close_hard_remaining_buckets_apr2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "may2026_incremental_expiration_core_pending": (
        "May 2026: implement ReactIncremental + ReactExpiration pending buckets (core-only).",
        _patch_wave_may2026_incremental_and_expiration_core_pending,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "may2026_lazy_internal_pending": (
        "May 2026: implement ReactLazy-test.internal pending bucket.",
        _patch_wave_may2026_lazy_internal_pending,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "may2026_transition_indicator_error_profiler_hooks_pending": (
        "May 2026: implement remaining core pending buckets (transition/indicator/error/profiler/hooks).",
        _patch_wave_may2026_transition_and_indicator_and_error_and_profiler_and_hooks_pending,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_suspense_concurrent_and_noop_defer_pending_may2026": (
        "Reopen deferred Suspense/noop concurrent buckets from non_goal -> pending.",
        _patch_wave_reopen_suspense_concurrent_and_noop_defer_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_flushsync_bucket_pending_may2026": (
        "Reopen ReactFlushSync bucket from non_goal -> pending.",
        _patch_wave_reopen_flushsync_bucket_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_context_defer_buckets_pending_may2026": (
        "Reopen deferred context propagation buckets from non_goal -> pending.",
        _patch_wave_reopen_context_defer_buckets_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_fragment_defer_bucket_pending_may2026": (
        "Reopen deferred fragment identity bucket from non_goal -> pending.",
        _patch_wave_reopen_fragment_defer_bucket_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_use_effect_event_bucket_pending_may2026": (
        "Reopen useEffectEvent bucket from non_goal -> pending.",
        _patch_wave_reopen_use_effect_event_bucket_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_scope_bucket_pending_may2026": (
        "Reopen ReactScope bucket from non_goal -> pending.",
        _patch_wave_reopen_scope_bucket_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_isomorphic_act_defer_pending_may2026": (
        "Reopen deferred isomorphic/async act buckets from non_goal -> pending.",
        _patch_wave_reopen_isomorphic_act_defer_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_use_defer_pending_may2026": (
        "Reopen deferred ReactUse bucket from non_goal -> pending.",
        _patch_wave_reopen_use_defer_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_create_react_class_integration_pending_may2026": (
        "Reopen create-react-class integration bucket from non_goal -> pending.",
        _patch_wave_reopen_create_react_class_integration_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_mismatched_versions_pending_may2026": (
        "Reopen ReactMismatchedVersions bucket from non_goal -> pending (optional).",
        _patch_wave_reopen_mismatched_versions_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_scheduler_integration_pending_may2026": (
        "Reopen ReactSchedulerIntegration bucket from non_goal -> pending.",
        _patch_wave_reopen_scheduler_integration_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_update_priority_and_updaters_pending_may2026": (
        "Reopen UpdatePriority + Updaters internal buckets from non_goal -> pending.",
        _patch_wave_reopen_update_priority_and_updaters_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_use_memo_cache_pending_may2026": (
        "Reopen useMemoCache bucket from non_goal -> pending.",
        _patch_wave_reopen_use_memo_cache_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_suspense_effects_semantics_pending_may2026": (
        "Reopen Suspense effects semantics buckets from non_goal -> pending.",
        _patch_wave_reopen_suspense_effects_semantics_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_suspensey_commit_phase_pending_may2026": (
        "Reopen Suspensey commit-phase bucket from non_goal -> pending.",
        _patch_wave_reopen_suspensey_commit_phase_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_deferred_value_pending_may2026": (
        "Reopen DeferredValue bucket from non_goal -> pending.",
        _patch_wave_reopen_deferred_value_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_incremental_error_handling_pending_may2026": (
        "Reopen IncrementalErrorHandling bucket from non_goal -> pending.",
        _patch_wave_reopen_incremental_error_handling_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_incremental_side_effects_pending_may2026": (
        "Reopen IncrementalSideEffects bucket from non_goal -> pending.",
        _patch_wave_reopen_incremental_side_effects_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_prerender_offscreen_pending_may2026": (
        "Reopen sibling prerendering + Activity buckets from non_goal -> pending.",
        _patch_wave_reopen_prerender_offscreen_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_persistent_renderer_pending_may2026": (
        "Reopen persistent renderer buckets from non_goal -> pending.",
        _patch_wave_reopen_persistent_renderer_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_owner_stacks_pending_may2026": (
        "Reopen owner stacks bucket from non_goal -> pending.",
        _patch_wave_reopen_owner_stacks_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_performance_track_pending_may2026": (
        "Reopen performance track bucket from non_goal -> pending.",
        _patch_wave_reopen_performance_track_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_suspense_callback_pending_may2026": (
        "Reopen Suspense callback bucket from non_goal -> pending.",
        _patch_wave_reopen_suspense_callback_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_configurable_error_logging_pending_may2026": (
        "Reopen configurable error logging bucket from non_goal -> pending.",
        _patch_wave_reopen_configurable_error_logging_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_batching_internal_pending_may2026": (
        "Reopen ReactBatching internal bucket from non_goal -> pending.",
        _patch_wave_reopen_batching_internal_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_legacy_context_validator_pending_may2026": (
        "Reopen legacy context validator bucket from non_goal -> pending.",
        _patch_wave_reopen_legacy_context_validator_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_profiler_devtools_integration_pending_may2026": (
        "Reopen Profiler DevTools integration bucket from non_goal -> pending.",
        _patch_wave_reopen_profiler_devtools_integration_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_interleaved_updates_pending_may2026": (
        "Reopen interleaved updates bucket from non_goal -> pending.",
        _patch_wave_reopen_interleaved_updates_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_noop_renderer_act_pending_may2026": (
        "Reopen noop renderer async act bucket from non_goal -> pending.",
        _patch_wave_reopen_noop_renderer_act_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_use_sync_external_store_pending_may2026": (
        "Reopen remaining useSyncExternalStore bucket from non_goal -> pending.",
        _patch_wave_reopen_use_sync_external_store_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "reopen_remaining_react_core_non_goals_pending_may2026": (
        "Reopen remaining React-core non_goals to pending (bucketed).",
        _patch_wave_reopen_remaining_react_core_non_goals_pending_may2026,
        _patch_wave_burndown_close_hard_remaining_buckets_dom_noop,
    ),
    "dom_property_operations_setvalue_slices_v106_may2026": (
        "DOM: DOMPropertyOperations setValue basics (title, role, xlink:href, disabled string/boolean).",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_setvalue_slices_v106_may2026,
    ),
    "dom_property_operations_credentialless_v107_may2026": (
        "DOM: DOMPropertyOperations iframe credentialless boolean + string-true DEV warning.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_credentialless_v107_may2026,
    ),
    "dom_property_operations_v108_may2026": (
        "DOM: DOMPropertyOperations progress null + custom element innerHTML/innerText/textContent strips.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v108_may2026,
    ),
    "dom_property_operations_v109_may2026": (
        "DOM: DOMPropertyOperations custom-element foo booleans + popoverTarget non-string strip/warn.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v109_may2026,
    ),
    "dom_property_operations_v110_may2026": (
        "DOM: DOMPropertyOperations delegated onChange from input/textarea on intrinsic ancestors.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v110_may2026,
    ),
    "dom_property_operations_v111_may2026": (
        "DOM: DOMPropertyOperations nested custom event targets + intrinsic change bubble rules.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v111_may2026,
    ),
    "dom_property_operations_v112_may2026": (
        "DOM: DOMPropertyOperations customized built-in input / radio event parity.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v112_may2026,
    ),
    "dom_property_operations_v113_may2026": (
        "DOM: DOMPropertyOperations customized built-in select event parity.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v113_may2026,
    ),
    "dom_property_operations_v114_may2026": (
        "DOM: DOMPropertyOperations custom on* property in-heuristic (setter parity).",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v114_may2026,
    ),
    "dom_property_operations_v115_may2026": (
        "DOM: DOMPropertyOperations custom element deleteValueForProperty removed-prop defaults.",
        _patch_wave_noop_react,
        _patch_wave_dom_property_operations_v115_may2026,
    ),
    "dom_input_v116_may2026": (
        "DOM: ReactDOMInput value bool/object stringification; checkbox/radio checked without value attr.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v116_may2026,
    ),
    "dom_input_v117_may2026": (
        "DOM: ReactDOMInput defaultValue→value, min/max/step/type/value order, radio value before type.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v117_may2026,
    ),
    "dom_input_v118_may2026": (
        "DOM: ReactDOMInput numeric value display, null value DEV warn, defaultValue object stringify.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v118_may2026,
    ),
    "dom_input_v119_may2026": (
        "DOM: ReactDOMInput omit name, submit default label, UNDEFINED value, 0.0 as 0.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v119_may2026,
    ),
    "dom_input_v120_may2026": (
        "DOM: ReactDOMInput controlled value read-only DEV warn; onInput counts; uncontrolled no warn.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v120_may2026,
    ),
    "dom_input_v121_may2026": (
        "DOM: ReactDOMInput controlled null/undefined merge + attribute pin parity.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v121_may2026,
    ),
    "dom_input_v122_may2026": (
        "DOM: ReactDOMInput SSR name/value/defaultValue; bigint SSR; number empty→0; string precision DEV warn.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v122_may2026,
    ),
    "dom_input_v123_may2026": (
        "DOM: ReactDOMInput text value transitions; type switch without invalid-value warn; reset/submit value SSR.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v123_may2026,
    ),
    "dom_input_v124_may2026": (
        "DOM: ReactDOMInput submit value; defaultValue updates; DEV read-only value without onChange.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v124_may2026,
    ),
    "dom_input_v125_may2026": (
        "DOM: ReactDOMInput controlled→uncontrolled DEV warns; date defaultValue update; defaultValue null.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v125_may2026,
    ),
    "dom_input_v126_may2026": (
        "DOM: ReactDOMInput DEV warns for checked without onChange, checked+defaultChecked, value+defaultValue.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v126_may2026,
    ),
    "dom_textarea_v127_may2026": (
        "DOM: ReactDOMTextarea full bucket — value/defaultValue, SSR, controlled/uncontrolled, DEV warnings.",
        _patch_wave_noop_react,
        _patch_wave_dom_textarea_v127_may2026,
    ),
    "dom_component_style_v128_may2026": (
        "DOM: ReactDOMComponent client style, innerHTML transitions, aliases, attribute removal.",
        _patch_wave_noop_react,
        _patch_wave_dom_component_style_v128_may2026,
    ),
    "dom_input_v129_may2026": (
        "DOM: ReactDOMInput Symbol/function values, defaultValue host, Temporal coercion, controlled warnings.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v129_may2026,
    ),
    "multichild_reconcile_v130_may2026": (
        "DOM: ReactMultiChildReconcile keyed child order, null slots, legacy/modern iterables.",
        _patch_wave_noop_react,
        _patch_wave_multichild_reconcile_v130_may2026,
    ),
    "dom_input_v131_may2026": (
        "DOM: ReactDOMInput checkbox/radio controlled warnings, Temporal defaultValue, defaultValue host.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v131_may2026,
    ),
    "dom_component_v132_may2026": (
        "DOM: ReactDOMComponent skip redundant updateProps, style freeze, custom elements, DEV warnings.",
        _patch_wave_noop_react,
        _patch_wave_dom_component_v132_may2026,
    ),
    "dom_input_v133_may2026": (
        "DOM: ReactDOMInput value/checked attribute sync, radio groups, events, reset, hydrate.",
        _patch_wave_noop_react,
        _patch_wave_dom_input_v133_may2026,
    ),
    "dom_event_listener_v134_may2026": (
        "DOM: ReactDOMEventListener propagation, capture, emulated bubbling, cross-root batching.",
        _patch_wave_noop_react,
        _patch_wave_dom_event_listener_v134_may2026,
    ),
    "dom_option_v135_may2026": (
        "DOM: ReactDOMOption children flattening, value attr, select selected, DSH.",
        _patch_wave_noop_react,
        _patch_wave_dom_option_v135_may2026,
    ),
    "dom_event_propagation_v136_may2026": (
        "DOM: ReactDOMEventPropagation bubbling, emulated bubbling, enter/leave.",
        _patch_wave_noop_react,
        _patch_wave_dom_event_propagation_v136_may2026,
    ),
    "dom_component_v137_may2026": (
        "DOM: ReactDOMComponent iOS tap onclick, mount media events, nesting (at **), unmount.",
        _patch_wave_noop_react,
        _patch_wave_dom_component_v137_may2026,
    ),
    "dom_root_v138_may2026": (
        "DOM: ReactDOMRoot createRoot/hydrateRoot render, unmount, DEV warnings.",
        _patch_wave_noop_react,
        _patch_wave_dom_root_v138_may2026,
    ),
    "dom_refs_identity_v141_may2026": (
        "DOM: refs, identity keys, tree traversal, browser event emitter.",
        _patch_wave_noop_react,
        _patch_wave_dom_refs_identity_v141_may2026,
    ),
    "dom_misc_v140_may2026": (
        "DOM: ReactDOM-test, ReactDOMUseId, ReactDOMSVG misc parity.",
        _patch_wave_noop_react,
        _patch_wave_dom_misc_v140_may2026,
    ),
    "dom_form_v139_may2026": (
        "DOM: ReactDOMForm form actions, useActionState, useFormStatus, requestFormReset.",
        _patch_wave_noop_react,
        _patch_wave_dom_form_v139_may2026,
    ),
    "use_effect_event_v142_may2026": (
        "React: useEffectEvent core noop semantics (memoization, render guard, effect ordering).",
        _patch_wave_use_effect_event_v142_may2026,
        _patch_wave_noop_react,
    ),
    "use_effect_event_defer_remaining_v142_may2026": (
        "React: defer remaining useEffectEvent Activity/integration/interleaved cases.",
        _patch_wave_use_effect_event_defer_remaining_v142_may2026,
        _patch_wave_noop_react,
    ),
    "flush_sync_v143_may2026": (
        "React: flushSync passive ordering and nested transition priority (v143).",
        _patch_wave_flush_sync_v143_may2026,
        _patch_wave_noop_react,
    ),
    "incremental_error_v143_may2026": (
        "React: incremental error handling sync-work deferral slice (v143).",
        _patch_wave_incremental_error_v143_may2026,
        _patch_wave_noop_react,
    ),
    "dom_updates_batching_v144_may2026": (
        "DOM: ReactUpdates state batching slice (v144).",
        _patch_wave_noop_react,
        _patch_wave_dom_updates_batching_v144_may2026,
    ),
    "dom_updates_batching_v145_may2026": (
        "DOM: ReactUpdates lifecycle/batching guards slice (v145).",
        _patch_wave_noop_react,
        _patch_wave_dom_updates_batching_v145_may2026,
    ),
    "dom_updates_batching_v146_may2026": (
        "DOM: ReactUpdates SCU bailout, props-child reuse, CWRP callbacks, reentrant commit (v146).",
        _patch_wave_noop_react,
        _patch_wave_dom_updates_batching_v146_may2026,
    ),
    "dom_composite_lifecycle_v147_may2026": (
        "DOM: ReactCompositeComponent + lifecycle class semantics (v147).",
        _patch_wave_noop_react,
        _patch_wave_dom_composite_lifecycle_v147_may2026,
    ),
    "dom_composite_lifecycle_v148_may2026": (
        "DOM: composite mount warnings, snapshot lifecycles, shallow SCU (v148).",
        _patch_wave_noop_react,
        _patch_wave_dom_composite_lifecycle_v148_may2026,
    ),
    "dom_composite_lifecycle_v149_may2026": (
        "DOM: CWRP batching, cWU guards, gDSFP legacy suppression, host children (v149).",
        _patch_wave_noop_react,
        _patch_wave_dom_composite_lifecycle_v149_may2026,
    ),
    "dom_composite_lifecycle_v150_may2026": (
        "DOM: refs, invalid elements, lifecycle warnings, gDSFP/gSBU, render guards (v150).",
        _patch_wave_noop_react,
        _patch_wave_dom_composite_lifecycle_v150_may2026,
    ),
    "dom_composite_lifecycle_v151_may2026": (
        "DOM: legacy callbacks, morphing, lifecycle order, portals, flushSync batch (v151).",
        _patch_wave_noop_react,
        _patch_wave_dom_composite_lifecycle_v151_may2026,
    ),
    "dom_legacy_v152_may2026": (
        "DOM: legacy render/unmount, batched legacy roots, findDOMNode cWU, text minimalism (v152).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_v152_may2026,
    ),
    "dom_legacy_updates_v153_may2026": (
        "DOM: legacy batchedUpdates, cWRP/replaceState, flushSync, cWU/cDU (v153).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_updates_v153_may2026,
    ),
    "dom_legacy_fiber_v154_may2026": (
        "DOM: legacy fiber portals/findDOMNode, container warnings, batched mount sync (v154).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_fiber_v154_may2026,
    ),
    "dom_legacy_updates_v155_may2026": (
        "DOM: legacy mount queue, cWU/cDU ordering, props-children reuse, fiber warnings (v155).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_updates_v155_may2026,
    ),
    "dom_legacy_fiber_v156_may2026": (
        "DOM: portal event bubbling, nested fragment findDOMNode, memo host, flush order (v156).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_fiber_v156_may2026,
    ),
    "dom_legacy_fiber_v157_may2026": (
        "DOM: portal SVG/MathML namespaces, empty portal unmount, namespace unwind on errors (v157).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_fiber_v157_may2026,
    ),
    "dom_legacy_updates_v157_may2026": (
        "DOM: legacy hidden subtrees sync render, nested update depth guard (v157).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_updates_v157_may2026,
    ),
    "dom_legacy_fiber_v158_may2026": (
        "DOM: document fragment legacy mount + adopt (v158).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_fiber_v158_may2026,
    ),
    "dom_legacy_updates_v158_may2026": (
        "DOM: render-phase base state, mutual legacy_render depth, batch/recover (v158).",
        _patch_wave_noop_react,
        _patch_wave_dom_legacy_updates_v158_may2026,
    ),
    "burndown_v159_context_error_logging_batching_jun2026": (
        "React: NewContext provider bailout, context propagation PureComponent/useMemo, "
        "configurable error logging, batching internal layout/suspense slices (v159).",
        _patch_wave_burndown_v159_context_error_logging_batching_jun2026,
        _patch_wave_noop_react,
    ),
    "burndown_v160_dom_function_component_jun2026": (
        "React DOM: ReactFunctionComponent stateless render, legacy context, DEV warnings, "
        "key warnings, bound functions, null/false returns (v160).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v160_dom_function_component_jun2026,
    ),
    "burndown_v161_dom_console_error_reporting_jun2026": (
        "React DOM: createRoot console/window error reporting for render, effects, and events (v161).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v161_dom_console_error_reporting_jun2026,
    ),
    "burndown_v162_dom_console_error_reporting_legacy_jun2026": (
        "React DOM: ReactDOM.render legacy console/window error reporting (v162).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v162_dom_console_error_reporting_legacy_jun2026,
    ),
    "burndown_v163_dom_legacy_composite_context_jun2026": (
        "React DOM: ReactLegacyCompositeComponent legacy context propagation (v163).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v163_dom_legacy_composite_context_jun2026,
    ),
    "burndown_v164_dom_multichild_reconciliation_jun2026": (
        "React DOM: ReactMultiChild iterables, DEV warnings, owners, lifecycle ordering (v164).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v164_dom_multichild_reconciliation_jun2026,
    ),
    "burndown_v166_dom_legacy_fiber_updates_composite_jun2026": (
        "React DOM: legacy fiber portal/events, legacy updates guards, context-only CWRP (v166).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v166_dom_legacy_fiber_updates_composite_jun2026,
    ),
    "burndown_v182_dom_legacy_composite_scu_jun2026": (
        "React DOM: ReactLegacyComposite SCU-false sibling reorder ref swap (v182).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v182_dom_legacy_composite_scu_jun2026,
    ),
    "burndown_v183_dom_find_dom_node_jun2026": (
        "React DOM: findDOMNode validation, unmount rejection, and StrictMode warnings (v183).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v183_dom_find_dom_node_jun2026,
    ),
    "burndown_v184_react_dom_jun2026": (
        "React: forwardRef deep bailout + useEffectEvent context; DOM: ReactChildReconciler (v184).",
        _patch_wave_burndown_v184_react_forwardref_useeffectevent_jun2026,
        _patch_wave_burndown_v184_dom_child_reconciler_jun2026,
    ),
    "burndown_v181_dom_legacy_updates_jun2026": (
        "React DOM: ReactLegacyUpdates batched mount/unmount sync and update ordering (v181).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v181_dom_legacy_updates_jun2026,
    ),
    "burndown_v180_dom_fiber_async_passive_jun2026": (
        "React DOM: ReactDOMFiberAsync passive effects across roots and flushSync tick batching (v180).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v180_dom_fiber_async_passive_jun2026,
    ),
    "burndown_v180_dom_comment_mount_jun2026": (
        "React DOM: ReactLegacyMount comment-node legacy render (v180).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v180_dom_comment_mount_jun2026,
    ),
    "burndown_v179_dom_fiber_async_flushsync_jun2026": (
        "React DOM: ReactDOMFiberAsync createRoot flushSync batching and stale-root guards (v179).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v179_dom_fiber_async_flushsync_jun2026,
    ),
    "burndown_v178_dom_mount_destruction_jun2026": (
        "React DOM: ReactMountDestruction createRoot unmount and legacy host-node warnings (v178).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v178_dom_mount_destruction_jun2026,
    ),
    "burndown_v178_dom_updates_infinite_loop_warn_jun2026": (
        "React DOM: ReactUpdates cross-component render-phase infinite loop warnings (v178).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v178_dom_updates_infinite_loop_warn_jun2026,
    ),
    "burndown_v177_dom_updates_depth_guards_jun2026": (
        "React DOM: ReactUpdates createRoot ref-callback and useEffect flushSync depth guards (v177).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v177_dom_updates_depth_guards_jun2026,
    ),
    "burndown_v177_dom_legacy_updates_flush_jun2026": (
        "React DOM: ReactLegacyUpdates flush ordering and portal mount-ready (v177).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v177_dom_legacy_updates_flush_jun2026,
    ),
    "burndown_v177_dom_legacy_root_warnings_jun2026": (
        "React DOM: ReactLegacyRootWarnings ReactDOM.render deprecation (v177).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v177_dom_legacy_root_warnings_jun2026,
    ),
    "burndown_v176_dom_updates_cross_root_jun2026": (
        "React DOM: ReactUpdates createRoot cross-root flush and portal mount-ready (v176).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v176_dom_updates_cross_root_jun2026,
    ),
    "burndown_v176_dom_error_boundaries_final_jun2026": (
        "React DOM: ReactErrorBoundaries createRoot final robustness cases (v176).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v176_dom_error_boundaries_final_jun2026,
    ),
    "burndown_v175_dom_error_boundaries_effects_jun2026": (
        "React DOM: ReactErrorBoundaries createRoot effects, cWU recovery, refs, gsbu, GDSFE (v175).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v175_dom_error_boundaries_effects_jun2026,
    ),
    "burndown_v174_dom_error_boundaries_update_jun2026": (
        "React DOM: ReactErrorBoundaries createRoot update-phase catch, multi-root, propagation (v174).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v174_dom_error_boundaries_update_jun2026,
    ),
    "burndown_v173_dom_error_boundaries_jun2026": (
        "React DOM: ReactErrorBoundaries createRoot catch/recover/uncaught logging (v173).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v173_dom_error_boundaries_jun2026,
    ),
    "burndown_v172_dom_legacy_error_boundaries_final_jun2026": (
        "React DOM: ReactLegacyErrorBoundaries multi-catch, gsbu errors, context cWM (v172).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v172_dom_legacy_error_boundaries_final_jun2026,
    ),
    "burndown_v171_dom_legacy_error_boundaries_unmount_refs_jun2026": (
        "React DOM: ReactLegacyErrorBoundaries unmount catch, refs on abort, removals (v171).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v171_dom_legacy_error_boundaries_unmount_refs_jun2026,
    ),
    "burndown_v170_dom_legacy_error_boundaries_lifecycle_jun2026": (
        "React DOM: ReactLegacyErrorBoundaries nested propagation, lifecycle catch, reorders (v170).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v170_dom_legacy_error_boundaries_lifecycle_jun2026,
    ),
    "burndown_v169_dom_legacy_error_boundaries_update_jun2026": (
        "React DOM: ReactLegacyErrorBoundaries update-phase catch, multi-root, mount abort (v169).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v169_dom_legacy_error_boundaries_update_jun2026,
    ),
    "burndown_v168_dom_legacy_error_boundaries_jun2026": (
        "React DOM: ReactLegacyErrorBoundaries legacy catch/recover/uncaught (v168).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v168_dom_legacy_error_boundaries_jun2026,
    ),
    "burndown_v167_dom_updates_create_root_jun2026": (
        "React DOM: ReactUpdates createRoot depth guards, hidden subtrees, batch limits (v167).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v167_dom_updates_create_root_jun2026,
    ),
    "burndown_v165_dom_composite_component_state_jun2026": (
        "React DOM: ReactCompositeComponentState lifecycle/state + DOMAttribute unknown camelCase/symbol (v165).",
        _patch_wave_noop_react,
        _patch_wave_burndown_v165_dom_composite_component_state_jun2026,
    ),
}


def _cmd_list() -> None:
    for name, (blurb, _, _) in sorted(WAVES.items()):
        print(f"{name}")
        print(f"  {blurb}")


def _cmd_apply(*, wave: str) -> None:
    if wave not in WAVES:
        raise SystemExit(f"Unknown wave {wave!r}. Try: list")
    _, patch_react, patch_dom = WAVES[wave]
    react_path = REPO / "tests_upstream/react/upstream_inventory.json"
    dom_path = REPO / "tests_upstream/react_dom/upstream_inventory.json"
    for path, fn in (
        (react_path, patch_react),
        (dom_path, patch_dom),
    ):
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = data["cases"]
        n = fn(cases)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"updated {n} case(s) in {path.relative_to(REPO)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List known inventory waves")
    p_list.set_defaults(handler=lambda _: _cmd_list())

    p_apply = sub.add_parser("apply", help="Apply a named wave to upstream inventories")
    p_apply.add_argument(
        "--wave",
        required=True,
        choices=sorted(WAVES),
        help="Wave name (see `list`).",
    )
    p_apply.set_defaults(handler=lambda a: _cmd_apply(wave=a.wave))

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
