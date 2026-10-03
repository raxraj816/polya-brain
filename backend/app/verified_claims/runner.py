"""Sandbox program that runs two independent claim derivations on real and perturbed data."""

from __future__ import annotations

import base64
import json
import math
import zlib
from typing import Any

from pydantic import Field, ValidationError

from app.execution.sandbox import SandboxExecutionResult
from app.models.contracts import ContractModel
from app.verified_claims.tables import Table

RUNNER_VERSION = "claim_runner@0.1.0"
MARKER = "__POLYABRAIN_CLAIMS__="

_DRIVER = r"""
import copy as _c, csv as _csv, io as _io, json as _j, math as _m, random as _r, signal as _s, sys as _y
from decimal import Decimal as _D
class _Timeout(BaseException):
    pass
def _alarm(signum, frame):
    raise _Timeout()
_s.signal(_s.SIGALRM, _alarm)
def _load(kind, blob):
    text = blob.decode("utf-8-sig")
    if kind == "csv":
        return [dict(row) for row in _csv.DictReader(_io.StringIO(text))]
    return _j.loads(text)
_BASE = {name: _load(__PB["kinds"][name], blob) for name, blob in __POLYA_DATA__.items()}
def _jitter(value, rng):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value + rng.choice((-2, -1, 1, 2))
    if isinstance(value, float):
        return value * (1 + rng.uniform(-0.05, 0.05))
    if isinstance(value, str):
        text = value.strip()
        try:
            if text.lstrip("-").isdigit():
                return str(int(text) + rng.choice((-2, -1, 1, 2)))
            if "." in text and text.replace(".", "", 1).lstrip("-").isdigit():
                decimals = len(text.split(".")[1])
                return ("%." + str(decimals) + "f") % (float(text) * (1 + rng.uniform(-0.05, 0.05)))
        except ValueError:
            return value
    return value
def _variant(index):
    rng = _r.Random(__PB["seed"] * 1000 + index)
    out = {}
    for name, rows in _BASE.items():
        if not isinstance(rows, list):
            out[name] = _c.deepcopy(rows)
            continue
        rows = _c.deepcopy(rows)
        mode = index % 4
        if mode == 0:
            rng.shuffle(rows)
        elif mode == 1 and rows:
            keep = max(1, int(len(rows) * 0.7))
            rows = rng.sample(rows, keep)
        elif mode == 2 and rows:
            rows = rows + [_c.deepcopy(rng.choice(rows)) for _ in range(max(1, len(rows) // 5))]
            rng.shuffle(rows)
        elif mode == 3:
            for row in rows:
                if isinstance(row, dict):
                    for key in list(row):
                        if rng.random() < 0.5:
                            row[key] = _jitter(row[key], rng)
        out[name] = rows
    return ("variant-%d:%s" % (index, ("shuffle", "subset", "duplicates", "jitter")[index % 4]), out)
def _jsonable(value, depth=0):
    if depth > 6:
        return repr(value)[:200]
    if value is None or isinstance(value, (bool, int, str)):
        return value if not isinstance(value, str) else value[:500]
    if isinstance(value, float):
        return value if _m.isfinite(value) else repr(value)
    if isinstance(value, _D):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item, depth + 1) for item in list(value)[:200]]
    if isinstance(value, dict):
        return {str(key): _jsonable(item, depth + 1) for key, item in list(value.items())[:200]}
    return repr(value)[:200]
class _Discard:
    def write(self, text):
        return len(text)
    def flush(self):
        pass
_out = _y.stdout
def _prepare(source):
    if not source:
        return None, "missing"
    namespace = {"__name__": "derivation"}
    try:
        exec(compile(source, "<derivation>", "exec"), namespace)
        return namespace["compute"], None
    except BaseException as exc:
        return None, "%s: %s" % (type(exc).__name__, str(exc)[:200])
def _run(fn, tables):
    _y.stdout = _Discard()
    _s.setitimer(_s.ITIMER_REAL, __PB["call_seconds"])
    try:
        values = fn(_c.deepcopy(tables))
        if not isinstance(values, dict):
            return {"ok": False, "error": "compute() must return a dict of claim id -> value"}
        return {"ok": True, "values": _jsonable(values)}
    except _Timeout:
        return {"ok": False, "error": "timed out"}
    except BaseException as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, str(exc)[:200])}
    finally:
        _s.setitimer(_s.ITIMER_REAL, 0)
        _y.stdout = _out
_fns = {side: _prepare(__PB["sources"].get(side)) for side in ("candidate", "oracle")}
_report = {"version": __PB["version"], "setup": {side: err for side, (fn, err) in _fns.items()}, "runs": []}
for _label, _tables in [("original", _BASE)] + [_variant(i) for i in range(__PB["variants"])]:
    _row = {"label": _label}
    for _side, (_fn, _err) in _fns.items():
        _row[_side] = _run(_fn, _tables) if _fn is not None else {"ok": False, "error": _err}
    _report["runs"].append(_row)
_y.stdout.write(__PB["marker"] + _j.dumps(_report) + "\n")
"""

_BOOTSTRAP = """import base64, json, zlib
__PB = json.loads(zlib.decompress(base64.b64decode({payload!r})))
exec(compile(__PB["driver"], "<polya-claims>", "exec"), {{"__PB": __PB, "__POLYA_DATA__": __POLYA_DATA__, "__name__": "__polya_claims__", "__builtins__": __builtins__}})
"""


def build_program(
    *,
    tables: list[Table],
    candidate: str | None,
    oracle: str | None,
    variants: int = 4,
    call_seconds: float = 5.0,
    seed: int = 20261003,
) -> str:
    payload = json.dumps(
        {
            "driver": _DRIVER,
            "sources": {"candidate": candidate, "oracle": oracle},
            "kinds": {table.name: table.kind for table in tables},
            "variants": variants,
            "call_seconds": call_seconds,
            "seed": seed,
            "version": RUNNER_VERSION,
            "marker": MARKER,
        }
    )
    program = _BOOTSTRAP.format(
        payload=base64.b64encode(zlib.compress(payload.encode(), 9)).decode()
    )
    if len(program) > 20_000:
        raise ValueError(f"claim program is {len(program)} characters; the sandbox admits 20000")
    return program


class SideResult(ContractModel):
    ok: bool
    values: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunResult(ContractModel):
    label: str
    candidate: SideResult
    oracle: SideResult


class ClaimRunReport(ContractModel):
    version: str
    setup: dict[str, str | None] = Field(default_factory=dict)
    runs: list[RunResult] = Field(default_factory=list)
    failure: str | None = None


def parse(execution: SandboxExecutionResult) -> ClaimRunReport:
    for line in reversed(execution.stdout.splitlines()):
        if line.startswith(MARKER):
            try:
                return ClaimRunReport.model_validate_json(line.removeprefix(MARKER))
            except ValidationError:
                break
    reason = (
        "the sandbox timed out"
        if execution.timed_out
        else "output exceeded its bound"
        if execution.output_truncated
        else (execution.stderr.strip().splitlines() or ["no result"])[-1][:200]
    )
    return ClaimRunReport(version=RUNNER_VERSION, failure=reason)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "").rstrip("%")
        try:
            return float(text)
        except ValueError:
            return None
    return None


def stated_tolerance(stated: Any) -> float:
    """Half a unit in the last stated decimal place (text claims are usually rounded)."""
    text = repr(stated) if isinstance(stated, float) else str(stated)
    text = text.strip().replace(",", "").rstrip("%")
    if "e" in text.lower():
        return 0.0
    decimals = len(text.split(".")[1]) if "." in text else 0
    return 0.5 * 10.0 ** (-decimals)


def same(a: Any, b: Any, *, absolute: float = 0.0) -> bool:
    """Value agreement: numbers with tolerance, strings case/space-insensitively, recursive.

    Booleans never equal numbers or numeric strings.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    x, y = _number(a), _number(b)
    if x is not None and y is not None:
        if math.isnan(x) or math.isnan(y):
            return math.isnan(x) and math.isnan(y)
        return abs(x - y) <= max(absolute, 1e-9 * max(abs(x), abs(y), 1.0))
    if isinstance(a, str) and isinstance(b, str):
        return " ".join(a.lower().split()) == " ".join(b.lower().split())
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            same(p, q, absolute=absolute) for p, q in zip(a, b, strict=True)
        )
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], absolute=absolute) for k in a)
    return bool(a == b)
