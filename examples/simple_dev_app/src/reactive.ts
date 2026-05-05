/** Minimal subscriptions — enough to drive DOM updates without a framework. */

export type Unsubscribe = () => void;

export function createSignal<T>(initial: T) {
  let value = initial;
  const subs = new Set<() => void>();

  return {
    read: (): T => value,
    write: (next: T) => {
      value = next;
      for (const fn of subs) fn();
    },
    update: (fn: (prev: T) => T) => {
      value = fn(value);
      for (const s of subs) s();
    },
    subscribe: (fn: () => void): Unsubscribe => {
      subs.add(fn);
      return () => {
        subs.delete(fn);
      };
    },
  };
}
