import fs from "node:fs";

import swc from "@swc/core";

function indexToLineCol(src, idx) {
  // 1-based line, 0-based col (good enough for printing)
  let line = 1;
  let col = 0;
  for (let i = 0; i < idx && i < src.length; i++) {
    if (src[i] === "\n") {
      line++;
      col = 0;
    } else {
      col++;
    }
  }
  return { line, col };
}

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

const mapping = [];

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
    case "MemberExpression": {
      // Minimal support for `React.memo` / `React.forwardRef` in expression positions.
      if (expr.object.type === "Identifier" && expr.object.value === "React") {
        if (expr.property.type === "Identifier" && expr.property.value === "memo") {
          return "(memo)";
        }
        if (expr.property.type === "Identifier" && expr.property.value === "forwardRef") {
          return "(forward_ref)";
        }
      }
      throw new Error(`Unsupported MemberExpression: ${expr.object.type}.${expr.property.type}`);
    }
    case "CallExpression": {
      // Minimal support for wrapper helpers in expression positions, e.g. `React.memo(x)`.
      const callee = emitExpr(expr.callee);
      const args = (expr.arguments ?? []).map((a) => {
        if (a.expression) return emitExpr(a.expression);
        throw new Error(`Unsupported call argument node`);
      });
      return `(${callee}(${args.join(", ")}))`;
    }
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
  mapping.push({
    kind: "Fragment",
    span: frag.span,
    loc: {
      start: indexToLineCol(src, frag.span.start),
      end: indexToLineCol(src, frag.span.end),
    },
  });
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
  mapping.push({
    kind: "Element",
    span: el.span,
    loc: {
      start: indexToLineCol(src, el.span.start),
      end: indexToLineCol(src, el.span.end),
    },
  });
  return `h(${args})`;
}

function findDefaultExport(mod) {
  for (const item of mod.body) {
    if (item.type === "ExportDefaultExpression") return item.expression;
  }
  return null;
}

function unwrapDefaultExpr(expr) {
  let cur = expr;
  // Common wrappers produced by TSX parsing.
  while (cur && (cur.type === "ParenthesisExpression" || cur.type === "TsAsExpression" || cur.type === "TsSatisfiesExpression")) {
    cur = cur.expression;
  }
  return cur;
}

const expr = findDefaultExport(parsed);
if (!expr) {
  throw new Error("Expected a default export expression, e.g. `export default <div />;`");
}

const unwrapped = unwrapDefaultExpr(expr);

let pyExpr;
if (unwrapped.type === "JSXElement") pyExpr = emitJsxElement(unwrapped);
else if (unwrapped.type === "JSXFragment") pyExpr = emitJsxFragment(unwrapped);
else throw new Error(`Unsupported default export expression type: ${unwrapped.type}`);

if (mode === "expr") {
  process.stdout.write(pyExpr + "\n");
} else if (mode === "module") {
  process.stdout.write(
    [
      "from __future__ import annotations",
      "",
      "from ryact import Fragment, forward_ref, h, memo",
      "",
      "__ryact_jsx_source__ = " + pyReprString(inputPath),
      "__ryact_jsx_map__ = " + JSON.stringify(mapping, null, 2),
      "",
      "def render(scope: dict[str, object]) -> object:",
      `    return ${pyExpr}`,
      "",
    ].join("\n")
  );
} else {
  throw new Error(`Unsupported --mode: ${mode}`);
}

