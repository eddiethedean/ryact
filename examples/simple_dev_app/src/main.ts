import { createSignal } from "./reactive";

/**
 * Full DOM rebuild on every keystroke destroys `<input>` nodes and kills focus.
 * We mount once, then only patch text/list nodes. Typing stays smooth.
 */

const root = document.querySelector("#root");
if (!root) throw new Error("#root missing");

const count = createSignal(0);
const todos = createSignal<string[]>([]);

type PropVal = string | boolean | undefined | ((e: Event) => void);

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Record<string, PropVal> | null,
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === undefined) continue;
      if (k === "class") node.className = String(v);
      else if (k.startsWith("on") && typeof v === "function") {
        const ev = k.slice(2).toLowerCase();
        node.addEventListener(ev, v as EventListener);
      } else if (k === "value" && node instanceof HTMLInputElement) {
        node.value = String(v);
      } else if (v !== false) node.setAttribute(k, String(v));
    }
  }
  for (const ch of children) {
    if (typeof ch === "string") node.appendChild(document.createTextNode(ch));
    else node.appendChild(ch);
  }
  return node;
}

function syncGreeting(): void {
  const input = document.querySelector<HTMLInputElement>("#name-input");
  const out = document.querySelector("#greeting-out");
  if (!input || !out) return;
  const nm = input.value.trim();
  const n = count.read();
  out.textContent = nm
    ? `Hello, ${nm}! The counter is ${n}.`
    : "Type a name — this line updates live.";
}

function updateCounterUI(): void {
  const n = count.read();
  const parity = n % 2 === 0 ? "even" : "odd";
  const big = document.querySelector("#count-val");
  const par = document.querySelector("#parity-out");
  if (big) big.textContent = String(n);
  if (par) par.textContent = `(${parity})`;
  syncGreeting();
}

function renderTodoList(): void {
  const ul = document.querySelector("#todo-list");
  const empty = document.querySelector("#todo-empty");
  if (!ul) return;
  const list = todos.read();
  ul.replaceChildren(
    ...list.map((item, i) =>
      el(
        "li",
        { class: "list-item" },
        el("span", null, item),
        el(
          "button",
          {
            type: "button",
            class: "ghost",
            onclick: () => todos.update((xs) => xs.filter((_, j) => j !== i)),
          },
          "✕",
        ),
      ),
    ),
  );
  if (empty) empty.toggleAttribute("hidden", list.length > 0);
}

function mount(): void {
  root.replaceChildren(
    el(
      "section",
      { class: "panel" },
      el("h2", null, "Reactive counter"),
      el("p", { class: "big", id: "count-val" }, "0"),
      el("p", { class: "muted", id: "parity-out" }, "(even)"),
      el(
        "div",
        { class: "row" },
        el("button", { type: "button", onclick: () => count.update((c) => c - 1) }, "−"),
        el("button", { type: "button", onclick: () => count.write(0) }, "Reset"),
        el("button", { type: "button", onclick: () => count.update((c) => c + 1) }, "+"),
      ),
    ),
    el(
      "section",
      { class: "panel" },
      el("h2", null, "Derived greeting"),
      el(
        "label",
        { class: "stack" },
        "Your name",
        el("input", {
          id: "name-input",
          type: "text",
          placeholder: "Ada",
          oninput: () => syncGreeting(),
        }),
      ),
      el("p", { class: "highlight", id: "greeting-out" }, "Type a name — this line updates live."),
    ),
    el(
      "section",
      { class: "panel" },
      el("h2", null, "Reactive list"),
      el(
        "div",
        { class: "row" },
        el("input", {
          id: "todo-draft",
          type: "text",
          placeholder: "Add a note…",
        }),
        el(
          "button",
          {
            type: "button",
            onclick: () => {
              const draft = document.querySelector<HTMLInputElement>("#todo-draft");
              const t = draft?.value.trim() ?? "";
              if (!t) return;
              todos.update((xs) => [...xs, t]);
              if (draft) draft.value = "";
            },
          },
          "Add",
        ),
      ),
      el("p", { class: "muted", id: "todo-empty" }, "Nothing here yet."),
      el("ul", { class: "list", id: "todo-list" }),
    ),
  );

  updateCounterUI();
  renderTodoList();
}

mount();
count.subscribe(updateCounterUI);
todos.subscribe(renderTodoList);
