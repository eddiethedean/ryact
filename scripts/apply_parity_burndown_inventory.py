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
