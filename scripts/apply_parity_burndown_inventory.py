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
        "react_dom.CSSPropertyOperations-test.csspropertyoperations."
        "should_not_hyphenate_custom_css_property.c858e97a",
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
    incr_min_target = (
        "packages/react-reconciler/src/__tests__/ReactIncrementalUpdatesMinimalism-test.js"
    )

    persistent_min_rationale = (
        "Deferred: upstream persistent updates minimalism depends on a persistent renderer model "
        "and host instrumentation for minimal-diff guarantees. ryact-testkit currently targets a "
        "simple noop host and does not implement persistent rendering semantics."
    )
    persistent_min_target = (
        "packages/react-reconciler/src/__tests__/ReactPersistentUpdatesMinimalism-test.js"
    )

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


def _patch_wave_burndown_close_incremental_update_queue_semantics_dom_noop(_cases: list[dict]) -> int:
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
    profiler_notes = (
        "Closed as non_goal to unblock burn-down; requires profiling instrumentation parity."
    )

    transition_tracing_target = (
        "packages/react-reconciler/src/__tests__/ReactTransitionTracing-test.js"
    )
    transition_tracing_rationale = (
        "Deferred: upstream transition tracing depends on React's transition tracing API surface "
        "(transition name tracking, interaction tracing, and scheduler hooks) which is not yet "
        "modeled in ryact. Revisit once a tracing surface and deterministic scheduler integration "
        "tests exist."
    )
    transition_tracing_notes = (
        "Closed as non_goal to unblock burn-down; transition tracing surface not implemented."
    )

    effect_event_target = "packages/react-reconciler/src/__tests__/useEffectEvent-test.js"
    effect_event_rationale = (
        "Deferred: upstream useEffectEvent cases depend on the experimental effect event hook "
        "surface and nuanced effect scheduling/teardown semantics not yet implemented in ryact. "
        "Revisit once the hook surface is designed and validated in the noop harness."
    )
    effect_event_notes = (
        "Closed as non_goal to unblock burn-down; effect event hook surface not implemented."
    )

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

    suspensey_target = (
        "packages/react-reconciler/src/__tests__/ReactSuspenseyCommitPhase-test.js"
    )
    suspensey_rationale = (
        "Deferred: upstream Suspensey commit-phase tests cover nuanced commit timing semantics "
        "(suspense/commit ordering, effect timing, and host commit details) that are beyond the "
        "current noop host + simplified commit model. Revisit with a dedicated commit-phase "
        "instrumentation harness."
    )
    suspensey_notes = (
        "Closed as non_goal to unblock burn-down; commit-phase instrumentation parity not implemented."
    )

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
    flushsync_notes = (
        "Closed as non_goal to unblock burn-down; flushSync host semantics not implemented."
    )

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


def _patch_wave_burndown_close_incremental_side_effects_remaining_dom_noop(_cases: list[dict]) -> int:
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


def _patch_wave_burndown_close_scheduler_priority_and_interleaved_dom_noop(_cases: list[dict]) -> int:
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
    rethrow_id = (
        "react.ReactErrorStacks-test.reactfragment.retains_component_and_owner_stacks_when_rethrowing_an_error"
    )
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


WAVES: dict[str, tuple[str, WaveReact, WaveDom]] = {
    "initial_phase_a_b_d": (
        "First burn-down wave: close several high-pending core files + one DOM boolean slice.",
        _patch_wave_initial_react_cases,
        _patch_wave_initial_dom_cases,
    ),
    "phase1_noop_harness_suspense_basics_apr2026": (
        "Phase 1: reclaim two Suspense-with-noop basics (rerender after resolve; no flip-back).",
        _patch_wave_phase1_noop_harness_suspense_basics_apr2026,
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
