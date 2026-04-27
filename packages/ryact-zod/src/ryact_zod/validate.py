from __future__ import annotations

import re
from typing import Any, Sequence, cast

from .ast import Issue, Node, ParseResult

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def safe_parse(schema: Node, data: object) -> ParseResult:
    issues: list[Issue] = []
    out = _parse(schema, data, path=[], issues=issues)
    if issues:
        return ParseResult(success=False, data=None, issues=issues)
    return ParseResult(success=True, data=out, issues=[])


def _parse(schema: Node, data: object, *, path: list[object], issues: list[Issue]) -> Any:
    optional = bool(schema.get("optional", False))
    nullable = bool(schema.get("nullable", False))
    if data is None:
        if nullable:
            return None
        if optional:
            return None
        issues.append(
            {"path": list(path), "code": "invalid_type", "message": "Expected non-null."}
        )
        return None

    kind = schema["kind"]

    if kind == "literal":
        expected = cast(Any, schema)["value"]
        if data != expected:
            issues.append(
                {
                    "path": list(path),
                    "code": "invalid_literal",
                    "message": f"Expected literal {expected!r}.",
                }
            )
        return data

    if kind == "string":
        if not isinstance(data, str):
            issues.append(
                {"path": list(path), "code": "invalid_type", "message": "Expected string."}
            )
            return None
        checks = cast(Any, schema).get("checks") or []
        for chk in checks:
            op = chk.get("op")
            val = chk.get("value")
            if op == "min" and isinstance(val, int) and len(data) < val:
                issues.append(
                    {
                        "path": list(path),
                        "code": "too_small",
                        "message": f"Must be at least {val} characters.",
                    }
                )
            elif op == "max" and isinstance(val, int) and len(data) > val:
                issues.append(
                    {
                        "path": list(path),
                        "code": "too_big",
                        "message": f"Must be at most {val} characters.",
                    }
                )
            elif op == "regex" and isinstance(val, str) and re.search(val, data) is None:
                issues.append(
                    {
                        "path": list(path),
                        "code": "invalid_string",
                        "message": "Does not match required pattern.",
                    }
                )
            elif op == "email" and not _EMAIL_RE.match(data):
                issues.append(
                    {
                        "path": list(path),
                        "code": "invalid_string",
                        "message": "Invalid email.",
                    }
                )
        return data

    if kind == "boolean":
        if not isinstance(data, bool):
            issues.append(
                {
                    "path": list(path),
                    "code": "invalid_type",
                    "message": "Expected boolean.",
                }
            )
            return None
        return data

    if kind == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            issues.append(
                {"path": list(path), "code": "invalid_type", "message": "Expected number."}
            )
            return None
        return data

    if kind == "array":
        if not isinstance(data, list):
            issues.append(
                {"path": list(path), "code": "invalid_type", "message": "Expected array."}
            )
            return None
        item = cast(Any, schema)["item"]
        return [
            _parse(item, v, path=[*path, i], issues=issues)
            for i, v in enumerate(cast(Sequence[object], data))
        ]

    if kind == "object":
        if not isinstance(data, dict):
            issues.append(
                {"path": list(path), "code": "invalid_type", "message": "Expected object."}
            )
            return None
        fields = cast(Any, schema).get("fields") or {}
        unknown_keys = cast(Any, schema).get("unknownKeys", "strip")

        out: dict[str, Any] = {}
        for k, sub in fields.items():
            if k in data:
                out[k] = _parse(sub, data[k], path=[*path, k], issues=issues)
            else:
                if bool(sub.get("optional", False)):
                    out[k] = None
                else:
                    issues.append(
                        {
                            "path": [*path, k],
                            "code": "missing_key",
                            "message": "Required.",
                        }
                    )

        if unknown_keys == "passthrough":
            for k, v in data.items():
                if k not in out:
                    out[str(k)] = v
        elif unknown_keys == "strict":
            extras = [k for k in data if k not in fields]
            if extras:
                issues.append(
                    {
                        "path": list(path),
                        "code": "unrecognized_keys",
                        "message": f"Unrecognized keys: {extras!r}",
                    }
                )
        return out

    if kind == "union":
        options = cast(Any, schema)["options"]
        all_issues: list[list[Issue]] = []
        for opt in options:
            local_issues: list[Issue] = []
            value = _parse(opt, data, path=path, issues=local_issues)
            if not local_issues:
                return value
            all_issues.append(local_issues)
        issues.append(
            {
                "path": list(path),
                "code": "invalid_union",
                "message": "Input did not match any union option.",
            }
        )
        return None

    issues.append(
        {"path": list(path), "code": "unknown_schema", "message": f"Unknown kind: {kind}"}
    )
    return None

