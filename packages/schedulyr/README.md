# schedulyr

[![PyPI](https://img.shields.io/pypi/v/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![Python](https://img.shields.io/pypi/pyversions/schedulyr.svg)](https://pypi.org/project/schedulyr/)
[![CI](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/ryact/actions/workflows/ci.yml)

Python port of **React Scheduler** semantics (parity target: `facebook/react` `packages/scheduler`).

## Install

```bash
pip install schedulyr
```

## Tiny example

```python
from schedulyr import NORMAL_PRIORITY, Scheduler

s = Scheduler()
s.schedule_callback(NORMAL_PRIORITY, lambda: print("work"), delay_ms=0)
s.run_until_idle()
```

## Source of truth

- Upstream: `https://github.com/facebook/react/tree/main/packages/scheduler`

