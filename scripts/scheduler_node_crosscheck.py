from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    # scripts/ is at repo root
    return Path(__file__).resolve().parent.parent


def _load_python_scenarios() -> Any:
    # Load the module by path so this script works outside pytest's import model.
    mod_path = _repo_root() / "tests_upstream" / "scheduler" / "node_crosscheck_scenarios.py"
    spec = spec_from_file_location("node_crosscheck_scenarios", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load scenarios module: {mod_path}")
    mod = module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_python_scenarios(selected: list[str]) -> dict[str, Any]:
    scenarios = _load_python_scenarios()
    out: dict[str, Any] = {}
    for name in selected:
        res = scenarios.run_scenario(name)
        out[name] = asdict(res)
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _require_cmd(cmd: str) -> None:
    if shutil.which(cmd) is None:
        raise SystemExit(f"Missing required command: {cmd!r}")


def _run_jest(react_path: Path, pattern: str) -> int:
    """
    Optional: run a tiny upstream Jest selection as a smoke cross-check.

    We intentionally do not parse Jest logs into a stable contract here. The
    primary repo gate remains pytest; this is just an opt-in confidence layer.
    """
    _require_cmd("node")
    # Prefer yarn if present; otherwise allow npm users to wire their own.
    if (react_path / "yarn.lock").exists():
        runner = ["yarn", "jest"]
        _require_cmd("yarn")
    else:
        runner = ["npm", "test", "--", "jest"]
        _require_cmd("npm")

    cmd = [
        *runner,
        "--runInBand",
        pattern,
    ]
    p = subprocess.run(cmd, cwd=str(react_path))
    return int(p.returncode)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="scheduler_node_crosscheck",
        description=(
            "Optional cross-check utilities for schedulyr.\n\n"
            "This tool intentionally does not replace pytest as the main gate."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    sub = ap.add_subparsers(dest="cmd", required=True)

    def _add_python_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--out",
            type=Path,
            default=_repo_root() / "artifacts" / "scheduler_crosscheck.json",
            help="Path for recorded Python scenario output (JSON).",
        )
        p.add_argument(
            "--scenario",
            action="append",
            default=[],
            help="Scenario name to include (repeatable). Default: all.",
        )

    py_record = sub.add_parser("python-record", help="Record Python scenarios to --out.")
    _add_python_opts(py_record)
    py_compare = sub.add_parser("python-compare", help="Compare Python scenarios to --out.")
    _add_python_opts(py_compare)

    jest = sub.add_parser("jest-smoke", help="Run a small upstream Jest subset (optional).")
    jest.add_argument(
        "--react-path",
        type=Path,
        required=True,
        help="Path to a local facebook/react checkout.",
    )
    jest.add_argument(
        "--pattern",
        type=str,
        default="packages/scheduler/src/__tests__",
        help="Jest testPathPattern (default: scheduler tests directory).",
    )

    ns = ap.parse_args(argv)

    scenarios = _load_python_scenarios()
    selected = getattr(ns, "scenario", []) or scenarios.list_scenarios()

    if ns.cmd == "python-record":
        payload = {
            "cwd": os.getcwd(),
            "scenarios": selected,
            "results": _run_python_scenarios(selected),
        }
        _write_json(ns.out, payload)
        print(f"Wrote {ns.out}")
        return 0

    if ns.cmd == "python-compare":
        expected = _read_json(ns.out)
        actual = {
            "scenarios": selected,
            "results": _run_python_scenarios(selected),
        }
        exp_results = expected.get("results", {})
        if exp_results != actual["results"]:
            # Simple structured diff for humans
            _write_json(ns.out.with_suffix(".actual.json"), actual)
            print(f"Mismatch. Wrote {ns.out.with_suffix('.actual.json')}", file=sys.stderr)
            return 2
        print("OK (Python scenarios match recorded output).")
        return 0

    if ns.cmd == "jest-smoke":
        return _run_jest(ns.react_path, ns.pattern)

    raise SystemExit(f"Unknown cmd: {ns.cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

