//! CLI: TSX/JSX → Python `h(...)` codegen (same contract as `scripts/jsx_to_py_transform.mjs`).

use std::env;
use std::path::PathBuf;
use std::process;

use oxc_allocator::Allocator;
use oxc_ast::ast::{
  Argument, ExportDefaultDeclarationKind, Expression, JSXAttributeItem, JSXAttributeName,
  JSXAttributeValue, JSXChild, JSXElement, JSXElementName, JSXExpression, JSXFragment,
  JSXOpeningElement, Statement,
};
use oxc_ast::ast::ExportDefaultDeclaration;
use oxc_parser::{Parser, ParserReturn};
use oxc_span::SourceType;
use serde_json::{json, Value};

fn usage() -> ! {
  eprintln!("Usage: ryact-jsx <input.tsx> --mode expr|module");
  process::exit(2);
}

fn py_repr_string(s: &str) -> String {
  serde_json::to_string(s).unwrap_or_else(|_| "\"\"".to_string())
}

fn index_to_line_col(src: &str, idx: usize) -> (usize, usize) {
  let mut line = 1usize;
  let mut col = 0usize;
  for (i, ch) in src.char_indices() {
    if i >= idx {
      break;
    }
    if ch == '\n' {
      line += 1;
      col = 0;
    } else {
      col += 1;
    }
  }
  (line, col)
}

fn span_loc(src: &str, span: oxc_span::Span) -> Value {
  let start = span.start as usize;
  let end = span.end as usize;
  let (ls, cs) = index_to_line_col(src, start);
  let (le, ce) = index_to_line_col(src, end);
  json!({
    "start": { "line": ls, "col": cs },
    "end": { "line": le, "col": ce },
  })
}

fn unwrap_default_expr<'a>(mut expr: &'a Expression<'a>) -> &'a Expression<'a> {
  loop {
    match expr {
      Expression::ParenthesizedExpression(p) => expr = &p.expression,
      Expression::TSAsExpression(a) => expr = &a.expression,
      Expression::TSSatisfiesExpression(s) => expr = &s.expression,
      _ => return expr,
    }
  }
}

fn is_uppercase_component_tag(name: &str) -> bool {
  name.chars().next().is_some_and(|c| c.is_uppercase())
}

fn emit_tag_name_expr_for_reference(name: &str) -> String {
  if is_uppercase_component_tag(name) {
    format!("scope[{}]", py_repr_string(name))
  } else {
    py_repr_string(name)
  }
}

fn jsx_element_name_emit(opening: &JSXOpeningElement<'_>) -> Result<String, String> {
  match &opening.name {
    JSXElementName::Identifier(id) => Ok(emit_tag_name_expr_for_reference(id.name.as_str())),
    JSXElementName::IdentifierReference(id) => Ok(emit_tag_name_expr_for_reference(id.name.as_str())),
    _ => Err("unsupported JSX element name (use simple identifiers)".into()),
  }
}

fn strip_wrapping_parens(s: &str) -> String {
  let t = s.trim();
  if t.starts_with('(') && t.ends_with(')') && t.len() > 2 {
    t[1..t.len() - 1].to_string()
  } else {
    t.to_string()
  }
}

fn emit_static_member_for_react<'a>(m: &oxc_ast::ast::StaticMemberExpression<'a>) -> Result<Option<String>, String> {
  if let Expression::Identifier(obj) = &m.object {
    if obj.name.as_str() == "React" && m.property.name.as_str() == "memo" {
      return Ok(Some("(memo)".to_string()));
    }
    if obj.name.as_str() == "React" && m.property.name.as_str() == "forwardRef" {
      return Ok(Some("(forward_ref)".to_string()));
    }
  }
  Ok(None)
}

fn emit_expression<'a>(
  expr: &'a Expression<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  match expr {
    Expression::Identifier(ident) => Ok(format!("({})", ident.name.as_str())),
    Expression::StringLiteral(sl) => Ok(format!("({})", py_repr_string(sl.value.as_str()))),
    Expression::NumericLiteral(n) => Ok(format!("({})", n.value)),
    Expression::BooleanLiteral(b) => Ok(format!("({})", if b.value { "True" } else { "False" })),
    Expression::NullLiteral(_) => Ok("(None)".to_string()),
    Expression::UnaryExpression(u) => {
      let inner = emit_expression(&u.argument, src, mapping)?;
      let inner_bare = strip_wrapping_parens(&inner);
      Ok(format!("({}{})", u.operator.as_str(), inner_bare))
    }
    Expression::BinaryExpression(b) => {
      let left = emit_expression(&b.left, src, mapping)?;
      let right = emit_expression(&b.right, src, mapping)?;
      Ok(format!(
        "({} {} {})",
        strip_wrapping_parens(&left),
        b.operator.as_str(),
        strip_wrapping_parens(&right)
      ))
    }
    Expression::StaticMemberExpression(m) => {
      if let Some(s) = emit_static_member_for_react(m)? {
        return Ok(s);
      }
      Err(format!(
        "unsupported StaticMemberExpression (only React.memo / React.forwardRef): {:?}",
        expr
      ))
    }
    Expression::CallExpression(c) => {
      let callee = emit_expression(&c.callee, src, mapping)?;
      let mut args = Vec::new();
      for arg in &c.arguments {
        args.push(emit_argument(arg, src, mapping)?);
      }
      Ok(format!(
        "({}({}))",
        strip_wrapping_parens(&callee),
        args.join(", ")
      ))
    }
    Expression::JSXElement(el) => emit_jsx_element(el.as_ref(), src, mapping),
    Expression::JSXFragment(fr) => emit_jsx_fragment(fr.as_ref(), src, mapping),
    Expression::ParenthesizedExpression(p) => emit_expression(&p.expression, src, mapping),
    Expression::TSAsExpression(a) => emit_expression(&a.expression, src, mapping),
    Expression::TSSatisfiesExpression(s) => emit_expression(&s.expression, src, mapping),
    _ => Err(format!("unsupported expression in TSX→Py lane: {:?}", expr)),
  }
}

fn emit_argument<'a>(arg: &'a Argument<'a>, src: &str, mapping: &mut Vec<Value>) -> Result<String, String> {
  match arg {
    Argument::SpreadElement(_) => Err("spread arguments not supported".into()),
    Argument::Identifier(id) => Ok(format!("({})", id.name.as_str())),
    Argument::StringLiteral(sl) => Ok(format!("({})", py_repr_string(sl.value.as_str()))),
    Argument::NumericLiteral(n) => Ok(format!("({})", n.value)),
    Argument::BooleanLiteral(b) => Ok(format!("({})", if b.value { "True" } else { "False" })),
    Argument::NullLiteral(_) => Ok("(None)".to_string()),
    Argument::UnaryExpression(u) => {
      let inner = emit_expression(&u.argument, src, mapping)?;
      Ok(format!("({}{})", u.operator.as_str(), strip_wrapping_parens(&inner)))
    }
    Argument::BinaryExpression(b) => {
      let left = emit_expression(&b.left, src, mapping)?;
      let right = emit_expression(&b.right, src, mapping)?;
      Ok(format!(
        "({} {} {})",
        strip_wrapping_parens(&left),
        b.operator.as_str(),
        strip_wrapping_parens(&right)
      ))
    }
    Argument::StaticMemberExpression(m) => {
      if let Some(s) = emit_static_member_for_react(m.as_ref())? {
        return Ok(s);
      }
      Err("unsupported StaticMemberExpression in argument".into())
    }
    Argument::ComputedMemberExpression(_) => Err("computed member in argument not supported".into()),
    Argument::CallExpression(c) => {
      let callee = emit_expression(&c.callee, src, mapping)?;
      let mut args = Vec::new();
      for a in &c.arguments {
        args.push(emit_argument(a, src, mapping)?);
      }
      Ok(format!(
        "({}({}))",
        strip_wrapping_parens(&callee),
        args.join(", ")
      ))
    }
    Argument::JSXElement(el) => emit_jsx_element(el.as_ref(), src, mapping),
    Argument::JSXFragment(fr) => emit_jsx_fragment(fr.as_ref(), src, mapping),
    Argument::ParenthesizedExpression(p) => emit_expression(&p.expression, src, mapping),
    Argument::TSAsExpression(a) => emit_expression(&a.expression, src, mapping),
    Argument::TSSatisfiesExpression(s) => emit_expression(&s.expression, src, mapping),
    _ => Err(format!("unsupported call argument: {:?}", arg)),
  }
}

fn emit_props<'a>(
  opening: &JSXOpeningElement<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  let attrs = &opening.attributes;
  if attrs.is_empty() {
    return Ok("None".to_string());
  }
  let mut items = Vec::new();
  for item in attrs {
    match item {
      JSXAttributeItem::SpreadAttribute(_) => return Err("JSX spread attributes not supported".into()),
      JSXAttributeItem::Attribute(attr) => {
        let key = match &attr.name {
          JSXAttributeName::Identifier(id) => id.name.as_str(),
          JSXAttributeName::NamespacedName(_) => return Err("namespaced JSX attributes not supported".into()),
        };
        let key_py = py_repr_string(key);
        if attr.value.is_none() {
          items.push(format!("{key_py}: True"));
          continue;
        }
        match attr.value.as_ref().unwrap() {
          JSXAttributeValue::StringLiteral(sl) => {
            items.push(format!("{}: {}", key_py, py_repr_string(sl.value.as_str())));
          }
          JSXAttributeValue::ExpressionContainer(ec) => {
            let ex = emit_jsx_expression(&ec.expression, src, mapping)?;
            items.push(format!("{}: {}", key_py, ex));
          }
          JSXAttributeValue::Element(_) | JSXAttributeValue::Fragment(_) => {
            return Err("JSX element/fragment attribute values not supported".into());
          }
        }
      }
    }
  }
  Ok(format!("{{{}}}", items.join(", ")))
}

fn emit_jsx_expression<'a>(
  expr: &'a JSXExpression<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  match expr {
    JSXExpression::EmptyExpression(_) => Ok("(None)".to_string()),
    JSXExpression::Identifier(id) => Ok(format!("({})", id.name.as_str())),
    JSXExpression::StringLiteral(sl) => Ok(format!("({})", py_repr_string(sl.value.as_str()))),
    JSXExpression::NumericLiteral(n) => Ok(format!("({})", n.value)),
    JSXExpression::BooleanLiteral(b) => Ok(format!("({})", if b.value { "True" } else { "False" })),
    JSXExpression::NullLiteral(_) => Ok("(None)".to_string()),
    JSXExpression::UnaryExpression(u) => {
      let inner = emit_expression(&u.argument, src, mapping)?;
      Ok(format!("({}{})", u.operator.as_str(), strip_wrapping_parens(&inner)))
    }
    JSXExpression::BinaryExpression(b) => {
      let left = emit_expression(&b.left, src, mapping)?;
      let right = emit_expression(&b.right, src, mapping)?;
      Ok(format!(
        "({} {} {})",
        strip_wrapping_parens(&left),
        b.operator.as_str(),
        strip_wrapping_parens(&right)
      ))
    }
    JSXExpression::StaticMemberExpression(m) => {
      if let Some(s) = emit_static_member_for_react(m.as_ref())? {
        return Ok(s);
      }
      Err("unsupported StaticMemberExpression in JSX expression".into())
    }
    JSXExpression::CallExpression(c) => {
      let callee = emit_expression(&c.callee, src, mapping)?;
      let mut args = Vec::new();
      for a in &c.arguments {
        args.push(emit_argument(a, src, mapping)?);
      }
      Ok(format!(
        "({}({}))",
        strip_wrapping_parens(&callee),
        args.join(", ")
      ))
    }
    JSXExpression::JSXElement(el) => emit_jsx_element(el.as_ref(), src, mapping),
    JSXExpression::JSXFragment(fr) => emit_jsx_fragment(fr.as_ref(), src, mapping),
    JSXExpression::ParenthesizedExpression(p) => emit_expression(&p.expression, src, mapping),
    JSXExpression::TSAsExpression(a) => emit_expression(&a.expression, src, mapping),
    JSXExpression::TSSatisfiesExpression(s) => emit_expression(&s.expression, src, mapping),
    _ => Err(format!("unsupported JSX embedded expression: {:?}", expr)),
  }
}

fn emit_child<'a>(
  child: &'a JSXChild<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<Option<String>, String> {
  match child {
    JSXChild::Text(t) => {
      let v = t.value.as_str();
      if v.trim().is_empty() {
        return Ok(None);
      }
      Ok(Some(py_repr_string(v)))
    }
    JSXChild::ExpressionContainer(ec) => Ok(Some(emit_jsx_expression(&ec.expression, src, mapping)?)),
    JSXChild::Element(el) => Ok(Some(emit_jsx_element(el.as_ref(), src, mapping)?)),
    JSXChild::Fragment(fr) => Ok(Some(emit_jsx_fragment(fr.as_ref(), src, mapping)?)),
    JSXChild::Spread(_) => Err("JSX spread children not supported".into()),
  }
}

fn emit_jsx_fragment<'a>(
  frag: &JSXFragment<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  mapping.push(json!({
    "kind": "Fragment",
    "span": { "start": frag.span.start, "end": frag.span.end },
    "loc": span_loc(src, frag.span),
  }));
  let mut parts = Vec::new();
  for ch in &frag.children {
    if let Some(s) = emit_child(ch, src, mapping)? {
      parts.push(s);
    }
  }
  let tail = if parts.is_empty() {
    String::new()
  } else {
    format!(", {}", parts.join(", "))
  };
  Ok(format!("h(Fragment, None{tail})"))
}

fn emit_jsx_element<'a>(
  el: &JSXElement<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  let opening = el.opening_element.as_ref();
  let tag = jsx_element_name_emit(opening)?;
  let props = emit_props(opening, src, mapping)?;
  let mut child_exprs = Vec::new();
  for ch in &el.children {
    if let Some(s) = emit_child(ch, src, mapping)? {
      child_exprs.push(s);
    }
  }
  mapping.push(json!({
    "kind": "Element",
    "span": { "start": el.span.start, "end": el.span.end },
    "loc": span_loc(src, el.span),
  }));
  if child_exprs.is_empty() {
    Ok(format!("h({}, {})", tag, props))
  } else {
    Ok(format!("h({}, {}, {})", tag, props, child_exprs.join(", ")))
  }
}

fn emit_from_export_kind<'a>(
  kind: &'a ExportDefaultDeclarationKind<'a>,
  src: &str,
  mapping: &mut Vec<Value>,
) -> Result<String, String> {
  match kind {
    ExportDefaultDeclarationKind::FunctionDeclaration(_)
    | ExportDefaultDeclarationKind::ClassDeclaration(_)
    | ExportDefaultDeclarationKind::TSInterfaceDeclaration(_) => Err(
      "unsupported export default (expected JSX element/fragment or expression)".into(),
    ),
    ExportDefaultDeclarationKind::JSXElement(el) => emit_jsx_element(el.as_ref(), src, mapping),
    ExportDefaultDeclarationKind::JSXFragment(fr) => emit_jsx_fragment(fr.as_ref(), src, mapping),
    ExportDefaultDeclarationKind::ParenthesizedExpression(p) => {
      let u = unwrap_default_expr(&p.expression);
      emit_expression(u, src, mapping)
    }
    ExportDefaultDeclarationKind::Identifier(id) => Ok(format!("({})", id.name.as_str())),
    ExportDefaultDeclarationKind::StringLiteral(sl) => Ok(format!("({})", py_repr_string(sl.value.as_str()))),
    ExportDefaultDeclarationKind::NumericLiteral(n) => Ok(format!("({})", n.value)),
    ExportDefaultDeclarationKind::BooleanLiteral(b) => Ok(format!("({})", if b.value { "True" } else { "False" })),
    ExportDefaultDeclarationKind::NullLiteral(_) => Ok("(None)".to_string()),
    ExportDefaultDeclarationKind::UnaryExpression(u) => {
      let inner = emit_expression(&u.argument, src, mapping)?;
      Ok(format!("({}{})", u.operator.as_str(), strip_wrapping_parens(&inner)))
    }
    ExportDefaultDeclarationKind::BinaryExpression(b) => {
      let left = emit_expression(&b.left, src, mapping)?;
      let right = emit_expression(&b.right, src, mapping)?;
      Ok(format!(
        "({} {} {})",
        strip_wrapping_parens(&left),
        b.operator.as_str(),
        strip_wrapping_parens(&right)
      ))
    }
    ExportDefaultDeclarationKind::StaticMemberExpression(m) => {
      if let Some(s) = emit_static_member_for_react(m.as_ref())? {
        return Ok(s);
      }
      Err("unsupported StaticMemberExpression on export default".into())
    }
    ExportDefaultDeclarationKind::ComputedMemberExpression(_) => {
      Err("computed member on export default not supported".into())
    }
    ExportDefaultDeclarationKind::CallExpression(c) => {
      let callee = emit_expression(&c.callee, src, mapping)?;
      let mut args = Vec::new();
      for a in &c.arguments {
        args.push(emit_argument(a, src, mapping)?);
      }
      Ok(format!(
        "({}({}))",
        strip_wrapping_parens(&callee),
        args.join(", ")
      ))
    }
    ExportDefaultDeclarationKind::TSAsExpression(a) => emit_expression(&a.expression, src, mapping),
    ExportDefaultDeclarationKind::TSSatisfiesExpression(s) => emit_expression(&s.expression, src, mapping),
    _ => Err(format!(
      "unsupported export default expression kind (extend ryact-jsx): {:?}",
      kind
    )),
  }
}

fn main() {
  let mut args = env::args_os().skip(1).peekable();
  let Some(first) = args.next() else {
    usage()
  };
  let input_path = PathBuf::from(first);
  let mut mode = String::from("expr");
  while let Some(a) = args.next() {
    if a == "--mode" {
      mode = args
        .next()
        .and_then(|s| s.into_string().ok())
        .unwrap_or_else(|| usage());
    }
  }

  let src = match std::fs::read_to_string(&input_path) {
    Ok(s) => s,
    Err(e) => {
      eprintln!("ryact-jsx: read {}: {e}", input_path.display());
      process::exit(1);
    }
  };

  let allocator = Allocator::default();
  let source_type = SourceType::from_path(&input_path).unwrap_or_else(|_| {
    SourceType::ts()
      .with_module(true)
      .with_typescript(true)
      .with_jsx(true)
  });

  let ParserReturn {
    program,
    errors,
    panicked,
    ..
  } = Parser::new(&allocator, &src, source_type).parse();

  if panicked || !errors.is_empty() {
    eprintln!("ryact-jsx: parse errors: {:?}", errors);
    process::exit(1);
  }

  let mut export: Option<&ExportDefaultDeclaration> = None;
  for stmt in &program.body {
    if let Statement::ExportDefaultDeclaration(decl) = stmt {
      export = Some(decl.as_ref());
      break;
    }
  }

  let Some(decl) = export else {
    eprintln!("ryact-jsx: Expected a default export expression");
    process::exit(1);
  };

  let mut mapping: Vec<Value> = Vec::new();
  let py_expr = match emit_from_export_kind(&decl.declaration, &src, &mut mapping) {
    Ok(s) => s,
    Err(e) => {
      eprintln!("ryact-jsx: {e}");
      process::exit(1);
    }
  };

  let input_display = input_path.to_string_lossy();
  match mode.as_str() {
    "expr" => print!("{py_expr}\n"),
    "module" => {
      let map_json = serde_json::to_string_pretty(&mapping).unwrap_or_else(|_| "[]".into());
      print!(
        r#"from __future__ import annotations

from ryact import Fragment, forward_ref, h, memo

__ryact_jsx_source__ = {}
__ryact_jsx_map__ = {}

def render(scope: dict[str, object]) -> object:
    return {}

"#,
        py_repr_string(&input_display),
        map_json,
        py_expr
      );
    }
    _ => {
      eprintln!("ryact-jsx: Unsupported --mode {mode}");
      process::exit(2);
    }
  }
}
