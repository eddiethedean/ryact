from __future__ import annotations

import pytest
from ryact_build.bundle_config import parse_define_arg


def test_parse_define_ok() -> None:
    assert parse_define_arg("NODE_ENV=\"production\"") == ("NODE_ENV", '"production"')


def test_parse_define_bad() -> None:
    with pytest.raises(ValueError):
        parse_define_arg("noequals")
