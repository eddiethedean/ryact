/* eslint-disable no-underscore-dangle */
// Curated upstream scenario recorder for Milestone 23.
//
// This script is intentionally minimal and relies on a local facebook/react checkout
// with dependencies installed (`yarn install`).
//
// It records a small set of scheduler scenarios into a stable JSON shape that can be
// cross-compared with the Python port’s scenario outputs.

'use strict';

const fs = require('fs');
const path = require('path');
const Module = require('module');

function parseArgs(argv) {
  const out = {reactPath: null, scenario: []};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--react-path') {
      out.reactPath = argv[++i];
      continue;
    }
    if (a === '--scenario') {
      out.scenario.push(argv[++i]);
      continue;
    }
  }
  if (!out.reactPath) {
    throw new Error('Missing --react-path');
  }
  return out;
}

function installReactJSTransform(reactPath) {
  const preprocessorPath = path.join(reactPath, 'scripts', 'jest', 'preprocessor.js');
  // The preprocessor expects to resolve deps relative to the upstream checkout.
  const preprocessor = require(preprocessorPath);

  const defaultLoader = require.extensions['.js'];
  require.extensions['.js'] = function (module, filename) {
    // Only transform upstream checkout files; delegate everything else.
    if (!filename.startsWith(reactPath)) {
      return defaultLoader(module, filename);
    }
    const src = fs.readFileSync(filename, 'utf8');
    const res = preprocessor.process(src, filename);
    module._compile(res.code, filename);
  };
}

function makePerformance() {
  let now = 0;
  return {
    now: () => now,
    _advance(ms) {
      now += ms;
    },
    _reset() {
      now = 0;
    },
  };
}

function makeMessageChannelHost(log) {
  const perf = makePerformance();
  let onMessage = null;
  let pending = false;

  global.performance = perf;
  global.MessageChannel = function MessageChannel() {
    const port1 = {};
    Object.defineProperty(port1, 'onmessage', {
      get() {
        return onMessage;
      },
      set(fn) {
        onMessage = fn;
      },
    });
    const port2 = {
      postMessage() {
        log.push('Post Message');
        pending = true;
      },
    };
    return {port1, port2};
  };
  global.setImmediate = undefined;

  const setTimeoutQueue = [];
  global.setTimeout = (cb, _delay) => {
    log.push('Set Timer');
    setTimeoutQueue.push(cb);
    return setTimeoutQueue.length;
  };
  global.clearTimeout = (_id) => {};

  return {
    perf,
    fireMessageEvent() {
      if (!pending) throw new Error('No message was scheduled');
      pending = false;
      log.push('Message Event');
      if (onMessage) onMessage({data: null});
    },
    hasPending() {
      return pending || setTimeoutQueue.length > 0;
    },
    fireSetTimeout() {
      if (setTimeoutQueue.length === 0) throw new Error('No setTimeout was scheduled');
      const cb = setTimeoutQueue.shift();
      log.push('SetTimeout Callback');
      cb();
    },
  };
}

function makeSetImmediateHost(log) {
  const perf = makePerformance();
  global.performance = perf;
  global.MessageChannel = undefined;

  let pending = null;
  global.setImmediate = (cb) => {
    log.push('Set Immediate');
    pending = cb;
    return 1;
  };
  global.clearImmediate = (_id) => {};

  const setTimeoutQueue = [];
  global.setTimeout = (cb, _delay) => {
    log.push('Set Timer');
    setTimeoutQueue.push(cb);
    return setTimeoutQueue.length;
  };
  global.clearTimeout = (_id) => {};

  return {
    perf,
    fireImmediate() {
      if (!pending) throw new Error('No setImmediate was scheduled');
      const cb = pending;
      pending = null;
      log.push('setImmediate Callback');
      cb();
    },
    hasPending() {
      return pending != null || setTimeoutQueue.length > 0;
    },
    fireSetTimeout() {
      if (setTimeoutQueue.length === 0) throw new Error('No setTimeout was scheduled');
      const cb = setTimeoutQueue.shift();
      log.push('SetTimeout Callback');
      cb();
    },
  };
}

function makeSetTimeoutHost(log) {
  const perf = makePerformance();
  global.performance = perf;
  global.MessageChannel = undefined;
  global.setImmediate = undefined;

  const q = [];
  global.setTimeout = (cb, _delay) => {
    log.push('Set Timer');
    q.push(cb);
    return q.length;
  };
  global.clearTimeout = (_id) => {};

  return {
    perf,
    hasPending() {
      return q.length > 0;
    },
    fireSetTimeout() {
      if (q.length === 0) throw new Error('No setTimeout was scheduled');
      const cb = q.shift();
      log.push('SetTimeout Callback');
      cb();
    },
  };
}

function requireFresh(modulePath) {
  delete require.cache[require.resolve(modulePath)];
  return require(modulePath);
}

function drainHost(host, log) {
  // Prefer immediate/message events if present; otherwise setTimeout.
  // The scheduler schedules a next tick if more work remains.
  let guard = 0;
  while (host.hasPending()) {
    if (++guard > 1000) throw new Error('Draining exceeded guard');
    if (host.fireImmediate) host.fireImmediate();
    else if (host.fireMessageEvent) host.fireMessageEvent();
    else host.fireSetTimeout();
    // Scheduler may not schedule another tick; loop checks `hasPending`.
  }
  return log;
}

function runScenarios(reactPath, selected) {
  const forkPath = path.join(
    reactPath,
    'packages',
    'scheduler',
    'src',
    'forks',
    'Scheduler.js'
  );

  const all = {
    'production_dom.driver_selection.set_immediate': () => {
      const log = [];
      const host = makeSetImmediateHost(log);
      const S = requireFresh(forkPath);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {});
      drainHost(host, log);
      return log;
    },
    'production_dom.driver_selection.message_channel': () => {
      const log = [];
      const host = makeMessageChannelHost(log);
      const S = requireFresh(forkPath);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {});
      drainHost(host, log);
      return log;
    },
    'production_dom.driver_selection.set_timeout': () => {
      const log = [];
      const host = makeSetTimeoutHost(log);
      const S = requireFresh(forkPath);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {});
      drainHost(host, log);
      return log;
    },
    'production_dom.continuation_forces_host_yield': () => {
      const log = [];
      const host = makeMessageChannelHost(log);
      const S = requireFresh(forkPath);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {
        log.push('Callback A');
        return () => log.push('Callback B');
      });
      drainHost(host, log);
      return log;
    },
    'production_dom.request_paint_yields': () => {
      const log = [];
      const host = makeMessageChannelHost(log);
      const S = requireFresh(forkPath);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {
        log.push('Callback A');
        S.unstable_requestPaint();
      });
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {
        log.push('Callback B');
      });
      drainHost(host, log);
      return log;
    },
    'browser.should_yield.force_frame_rate': () => {
      const log = [];
      const host = makeMessageChannelHost(log);
      const S = requireFresh(forkPath);
      S.unstable_forceFrameRate(60);
      S.unstable_scheduleCallback(S.unstable_NormalPriority, () => {
        // Advance time until shouldYield flips.
        while (!S.unstable_shouldYield()) {
          host.perf._advance(1);
        }
        log.push(`Yield at ${Math.trunc(host.perf.now())}ms`);
      });
      drainHost(host, log);
      return log;
    },
  };

  const names = selected.length ? selected : Object.keys(all);
  const results = {};
  for (const name of names) {
    if (!all[name]) throw new Error(`Unknown scenario: ${name}`);
    results[name] = {name, events: all[name]()};
  }
  return {scenarios: names, results};
}

function main() {
  const ns = parseArgs(process.argv.slice(2));
  const reactPath = path.resolve(ns.reactPath);

  // Make upstream checkout discoverable for require() resolution.
  process.chdir(reactPath);
  Module._initPaths();

  installReactJSTransform(reactPath);
  const payload = runScenarios(reactPath, ns.scenario);
  process.stdout.write(JSON.stringify(payload, null, 2) + '\n');
}

main();

