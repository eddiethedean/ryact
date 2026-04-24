## Host harnesses guide

`schedulyr` contains multiple “host harnesses” that mirror upstream Scheduler behavior under different host environments. These are primarily used by translated upstream tests, but they can also be useful for deterministic host-loop simulations.

### Browser-style host (MessageChannel)
- **Harness**: `schedulyr.BrowserSchedulerHarness`
- **Runtime**: `schedulyr.MockBrowserRuntime`
- Shape: mirrors `describe('SchedulerBrowser')` in upstream `Scheduler-test.js`.

### `setImmediate` host fork
- **Harness**: `schedulyr.SetImmediateSchedulerHarness`
- **Runtime**: `schedulyr.SetImmediateMockRuntime`

### `setTimeout(0)` host fork
- **Harness**: `schedulyr.SetTimeoutSchedulerHarness`
- Runtime is a function interface; the production host loop uses `schedulyr.SetTimeoutMockRuntime`.

### `postTask` host fork
- **Harness**: `schedulyr.PostTaskSchedulerHarness`
- **Runtime**: `schedulyr.PostTaskMockRuntime`

### Production DOM host selection wrapper
- **Harness**: `schedulyr.ProductionDOMHarness`
- Selection order: `setImmediate` → `MessageChannel` → `setTimeout(0)` (mirrors upstream).

