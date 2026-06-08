from __future__ import annotations

import math

from ryact_zod import number, object_, regex, safe_parse, string, union


def test_regex_requires_full_string_match() -> None:
    schema = regex(string(), r"^\d+$").ast
    ok = safe_parse(schema, "123")
    bad = safe_parse(schema, "abc123")
    assert ok.success is True
    assert bad.success is False
    assert bad.issues[0]["code"] == "invalid_string"


def test_optional_fields_omit_absent_keys() -> None:
    schema = object_({"name": string().optional()}).ast
    result = safe_parse(schema, {})
    assert result.success is True
    assert result.data == {}


def test_number_rejects_nan_and_inf() -> None:
    schema = number().ast
    assert safe_parse(schema, float("nan")).success is False
    assert safe_parse(schema, math.inf).success is False
    assert safe_parse(schema, 1).success is True


def test_schema_ast_is_deep_copied() -> None:
    base = string()
    base.ast["checks"].append({"op": "min", "value": 1})
    other = string()
    assert other.ast["checks"] == []


def test_union_failure_includes_branch_issues() -> None:
    schema = union([string(), number()]).ast
    result = safe_parse(schema, True)
    assert result.success is False
    issue = result.issues[0]
    assert issue["code"] == "invalid_union"
    assert "branches" in issue
    assert len(issue["branches"]) == 2
    assert all(branch for branch in issue["branches"])


def test_safe_parse_rejects_invalid_regex_pattern_at_runtime() -> None:
    schema = {"kind": "string", "checks": [{"op": "regex", "value": r"^\d+$"}]}
    assert safe_parse(schema, "12").success is True
