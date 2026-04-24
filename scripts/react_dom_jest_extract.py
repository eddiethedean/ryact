"""
Extract Jest describe/it/test titles from React DOM __tests__ JavaScript files.

This mirrors ``scripts/react_jest_extract.py`` but scans React DOM test folders.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


class ExtractedCase(NamedTuple):
    upstream_path: str
    describe_path: tuple[str, ...]
    it_title: str
    kind: str  # "it" | "it.skip" | "test"


REACT_DOM_TEST_DIRS = [
    Path("packages/react-dom/src/__tests__"),
    Path("packages/react-dom/src/client/__tests__"),
]


def read_string_literal(text: str, i: int) -> tuple[str, int]:
    quote = text[i]
    if quote not in "\"'":
        raise ValueError(f"Expected string opener at {i}")
    i += 1
    out: list[str] = []
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 1
            if i < len(text):
                out.append(text[i])
                i += 1
            continue
        if c == quote:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("Unterminated string literal")


def skip_non_code(text: str, i: int) -> int:
    while i < len(text):
        if text[i] in " \t\n\r":
            i += 1
            continue
        if i + 1 < len(text) and text[i : i + 2] == "//":
            i += 2
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if i + 1 < len(text) and text[i : i + 2] == "/*":
            i += 2
            while i + 1 < len(text) and text[i : i + 2] != "*/":
                i += 1
            i = min(i + 2, len(text))
            continue
        # Skip regex literals to avoid confusing quotes inside /.../ as strings.
        # This is intentionally conservative: it only triggers on a '/' that is
        # not starting a comment, and then scans to the next unescaped '/'.
        if text[i] == "/" and not (i + 1 < len(text) and text[i + 1] in "/*"):
            j = i + 1
            in_class = False
            while j < len(text):
                c = text[j]
                if c == "\\":
                    j += 2
                    continue
                if c == "[":
                    in_class = True
                    j += 1
                    continue
                if c == "]":
                    in_class = False
                    j += 1
                    continue
                if c == "/" and not in_class:
                    # consume trailing flags
                    j += 1
                    while j < len(text) and text[j].isalpha():
                        j += 1
                    i = j
                    break
                if c == "\n":
                    # Not a regex literal; treat as code.
                    break
                j += 1
            if i == j:
                continue
        if text[i] == "'":
            try:
                _, i = read_string_literal(text, i)
            except Exception:
                break
            continue
        if text[i] == '"':
            try:
                _, i = read_string_literal(text, i)
            except Exception:
                break
            continue
        if text[i] == "`":
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "`":
                    i += 1
                    break
                if text[i] == "$" and i + 1 < len(text) and text[i + 1] == "{":
                    i += 2
                    b = 1
                    while i < len(text) and b > 0:
                        if text[i] == "{":
                            b += 1
                        elif text[i] == "}":
                            b -= 1
                        i += 1
                    continue
                i += 1
            continue
        break
    return i


def _is_ident_char(c: str) -> bool:
    return c.isalnum() or c == "_" or c == "$"


def _starts_with_keyword(text: str, i: int, kw: str) -> bool:
    end = i + len(kw)
    if end > len(text) or text[i:end] != kw:
        return False
    if i > 0 and _is_ident_char(text[i - 1]):
        return False
    return not (end < len(text) and _is_ident_char(text[end]))


def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\n\r":
        i += 1
    return i


def parse_concatenated_string_title(text: str, i: int) -> tuple[str, int]:
    """After '(' of it/describe/test, read title: string (+ string)*."""
    parts: list[str] = []
    i = _skip_ws(text, i)
    while True:
        if i >= len(text):
            raise ValueError("Unterminated title")
        if text[i] in "'\"":
            frag, i = read_string_literal(text, i)
            parts.append(frag)
            i = _skip_ws(text, i)
            if i < len(text) and text[i] == "+":
                i += 1
                i = _skip_ws(text, i)
                continue
            break
        break
    return "".join(parts), i


def find_matching_paren(text: str, open_paren_idx: int) -> int:
    if open_paren_idx >= len(text) or text[open_paren_idx] != "(":
        raise ValueError("find_matching_paren: expected '('")
    depth = 1
    i = open_paren_idx + 1
    while depth > 0 and i < len(text):
        i = skip_non_code(text, i)
        if i >= len(text):
            break
        c = text[i]
        if c == "(":
            depth += 1
            i += 1
        elif c == ")":
            depth -= 1
            i += 1
        else:
            i += 1
    if depth != 0:
        raise ValueError("Unbalanced parentheses while scanning")
    return i


def _find_describe_callback_open_brace(text: str, after_title_idx: int) -> int:
    """After describe title string ends, find opening '{' of suite callback."""
    i = skip_non_code(text, after_title_idx)
    if i >= len(text) or text[i] != ",":
        raise ValueError("Expected comma after describe title")
    i += 1
    i = skip_non_code(text, i)
    # () => {  OR  function name() {
    if i + 1 < len(text) and text[i : i + 2] == "()":
        i += 2
        i = skip_non_code(text, i)
        if i + 1 < len(text) and text[i : i + 2] == "=>":
            i += 2
            i = skip_non_code(text, i)
            if i < len(text) and text[i] == "{":
                return i
        raise ValueError("Expected => { after describe ()")
    if _starts_with_keyword(text, i, "function"):
        p = text.find("(", i)
        if p == -1:
            raise ValueError("function without (")
        close = find_matching_paren(text, p)
        i = skip_non_code(text, close)
        if i < len(text) and text[i] == "{":
            return i
        raise ValueError("Expected { after function")
    raise ValueError(f"Unexpected describe callback start at {i}: {text[i : i + 20]!r}")


def _suite_keyword_at(text: str, i: int) -> tuple[str, int] | None:
    """Return (kind, open_paren_index) or None. kind in describe, it, it.skip, test."""
    i = skip_non_code(text, i)
    if i >= len(text):
        return None
    if _starts_with_keyword(text, i, "describe"):
        j = i + len("describe")
        j = skip_non_code(text, j)
        if j < len(text) and text[j] == "(":
            return "describe", j
    if _starts_with_keyword(text, i, "it.skip"):
        j = i + len("it.skip")
        j = skip_non_code(text, j)
        if j < len(text) and text[j] == "(":
            return "it.skip", j
    if _starts_with_keyword(text, i, "it"):
        j = i + len("it")
        j = skip_non_code(text, j)
        if j < len(text) and text[j] == "(":
            return "it", j
    if _starts_with_keyword(text, i, "test"):
        j = i + len("test")
        j = skip_non_code(text, j)
        if j < len(text) and text[j] == "(":
            return "test", j
    return None


def _slug_segment(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "case"


def stable_case_id(upstream_path: str, describe_path: tuple[str, ...], it_title: str) -> str:
    stem = Path(upstream_path).stem
    dslug = ".".join(_slug_segment(d) for d in describe_path)
    tslug = _slug_segment(it_title)
    key = json.dumps(
        {"path": upstream_path, "describe": list(describe_path), "title": it_title},
        sort_keys=True,
    )
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"react_dom.{stem}.{dslug}.{tslug}.{h}"


def canonical_case_key(upstream_path: str, describe_path: tuple[str, ...], it_title: str) -> str:
    return json.dumps(
        {"path": upstream_path, "describe": list(describe_path), "title": it_title},
        sort_keys=True,
    )


def _scan_suite_block(
    text: str,
    body_brace_open: int,
    upstream_path: str,
    describe_stack: list[str],
    out: list[ExtractedCase],
) -> int:
    """Scan from first '{' of describe/test body until matching '}'. Return index after '}'."""
    depth = 1
    i = body_brace_open + 1
    while depth > 0 and i < len(text):
        if depth == 1:
            kw = _suite_keyword_at(text, i)
            if kw is not None:
                kind, open_paren = kw
                if kind == "describe":
                    try:
                        title, after_title = parse_concatenated_string_title(text, open_paren + 1)
                        inner_brace = _find_describe_callback_open_brace(text, after_title)
                    except Exception:
                        i = open_paren + 1
                        continue
                    stack = describe_stack + [title]
                    close = _scan_suite_block(text, inner_brace, upstream_path, stack, out)
                    i = close
                    continue
                try:
                    title, _ = parse_concatenated_string_title(text, open_paren + 1)
                    close_call = find_matching_paren(text, open_paren)
                except Exception:
                    i = open_paren + 1
                    continue
                mapped = "it.skip" if kind == "it.skip" else kind
                out.append(
                    ExtractedCase(
                        upstream_path=upstream_path,
                        describe_path=tuple(describe_stack),
                        it_title=title,
                        kind=mapped,
                    )
                )
                i = close_call
                continue
        c = text[i]
        if c == "{":
            depth += 1
            i += 1
        elif c == "}":
            depth -= 1
            i += 1
        else:
            i += 1
    return i


def extract_file(upstream_root: Path, rel_path: str) -> list[ExtractedCase]:
    text = (upstream_root / rel_path).read_text(encoding="utf-8")
    out: list[ExtractedCase] = []
    i = 0
    while i < len(text):
        kw = _suite_keyword_at(text, i)
        if kw is None:
            j = skip_non_code(text, i)
            i = j if j > i else i + 1
            continue
        kind, open_paren = kw
        if kind in ("it", "it.skip", "test"):
            try:
                title, _ = parse_concatenated_string_title(text, open_paren + 1)
                close_call = find_matching_paren(text, open_paren)
            except Exception:
                i = open_paren + 1
                continue
            mapped = "it.skip" if kind == "it.skip" else kind
            out.append(
                ExtractedCase(
                    upstream_path=rel_path,
                    describe_path=(),
                    it_title=title,
                    kind=mapped,
                )
            )
            i = close_call
            continue
        if kind != "describe":
            j = skip_non_code(text, i)
            i = j if j > i else i + 1
            continue
        try:
            title, after_title = parse_concatenated_string_title(text, open_paren + 1)
            body_brace = _find_describe_callback_open_brace(text, after_title)
        except Exception:
            i = open_paren + 1
            continue
        i = _scan_suite_block(text, body_brace, rel_path, [title], out)
    return out


def iter_react_dom_test_files(upstream_root: Path) -> list[str]:
    rels: list[str] = []
    for rel_dir in REACT_DOM_TEST_DIRS:
        test_dir = upstream_root / rel_dir
        if not test_dir.exists():
            continue
        for p in sorted(test_dir.glob("*.js")):
            rels.append(str(p.relative_to(upstream_root)))
    if not rels:
        raise FileNotFoundError(
            "No upstream React DOM test dirs found (expected one of: "
            + ", ".join(str(d) for d in REACT_DOM_TEST_DIRS)
            + ")"
        )
    return rels


def extract_all(upstream_root: Path) -> list[ExtractedCase]:
    upstream_root = upstream_root.resolve()
    all_cases: list[ExtractedCase] = []
    for rel in iter_react_dom_test_files(upstream_root):
        all_cases.extend(extract_file(upstream_root, rel))
    return all_cases


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/react_dom_jest_extract.py /path/to/facebook/react")
        return 2
    upstream_root = Path(sys.argv[1]).resolve()
    cases = extract_all(upstream_root)
    payload = [c._asdict() for c in cases]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
