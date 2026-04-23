# ryact

[![PyPI](https://img.shields.io/pypi/v/ryact.svg)](https://pypi.org/project/ryact/)
[![Python](https://img.shields.io/pypi/pyversions/ryact.svg)](https://pypi.org/project/ryact/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **React core** semantics (parity target: `facebook/react` `packages/react`).

This is intentionally incomplete early on; parity is driven by translated upstream tests in this repo.

## Install

```bash
pip install ryact
```

## Tiny example (elements)

```python
from ryact import create_element

el = create_element("div", {"id": "root"}, "hello")
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/react`

