"""Run one case check against a selected frozen implementation."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reproduction module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case_root", type=Path)
    parser.add_argument("implementation", choices=["buggy", "fixed"])
    args = parser.parse_args()
    case_root = args.case_root.resolve(strict=True)
    implementation = _load(
        case_root / f"{args.implementation}_impl.py",
        f"field_{args.implementation}_impl",
    )
    check = _load(case_root / "check.py", "field_reproduction_check")
    check.verify(implementation)
    print(f"{case_root.name}:{args.implementation}:PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
