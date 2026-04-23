# ryact-native

[![PyPI](https://img.shields.io/pypi/v/ryact-native.svg)](https://pypi.org/project/ryact-native/)
[![Python](https://img.shields.io/pypi/pyversions/ryact-native.svg)](https://pypi.org/project/ryact-native/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Early scaffold for a **React Native–style renderer** in Python.

For now, it renders into a deterministic in-memory native tree so tests can assert on output.

## Install

```bash
pip install ryact-native
```

## Tiny example (render)

```python
from ryact import create_element
from ryact_native import NativeContainer, create_root

container = NativeContainer()
root = create_root(container)
root.render(create_element("View", {"testID": "root"}, "hello"))
```

## Notes

- This package is a scaffold; the long-term goal is parity with React Native host semantics as tests are ported.

