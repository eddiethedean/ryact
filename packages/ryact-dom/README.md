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

## Optional `schedulyr` integration (deferred flush)

Pass a **`schedulyr.Scheduler`** into **`create_root`** when you want reconciler commits to run through the scheduler (Milestone 3 wiring). **`root.render(...)`** then **queues** the commit; call **`scheduler.run_until_idle()`** (and advance fake time if you inject **`FakeTimers`**) to apply updates to the container.

```python
from schedulyr import Scheduler
from ryact import create_element
from ryact_dom import create_root
from ryact_dom.dom import Container

sched = Scheduler()
root = create_root(Container(), scheduler=sched)
root.render(create_element("div", None, "hi"))
sched.run_until_idle()
```

With **`scheduler=None`** (the default), behavior matches the synchronous example above (**`perform_work`** runs inside **`render`**).

## Tiny example (server render)

```python
from ryact import create_element
from ryact_dom import render_to_string

html = render_to_string(create_element("div", {"id": "x"}, "hi"))
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/react-dom`

