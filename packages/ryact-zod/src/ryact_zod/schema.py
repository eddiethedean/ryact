from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .ast import Node, UnknownKeys


@dataclass(frozen=True)
class Schema:
    ast: Node

    def optional(self) -> Schema:
        return Schema({**self.ast, "optional": True})

    def nullable(self) -> Schema:
        return Schema({**self.ast, "nullable": True})


def string() -> Schema:
    return Schema({"kind": "string", "checks": []})


def boolean() -> Schema:
    return Schema({"kind": "boolean"})


def number() -> Schema:
    return Schema({"kind": "number", "checks": []})


def literal(value: object) -> Schema:
    return Schema({"kind": "literal", "value": value})


def array(item: Schema) -> Schema:
    return Schema({"kind": "array", "item": item.ast})


def object_(fields: Mapping[str, Schema], *, unknown_keys: UnknownKeys = "strip") -> Schema:
    return Schema(
        {
            "kind": "object",
            "fields": {k: v.ast for k, v in fields.items()},
            "unknownKeys": unknown_keys,
        }
    )


def union(options: Sequence[Schema]) -> Schema:
    return Schema({"kind": "union", "options": [s.ast for s in options]})


def min_length(s: Schema, n: int) -> Schema:
    if s.ast.get("kind") != "string":
        raise TypeError("min_length is only valid for string schemas")
    checks = list(s.ast.get("checks") or [])
    checks.append({"op": "min", "value": n})
    return Schema({**s.ast, "checks": checks})


def max_length(s: Schema, n: int) -> Schema:
    if s.ast.get("kind") != "string":
        raise TypeError("max_length is only valid for string schemas")
    checks = list(s.ast.get("checks") or [])
    checks.append({"op": "max", "value": n})
    return Schema({**s.ast, "checks": checks})


def regex(s: Schema, pattern: str) -> Schema:
    if s.ast.get("kind") != "string":
        raise TypeError("regex is only valid for string schemas")
    # Validate pattern early so schema is safe to ship across lanes.
    re.compile(pattern)
    checks = list(s.ast.get("checks") or [])
    checks.append({"op": "regex", "value": pattern})
    return Schema({**s.ast, "checks": checks})


def email(s: Schema) -> Schema:
    if s.ast.get("kind") != "string":
        raise TypeError("email is only valid for string schemas")
    checks = list(s.ast.get("checks") or [])
    checks.append({"op": "email", "value": True})
    return Schema({**s.ast, "checks": checks})
