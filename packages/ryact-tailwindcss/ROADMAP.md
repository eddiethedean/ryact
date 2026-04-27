# ryact-tailwindcss roadmap

Parity target (conceptual): **Tailwind CSS** — utility-first styling with a configuration-driven design system.

Constraint: `ryact` renderers aren’t the browser. We want Tailwind-like **authoring ergonomics** and **design tokens**, but the output must be compatible with the host renderer’s style model (e.g. `ryact-dom` style dicts).

Upstream reference: [`tailwindlabs/tailwindcss`](https://github.com/tailwindlabs/tailwindcss)

---

## Baseline today (scaffold)

- Package exists and is wired into CI/type paths.
- Placeholder public surface: `tw(class_name, theme=None) -> TailwindResult`.

---

## Milestone 0 — Define the target style model

- Decide what the renderer expects:
  - `style` dict keys (CSS property naming + unit conventions)
  - supported subset per renderer (`ryact-dom` vs `ryact-native`)
- Add unit tests for conversion rules.

## Milestone 1 — Minimal utility compiler

- Implement a small utility subset that is widely useful:
  - spacing (`p-*`, `m-*`)
  - typography basics (`text-*`, `font-*`)
  - layout basics (`flex`, `items-*`, `justify-*`)
- Return:
  - normalized `class_name` (for debugging)
  - computed `style` dict

## Milestone 2 — Theme/config

- Support a minimal Tailwind-like config object:
  - spacing scale, colors, font sizes
- Keep it JSON-serializable for cross-lane usage.

## Milestone 3 — TSX lane + parity apps

- Make TSX usage ergonomic (class strings compile as-is).
- Add a parity app fixture under `tests_parity/` that asserts deterministic DOM output for a few utilities.

