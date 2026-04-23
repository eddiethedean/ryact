# ryact-testkit roadmap

Goal: provide shared utilities so translated upstream tests stay readable, deterministic, and consistent.

## Milestone 0 — Common primitives
- Fake timers integrated with `schedulyr`.
- `act()` that deterministically flushes:
  - scheduled callbacks
  - pending renders/commits
  - passive/layout effects
- Warning/error capture utilities that match upstream expectations.

## Milestone 1 — Renderer helpers
- Deterministic “no-op” host helpers for reconciler-focused tests (no DOM/native needed).
- Tree serialization helpers for stable assertions/snapshots.

## Milestone 2 — Drift + manifest tooling
- Expand `scripts/check_upstream_drift.py` into:
  - a manifest generator/update tool
  - upstream test discovery helpers
  - drift checks in CI against a pinned upstream commit/tag

## “done” definition
- Translated tests rely on testkit instead of ad-hoc per-test helpers.
- Updating upstream test references is automated and low-friction.

