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

R_CONTEXT_DEFER = (
    "Deferred: New Context API / propagation / bailout semantics beyond the current minimal "
    "create_context helper; revisit with dedicated translated slices."
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
            simple_id = (
                "react.ReactIncremental-test.reactincremental.should_render_a_simple_component"
            )
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "self_and_source_are_treated_as_normal_props",
        "react.elementValidator.selfSourceAsProps",
        "tests_upstream/react/test_element_validator_self_source_props.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "calls_callback_after_update_is_flushed",
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_fragments_with_illegal_attributes",
        "react.elementValidator.fragmentIllegalProps",
        "tests_upstream/react/test_element_validator_fragment_illegal_props.py",
    ),
    (
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_update_child_nodes_of_a_fragment",
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
        "react.ReactIncrementalSideEffects-test.reactincrementalsideeffects."
        "can_update_child_nodes_of_a_host_instance",
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "warns_for_keys_with_component_stack_info",
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_blow_up_with_inlined_children",
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
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "removes_custom_attributes.9a20fe45",
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "should_not_enumerate_enumerable_numbers_4776",
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
        "react.ReactElementValidator-test.internal.reactelementvalidator."
        "does_not_call_lazy_initializers_eagerly",
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
            "react_dom.ReactDOMComponent-test.reactdomcomponent.custom_attributes."
            "warns_on_nan_attributes.d9c72853",
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
            "react_dom.ReactDOMComponent-test.reactdomcomponent.mountcomponent."
            "should_allow_html_null.19e208e1",
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
        (
            "Deferred: depends on a host config that can throw 'Error in host config.' "
            "during reconciliation/commit."
        ),
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
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "schedules_and_flushes_deferred_work",
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
        "react.ReactIncrementalScheduling-test.reactincrementalscheduling."
        "performs_task_work_even_after_time_runs_out",
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
    non_goal_rationale = (
        "Deferred: requires multi-root noop renderer + cross-root scheduling/flush semantics."
    )
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
        "react_dom.ReactMultiChild-test.reactmultichild.reconciliation."
        "should_update_children_when_possible.54b20ccf",
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
        "react.ReactHooks-test.internal.reacthooks."
        "warns_if_switching_from_dependencies_to_no_dependencies",
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
        "react.ReactActWarnings-test.act_warnings."
        "warns_about_unwrapped_updates_only_if_environment_flag_is_enabled",
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


WAVES: dict[str, tuple[str, WaveReact, WaveDom]] = {
    "initial_phase_a_b_d": (
        "First burn-down wave: close several high-pending core files + one DOM boolean slice.",
        _patch_wave_initial_react_cases,
        _patch_wave_initial_dom_cases,
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
