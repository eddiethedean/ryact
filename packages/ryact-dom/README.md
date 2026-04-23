# ryact-dom

[![PyPI](https://img.shields.io/pypi/v/ryact-dom.svg)](https://pypi.org/project/ryact-dom/)
[![Python](https://img.shields.io/pypi/pyversions/ryact-dom.svg)](https://pypi.org/project/ryact-dom/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **`react-dom`** (parity target: `facebook/react` `packages/react-dom`).

The renderer targets a deterministic in-Python DOM abstraction so behavior can be asserted in pytest.

## Install

```bash
pip install ryact-dom
```

## Tiny example (render)

```python
from ryact import create_element
from ryact_dom import create_root
from ryact_dom.dom import Container

container = Container()
root = create_root(container)
root.render(create_element("div", {"id": "a"}, "hello"))
```

## Tiny example (server render)

```python
from ryact import create_element
from ryact_dom import render_to_string

html = render_to_string(create_element("div", {"id": "x"}, "hi"))
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/react-dom`

