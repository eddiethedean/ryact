import fs from "node:fs";

import swc from "@swc/core";

function usage() {
  console.error("Usage: node scripts/jsx_to_py_transform.mjs <input.tsx> --mode expr|module");
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length < 1) usage();

const inputPath = args[0];
let mode = "expr";
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--mode") {
    mode = args[i + 1] ?? "expr";
    i++;
  }
}

const src = fs.readFileSync(inputPath, "utf8");

const parsed = await swc.parse(src, {
  syntax: "typescript",
  tsx: true,
  target: "es2022",
  comments: false,
});

function pyReprString(s) {
  // Use JSON escaping as a stable subset (double-quoted Python string).
  return JSON.stringify(s);
}

function isUppercaseTag(name) {
  return name.length > 0 && name[0] === name[0].toUpperCase();
}

function emitTagName(name) {
  if (isUppercaseTag(name)) return `scope[${pyReprString(name)}]`;
  return pyReprString(name);
}

function emitExpr(expr) {
  // Intentionally small "JS-ish to Python-ish" expression emitter.
  // This is only meant for the milestone's smoke tests; deeper JS semantics
  // belong in later milestones.
  switch (expr.type) {
    case "Identifier":
      return `(${expr.value})`;
    case "StringLiteral":
      return `(${pyReprString(expr.value)})`;
    case "NumericLiteral":
      return `(${String(expr.value)})`;
    case "BooleanLiteral":
      return `(${expr.value ? "True" : "False"})`;
    case "NullLiteral":
      return "(None)";
    case "UnaryExpression":
      return `(${expr.operator}${emitExpr(expr.argument)})`;
    case "BinaryExpression":
      return `(${emitExpr(expr.left)} ${expr.operator} ${emitExpr(expr.right)})`;
    default:
      throw new Error(`Unsupported expression node type: ${expr.type}`);
  }
}

function emitProps(attrs) {
  if (!attrs || attrs.length === 0) return "None";
  const items = [];
  for (const a of attrs) {
    if (a.type === "JSXAttribute") {
      const key = a.name.value;
      if (a.value == null) {
        items.push(`${pyReprString(key)}: True`);
      } else if (a.value.type === "StringLiteral") {
        items.push(`${pyReprString(key)}: ${pyReprString(a.value.value)}`);
      } else if (a.value.type === "JSXExpressionContainer") {
        items.push(`${pyReprString(key)}: ${emitExpr(a.value.expression)}`);
      } else {
        throw new Error(`Unsupported JSXAttribute value type: ${a.value.type}`);
      }
      continue;
    }
    throw new Error(`Unsupported attribute node type: ${a.type}`);
  }
  return `{${items.join(", ")}}`;
}

function emitChild(node) {
  if (node.type === "JSXText") {
    const t = node.value;
    if (t.trim() === "") return "None";
    return pyReprString(t);
  }
  if (node.type === "JSXExpressionContainer") {
    return emitExpr(node.expression);
  }
  if (node.type === "JSXElement") {
    return emitJsxElement(node);
  }
  if (node.type === "JSXFragment") {
    return emitJsxFragment(node);
  }
  throw new Error(`Unsupported JSX child node: ${node.type}`);
}

function emitJsxFragment(frag) {
  const children = (frag.children ?? []).map(emitChild).filter((c) => c !== "None");
  return `h(Fragment, None${children.length ? ", " + children.join(", ") : ""})`;
}

function emitJsxElement(el) {
  const opening = el.opening;
  let tag;
  if (opening.name.type === "Identifier") {
    tag = emitTagName(opening.name.value);
  } else {
    throw new Error(`Unsupported JSX element name: ${opening.name.type}`);
  }
  const props = emitProps(opening.attributes ?? []);
  const children = (el.children ?? []).map(emitChild).filter((c) => c !== "None");
  const args = [tag, props, ...children].join(", ");
  return `h(${args})`;
}

function findDefaultExport(mod) {
  for (const item of mod.body) {
    if (item.type === "ExportDefaultExpression") return item.expression;
  }
  return null;
}

const expr = findDefaultExport(parsed);
if (!expr) {
  throw new Error("Expected a default export expression, e.g. `export default <div />;`");
}

let pyExpr;
if (expr.type === "JSXElement") pyExpr = emitJsxElement(expr);
else if (expr.type === "JSXFragment") pyExpr = emitJsxFragment(expr);
else throw new Error(`Unsupported default export expression type: ${expr.type}`);

if (mode === "expr") {
  process.stdout.write(pyExpr + "\n");
} else if (mode === "module") {
  process.stdout.write(
    [
      "from __future__ import annotations",
      "",
      "from ryact import Fragment, h",
      "",
      "def render(scope: dict[str, object]) -> object:",
      `    return ${pyExpr}`,
      "",
    ].join("\n")
  );
} else {
  throw new Error(`Unsupported --mode: ${mode}`);
}

