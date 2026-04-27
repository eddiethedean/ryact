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


WaveReact = Callable[[list[dict]], int]
WaveDom = Callable[[list[dict]], int]

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
