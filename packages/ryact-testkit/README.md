# ryact-testkit

[![PyPI](https://img.shields.io/pypi/v/ryact-testkit.svg)](https://pypi.org/project/ryact-testkit/)
[![Python](https://img.shields.io/pypi/pyversions/ryact-testkit.svg)](https://pypi.org/project/ryact-testkit/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Shared helpers used by translated upstream tests in this repo.

## Install

```bash
pip install ryact-testkit
```

## Contents (early)

- `FakeTimers`: deterministic fake time for scheduler tests
- `act()`: minimal flush helper
- `WarningCapture`: capture warnings asserted by tests

