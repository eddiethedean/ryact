# Parity burn-down: process + current status

This repo drives React/ReactDOM parity by translating upstream Jest tests into pytest and
gating “implemented” behavior via a **manifest** + **inventory** workflow.

## Glossary (what each file means)

- **Upstream inventories**
  - `tests_upstream/react/upstream_inventory.json`
  - `tests_upstream/react_dom/upstream_inventory.json`
  - **Purpose**: a structured checklist of upstream Jest test cases.
  - **Fields that matter**:
    - `status`: `pending` | `implemented` | `non_goal`
    - `manifest_id`: required when `implemented`
    - `python_test`: required when `implemented`
    - `non_goal_rationale`: required when `non_goal`

- **Manifest gate**
  - `tests_upstream/MANIFEST.json`
  - **Purpose**: the allowlist of upstream cases we claim are implemented.
  - **Rule**: every `manifest_id` must correspond to a real translated pytest test, and
    must only represent behavior that is actually implemented (CI enforces this).

- **Wave applier**
  - `scripts/apply_parity_burndown_inventory.py`
  - **Purpose**: codifies small, reviewable “waves” that flip inventory rows from
    `pending` → `implemented` (or `non_goal`) in a repeatable way.
  - **Rule**: waves only flip rows that are still `pending`, so they can be re-run safely.

- **Gates / schema checks**
  - `tests_upstream/react/test_upstream_inventory_schema.py`
  - `tests_upstream/react_dom/test_react_dom_upstream_inventory_schema.py`
  - `tests_upstream/test_manifest_gate.py`

## The burn-down loop (what we do each wave)

### 1) Re-measure what’s pending

Run:

```bash
uv run python scripts/report_upstream_inventory.py --top 40
```

This prints totals and the largest remaining `upstream_path` buckets. We pick work from
still-`pending` rows, preferring “high leverage” buckets that match current harness
capabilities (e.g. single-root incremental error-handling, DOM property operations).

### 2) Translate/select upstream cases into tight pytest slices

For each chosen inventory row:

- Add a translated pytest module under `tests_upstream/react/` or `tests_upstream/react_dom/`.
- Keep modules tight and reviewable: typically **one manifest id per row**, except for
  small related DOM assertions that can share a module.

### 3) Implement the minimal runtime behavior needed

Depending on the slice, changes usually land in one of:

- `packages/ryact/src/ryact/` (core reconciler semantics)
- `packages/ryact-testkit/` (noop renderer harness + deterministic host assertions)
- `packages/ryact-dom/src/ryact_dom/` (DOM props normalization + SSR serialization)

### 4) Add MANIFEST entries

Append the new `manifest_id` entries to `tests_upstream/MANIFEST.json`.

The manifest is the “we claim this is implemented” contract, so each new entry must map
to a real translated pytest test (and should be directly traceable to an upstream `it(...)`).

### 5) Flip the corresponding inventory rows (tight flips)

In the relevant upstream inventory JSON, flip only the chosen rows:

- `status: implemented`
- `manifest_id: <new id>`
- `python_test: <new test module>`
- `non_goal_rationale: null`

**Important**: don’t flip a whole upstream file unless we explicitly decide it’s `non_goal`.
This is what keeps the process honest and incremental.

### 6) Register a wave (optional but preferred)

Add a new wave entry to `scripts/apply_parity_burndown_inventory.py` so the flips are
repeatable (and future re-measurements remain consistent).

Smoke check:

```bash
uv run python scripts/apply_parity_burndown_inventory.py apply --wave <wave_name>
```

After you’ve manually flipped rows, re-applying the wave should report **0 updates**.

### 7) Verify (tests + lint)

Run at minimum:

```bash
uv run pytest \
  tests_upstream/react/test_upstream_inventory_schema.py \
  tests_upstream/react_dom/test_react_dom_upstream_inventory_schema.py \
  tests_upstream/test_manifest_gate.py

uv run ruff check <touched files>
```

If core reconciler behavior changed, it’s common to run the full translated suites:

```bash
uv run pytest tests_upstream/react/ tests_upstream/react_dom/
```

## Where we currently stand (latest re-measure)

From `uv run python scripts/report_upstream_inventory.py --top 25`:

### React (`tests_upstream/react/upstream_inventory.json`)

- **total**: 1336
- **implemented**: 362
- **pending**: 640
- **non_goal**: 334

Largest remaining pending buckets (top items):

- `ReactHooksWithNoopRenderer-test.js`: 76 pending
- `ReactUse-test.js`: 48 pending
- `ReactLazy-test.internal.js`: 40 pending
- `ReactHooks-test.internal.js`: 35 pending
- `ReactProfiler-test.internal.js`: 34 pending
- `createReactClassIntegration-test.js`: 28 pending
- `ReactAsyncActions-test.js`: 26 pending
- `ReactTransitionTracing-test.js`: 22 pending
- `ReactJSXTransformIntegration-test.js`: 19 pending
- `ReactStrictMode-test.js`: 18 pending
- `useEffectEvent-test.js`: 17 pending
- `ReactSuspenseEffectsSemantics-test.js`: 12 pending

Notes on prioritization:

- The process intentionally **defers** some large buckets (e.g. `ReactUse`,
  `ReactTransitionTracing`) when they depend on hooks/transition-tracing surfaces not yet
  modeled in `ryact` + `ryact-testkit`.
- We prefer slices that are mostly assertion-only with current harness support (e.g.
  incremental error-handling, small Suspense semantics snapshots, element validation).

### ReactDOM (`tests_upstream/react_dom/upstream_inventory.json`)

- **total**: 2234
- **implemented**: 54
- **pending**: 2180
- **non_goal**: 0

Largest remaining pending buckets (top items):

- `ReactDOMFizzServer-test.js`: 156 pending
- `ReactDOMComponent-test.js`: 131 pending
- `ReactDOMFloat-test.js`: 125 pending
- `ReactDOMInput-test.js`: 124 pending
- `ReactDOMEventPropagation-test.js`: 91 pending
- `ReactDOMFragmentRefs-test.js` / `ReactDOMSelect-test.js`: 61 pending each
- `DOMPropertyOperations-test.js`: 36 pending

Notes on prioritization:

- DOM parity is still very early relative to inventory size; we typically pick low-risk
  property normalization / serialization slices first, before attempting server streaming
  (`Fizz`) or large event systems.

## Latest completed wave

The most recent registered wave is:

- `burndown_v50_class_and_topleveltext_dom_property_ops_apr2026` in
  `scripts/apply_parity_burndown_inventory.py`

It covered:

- **React (manifest bookkeeping + tests)**: `ReactClassComponentPropResolution` (defaultProps + ref
  before cWM/cDM), `ReactClassSetStateCallback` (2nd arg fires once), `ReactTopLevelText` (string /
  number / large int from a function component via the noop renderer).
- **ReactDOM**: `DOMPropertyOperations` “custom component tag” (`my-icon` + `size`), and “special
  properties” for `input` when `value` is dropped (attribute retained; DEV warning). Incremental
  host commit logic lives in
  `packages/ryact-dom/src/ryact_dom/root.py`.

Prior milestone waves (for example the noop hooks pilot `burndown_v49_react_hooks_noop_renderer_pilot_apr2026`)
remain available via `apply ... list`.

## Practical “what to do next”

If you’re starting the next wave after v50, the highest-signal next steps are:

- Continue **ReactHooksWithNoopRenderer** slices that match the current `ryact-testkit` harness, or
  take small cases from `ReactSuspenseEffectsSemantics-test.js` / `ReactJSXTransformIntegration-test.js`
  when the reconciler and harness can assert deterministically.
- For **ReactDOM**, continue low-risk `DOMPropertyOperations` / `ReactDOMComponent` rows before
  Fizz, selective hydration, or full event propagation.

