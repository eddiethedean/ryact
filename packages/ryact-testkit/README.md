# ryact-testkit

[![PyPI](https://img.shields.io/pypi/v/ryact-testkit.svg)](https://pypi.org/project/ryact-testkit/)
[![Python](https://img.shields.io/pypi/pyversions/ryact-testkit.svg)](https://pypi.org/project/ryact-testkit/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Shared helpers used by translated upstream tests in this repo.

## Install

```bash
pip install ryact-testkit
```

With optional **JavaScript** execution (via [js2py](https://pypi.org/project/Js2Py/)) for snippets while porting upstream tests:

```bash
pip install 'ryact-testkit[javascript]'
```

## Contents (early)

- `FakeTimers`: deterministic fake time for scheduler tests
- `act()`: minimal flush helper
- `WarningCapture`: capture warnings asserted by tests
- `eval_js`, `JsContext`, `is_javascript_runtime_available`: optional JS runner (`[javascript]` extra)
- `create_noop_root()`: deterministic no-op host for reconciler-focused tests
  - supports a commit snapshot log (`container.commits` / `container.last_committed`)
  - supports a deterministic host op log (`root.get_ops()` / `root.clear_ops()`) for keyed insert/move/delete assertions

