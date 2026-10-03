"""Deterministic differential harness executed inside the networkless sandbox.

The harness, not a model, decides whether a candidate agrees with an independent
reference. Model-written sources are embedded as JSON strings and executed in
separate namespaces, so candidate and reference cannot share helpers or state.
"""

from __future__ import annotations

import base64
import json
import zlib
from collections.abc import Sequence

from pydantic import Field, ValidationError

from app.execution.sandbox import SandboxExecutionResult
from app.models.contracts import ContractModel

HARNESS_VERSION = "differential_harness@0.3.0"
RESULT_MARKER = "__POLYABRAIN_DIFFERENTIAL__="
MAX_SANDBOX_CODE = 20_000
REPR_LIMIT = 400


class Entrypoint(ContractModel):
    """The callable under test: a module function or a method on a fresh instance."""

    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    class_name: str | None = Field(
        default=None, max_length=120, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    def label(self) -> str:
        return f"{self.class_name}().{self.name}" if self.class_name else self.name


class Example(ContractModel):
    """An executable example quoted from the problem statement."""

    call: str = Field(min_length=1, max_length=2_000)
    expected: str = Field(min_length=1, max_length=2_000)


class Regression(ContractModel):
    """A previously adjudicated counterexample pinned for every later run."""

    args: str = Field(min_length=1, max_length=4_000)
    expected: str = Field(min_length=1, max_length=4_000)


class HarnessConfig(ContractModel):
    entrypoint: Entrypoint
    examples: list[Example] = Field(default_factory=list)
    regressions: list[Regression] = Field(default_factory=list)
    max_size: int = Field(default=8, ge=0, le=12)
    budget_seconds: float = Field(default=6.0, gt=0, le=60)
    call_seconds: float = Field(default=1.0, gt=0, le=10)
    scale_seconds: float = Field(default=4.0, gt=0, le=30)
    max_cases: int = Field(default=3_000, ge=1, le=20_000)
    seed: int = 20261002
    relaxations: list[str] = Field(default_factory=list)
    # Exhaustive mode keeps comparing across every size for the whole budget and
    # returns a diverse sample of differences (change review). The default stops
    # early at the smallest disagreement (bug hunting).
    exhaustive: bool = False
    keep: int = Field(default=3, ge=1, le=12)
    # "absolute": any candidate mutation is a finding (a spec forbids it).
    # "relative": only mutation that differs from the reference's own is a finding.
    mutation_mode: str = Field(default="absolute", pattern="^(absolute|relative)$")


class Disagreement(ContractModel):
    """One concrete input on which the candidate and the reference differ."""

    kind: str
    size: int | None = None
    args: str
    candidate: str
    reference: str


class ExampleOutcome(ContractModel):
    call: str
    expected: str
    candidate: str
    reference: str
    candidate_ok: bool
    reference_ok: bool


class ScaleOutcome(ContractModel):
    index: int
    seconds: float | None = None
    timed_out: bool = False
    error: str | None = None
    input_summary: str


class DifferentialResult(ContractModel):
    """Bounded summary emitted by one harness execution."""

    harness_version: str = HARNESS_VERSION
    setup_error: str | None = None
    examples: list[ExampleOutcome] = Field(default_factory=list)
    regressions_failed: list[Disagreement] = Field(default_factory=list)
    cases_compared: int = 0
    reference_skipped: int = 0
    generator_errors: int = 0
    sizes_covered: list[int] = Field(default_factory=list)
    disagreements: int = 0
    counterexamples: list[Disagreement] = Field(default_factory=list)
    mutation_detected: bool = False
    scale: list[ScaleOutcome] = Field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def candidate_example_failures(self) -> list[ExampleOutcome]:
        return [item for item in self.examples if not item.candidate_ok]

    @property
    def reference_example_failures(self) -> list[ExampleOutcome]:
        return [item for item in self.examples if not item.reference_ok]

    @property
    def scale_failures(self) -> list[ScaleOutcome]:
        return [item for item in self.scale if item.timed_out or item.error]

    @property
    def coverage_failure(self) -> str | None:
        """Existing result counters must not hide unavailable comparisons."""
        if self.setup_error is not None:
            return self.setup_error
        if self.cases_compared == 0 or self.generator_errors or self.reference_skipped:
            return (
                f"Incomplete comparison coverage: {self.cases_compared} completed inputs, "
                f"generator errors {self.generator_errors}, "
                f"reference timeouts {self.reference_skipped}."
            )
        return None

    @property
    def agrees(self) -> bool:
        """True only when every executed comparison agreed and nothing was unusable."""
        return (
            self.coverage_failure is None
            and not self.disagreements
            and not self.regressions_failed
            and not self.mutation_detected
            and not self.candidate_example_failures
            and not self.reference_example_failures
            and not self.scale_failures
        )


_DRIVER = r"""
import copy as _c, json as _j, math as _m, random as _r, signal as _s, sys as _y, time as _t
import datetime, fractions, decimal, collections
_SRC = __PB["sources"]
_CFG = __PB["config"]
_OUT = {"harness_version": __PB["version"], "examples": [], "regressions_failed": [], "counterexamples": [], "scale": []}
_LIMIT = 400
class _Timeout(BaseException):
    pass
def _alarm(signum, frame):
    raise _Timeout()
_s.signal(_s.SIGALRM, _alarm)
_ATOMS = (int, float, complex, str, bytes, bool, type(None))
def _plain_object(value):
    return hasattr(value, "__dict__") and type(value).__eq__ is object.__eq__ and not isinstance(value, type)
def _snap(value, memo=None):
    # Structural, address-free snapshot used to compare objects without value equality.
    if memo is None:
        memo = {}
    if isinstance(value, _ATOMS):
        return ("atom", type(value).__name__, value)
    key = id(value)
    if key in memo:
        return ("ref", memo[key])
    memo[key] = len(memo)
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, tuple(_snap(item, memo) for item in value))
    if isinstance(value, dict):
        return ("dict", tuple((_snap(k, memo), _snap(v, memo)) for k, v in value.items()))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, tuple(sorted(repr(_snap(item, memo)) for item in value)))
    if _plain_object(value):
        return ("obj", type(value).__name__, _snap(vars(value), memo))
    return ("value", value)
def _brief(value, depth=0, seen=None):
    seen = set() if seen is None else seen
    if not _plain_object(value):
        if isinstance(value, list) and hasattr(value, "truncated"):
            return "generator yielding " + _brief(list(value), depth, seen) + (" ...(truncated)" if value.truncated else "")
        if isinstance(value, (list, tuple)) and depth < 4:
            inner = ", ".join(_brief(item, depth + 1, seen) for item in value[:8])
            if isinstance(value, tuple) and len(value) == 1:
                inner += ","
            return ("[%s]" if isinstance(value, list) else "(%s)") % (inner + (", ..." if len(value) > 8 else ""))
        return repr(value)
    if id(value) in seen or depth > 2:
        return type(value).__name__ + "(...)"
    seen.add(id(value))
    fields = ", ".join("%s=%s" % (k, _brief(v, depth + 1, seen)) for k, v in list(vars(value).items())[:6])
    return "%s(%s)" % (type(value).__name__, fields)
def _rep(value):
    try:
        text = _brief(value)
    except BaseException as exc:
        text = "<unrepresentable %s>" % type(exc).__name__
    return text if len(text) <= _LIMIT else text[:_LIMIT] + "...<truncated>"
class _Gen(list):
    # Items produced by a generator/iterator result, consumed inside the timed call.
    truncated = False
    def __repr__(self):
        return "generator yielding " + list.__repr__(self) + (" ...(truncated)" if self.truncated else "")
def _materialize(value):
    if isinstance(value, (str, bytes, bytearray, list, tuple, dict, set, frozenset)):
        return value
    if hasattr(value, "__next__") and hasattr(value, "__iter__"):
        items = _Gen()
        for index, item in enumerate(value):
            if index >= 10000:
                _unverified("iterator result exceeded the 10000-item comparison limit")
            items.append(item)
        return items
    return value
def _call(fn, args, seconds):
    _s.setitimer(_s.ITIMER_REAL, seconds)
    try:
        return ("ok", _materialize(fn(*args)))
    except _Timeout:
        return ("timeout", None)
    except RecursionError:
        return ("raise", "RecursionError")
    except MemoryError:
        return ("raise", "MemoryError")
    except Exception as exc:
        return ("raise", type(exc).__name__)
    finally:
        _s.setitimer(_s.ITIMER_REAL, 0)
def _same_type(a, b, lenient=False):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b)
    if lenient or "numeric_type" in _CFG["relaxations"]:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return type(a) is type(b)
    return True
def _unordered_eq(a, b, lenient):
    # The normal sorted path is fast. Ambiguous sort ties or non-orderable
    # containers need bounded matching, still using recursive type checks.
    if len(a) != len(b):
        return False
    try:
        if all(_eq(x, y, lenient) for x, y in zip(sorted(a), sorted(b))):
            return True
    except Exception:
        pass
    remaining = list(b)
    comparisons = 0
    for value in a:
        for index, other in enumerate(remaining):
            comparisons += 1
            if comparisons > 50000:
                _unverified("unordered comparison exceeded its matching limit")
            if _eq(value, other, lenient):
                remaining.pop(index)
                break
        else:
            return False
    return True
def _eq(a, b, lenient=False):
    if not _same_type(a, b, lenient):
        return False
    if isinstance(a, float) and isinstance(b, (int, float)):
        if _m.isnan(a) and isinstance(b, float) and _m.isnan(b):
            return True
        return _m.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if type(a) is not type(b) or len(a) != len(b):
            return False
        if getattr(a, "truncated", False) != getattr(b, "truncated", False):
            return False
        if "unordered" in _CFG["relaxations"]:
            return _unordered_eq(a, b, lenient)
        return all(_eq(x, y, lenient) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return False
        keys = {key: key for key in b}
        return all(_eq(k, keys[k], lenient) and _eq(a[k], b[k], lenient) for k in a)
    if isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset)):
        if type(a) is not type(b) or a != b:
            return False
        members = {item: item for item in b}
        return all(_eq(item, members[item], lenient) for item in a)
    if _plain_object(a) or _plain_object(b):
        return type(a).__name__ == type(b).__name__ and _snap(a) == _snap(b)
    try:
        return bool(a == b)
    except Exception:
        return False
def _ns(source, name):
    ns = {"__name__": name, "__builtins__": __builtins__}
    exec(compile(source, "<%s>" % name, "exec"), ns)
    return ns
def _resolve(ns):
    entry = _CFG["entrypoint"]
    if entry.get("class_name"):
        cls = ns[entry["class_name"]]
        return lambda *args: getattr(cls(), entry["name"])(*args)
    return ns[entry["name"]]
def _done():
    _OUT["elapsed_seconds"] = round(_t.perf_counter() - _START, 3)
    _y.__stdout__.write(__PB["marker"] + _j.dumps(_OUT) + "\n")
    _y.__stdout__.flush()
def _unverified(reason):
    _OUT["setup_error"] = "harness: " + reason
    _done()
    raise SystemExit(0)
_START = _t.perf_counter()
_stage = "candidate"
try:
    _cand_ns = _ns(_SRC["candidate"], "candidate")
    _cand = _resolve(_cand_ns)
    _stage = "reference"
    _ref_ns = _ns(_SRC["reference"], "reference")
    _ref = _resolve(_ref_ns)
    _stage = "oracle_tools"
    _tool_ns = _ns(_SRC["tools"], "oracle_tools")
    _gen = _tool_ns["generate"]
    _same = _tool_ns.get("same")
    _scale = _tool_ns.get("scale_inputs")
except BaseException as exc:
    _OUT["setup_error"] = "%s: %s: %s" % (_stage, type(exc).__name__, _rep(str(exc))[:200])
    _done()
    raise SystemExit(0)
class _Discard:
    def write(self, text):
        return len(text)
    def flush(self):
        pass
_y.stdout = _Discard()
def _agree(args, a, b):
    if a[0] != b[0]:
        return False
    if a[0] == "raise":
        return a[1] == b[1]
    if a[0] == "timeout":
        return False
    if _same is not None:
        try:
            return bool(_same(_c.deepcopy(args), a[1], b[1]))
        except BaseException:
            return False
    return _eq(a[1], b[1])
def _show(result):
    if result[0] == "ok":
        return _rep(result[1])
    if result[0] == "raise":
        return "raised " + str(result[1])
    return "timed out"
_eval_ns = {"datetime": datetime, "date": datetime.date, "fractions": fractions, "Fraction": fractions.Fraction, "decimal": decimal, "Decimal": decimal.Decimal, "collections": collections, "inf": float("inf"), "nan": float("nan")}
for _ex in _CFG["examples"]:
    try:
        _want = eval(_ex["expected"], dict(_eval_ns))
    except BaseException as exc:
        _unverified("required example expected value could not be evaluated: " + type(exc).__name__)
    _rows = []
    for _side_ns in (_cand_ns, _ref_ns):
        _env = dict(_eval_ns); _env.update(_side_ns)
        _s.setitimer(_s.ITIMER_REAL, _CFG["call_seconds"] * 2)
        try:
            _rows.append(("ok", _materialize(eval(_ex["call"], _env))))
        except _Timeout:
            _rows.append(("timeout", None))
        except SystemExit:
            raise
        except BaseException as exc:
            _rows.append(("raise", type(exc).__name__))
        finally:
            _s.setitimer(_s.ITIMER_REAL, 0)
    _OUT["examples"].append({
        "call": _ex["call"][:_LIMIT], "expected": _ex["expected"][:_LIMIT],
        "candidate": _show(_rows[0]), "reference": _show(_rows[1]),
        "candidate_ok": _rows[0][0] == "ok" and _eq(_rows[0][1], _want, True),
        "reference_ok": _rows[1][0] == "ok" and _eq(_rows[1][1], _want, True),
    })
for _reg in _CFG["regressions"]:
    try:
        _args = eval(_reg["args"], dict(_eval_ns))
        _want = eval(_reg["expected"], dict(_eval_ns))
    except BaseException as exc:
        _unverified("pinned regression could not be evaluated: " + type(exc).__name__)
    _got = _call(_cand, _c.deepcopy(_args), _CFG["call_seconds"] * 2)
    if not (_got[0] == "ok" and _eq(_got[1], _want)):
        _OUT["regressions_failed"].append({"kind": "regression", "size": None, "args": _rep(_args), "candidate": _show(_got), "reference": _rep(_want)})
_rng = _r.Random(_CFG["seed"])
_found = []
_compared = _skipped = _generr = _dis = 0
_sizes = set()
_mutated = False
_deadline = _START + _CFG["budget_seconds"]
_after_found = 0
while _compared < _CFG["max_cases"] and _t.perf_counter() < _deadline and _generr < 50:
    _limit = (
        _CFG["max_size"] + 1
        if _CFG["exhaustive"] or not _found
        else min(f["size"] for f in _found)
    )
    _active = [z for z in range(_CFG["max_size"] + 1) if z < _limit]
    if not _active or (_after_found > 400 and not _CFG["exhaustive"]):
        break
    for _size in _active:
        if _compared >= _CFG["max_cases"] or _t.perf_counter() >= _deadline:
            break
        _case_rng = _r.Random(_rng.random())
        _gs = _call(lambda: _gen(_case_rng, _size), (), _CFG["call_seconds"])
        if _gs[0] != "ok" or not isinstance(_gs[1], tuple):
            _generr += 1
            continue
        _args = _gs[1]
        _ref_args = _c.deepcopy(_args)
        _b = _call(_ref, _ref_args, _CFG["call_seconds"])
        if _b[0] == "timeout":
            _skipped += 1
            continue
        _cand_args = _c.deepcopy(_args)
        try:
            _before = _snap(_cand_args)
        except BaseException:
            _before = None
        _a = _call(_cand, _cand_args, _CFG["call_seconds"])
        _compared += 1
        _sizes.add(_size)
        if _found:
            _after_found += 1
        try:
            if _CFG["mutation_mode"] == "relative":
                _changed = _snap(_cand_args) != _snap(_ref_args)
            else:
                _changed = _before is not None and _snap(_cand_args) != _before
        except BaseException:
            _changed = False
        if "mutation_allowed" not in _CFG["relaxations"] and _changed:
            if not _mutated:
                _found.append({"kind": "input_mutated", "size": _size, "args": _rep(_args), "candidate": "left its arguments as " + _rep(_cand_args), "reference": "left its arguments as " + _rep(_ref_args) if _CFG["mutation_mode"] == "relative" else _show(_b)})
            _mutated = True
        if not _agree(_args, _a, _b):
            _dis += 1
            _kind = "candidate_timeout" if _a[0] == "timeout" else "output_mismatch"
            if len(_found) < 200:
                _found.append({"kind": _kind, "size": _size, "args": _rep(_args), "candidate": _show(_a), "reference": _show(_b)})
            if not _CFG["exhaustive"]:
                break
_found.sort(key=lambda f: (f["size"], len(f["args"])))
if _CFG["exhaustive"]:
    # One example per distinct outcome shape first (raised vs value and result type,
    # old and new), then per size; never the same input twice.
    def _shape(text):
        if text.startswith("raised "):
            return text
        if text == "timed out":
            return "timeout"
        head = text[:1]
        if head.isdigit() or head == "-":
            return "number"
        return {"[": "list", "(": "tuple", "{": "mapping", "'": "str", '"': "str",
                "N": "None", "T": "bool", "F": "bool"}.get(head, "other")
    _unique, _args_seen = [], set()
    for _f in _found:
        if _f["args"] not in _args_seen:
            _args_seen.add(_f["args"])
            _unique.append(_f)
    _picked = []
    for _key in (
        lambda f: (f["kind"], _shape(f["reference"]), _shape(f["candidate"])),
        lambda f: (f["kind"], f["size"]),
    ):
        _seen = {_key(f) for f in _picked}
        for _f in _unique:
            if _f not in _picked and _key(_f) not in _seen:
                _seen.add(_key(_f))
                _picked.append(_f)
    _picked += [_f for _f in _unique if _f not in _picked]
    _found = _picked
_OUT["counterexamples"] = _found[:_CFG["keep"]]
_OUT.update(cases_compared=_compared, reference_skipped=_skipped, generator_errors=_generr, disagreements=_dis, mutation_detected=_mutated, sizes_covered=sorted(_sizes))
if _scale is not None and not _found and not _OUT["regressions_failed"]:
    _sc = _call(lambda: _scale(_r.Random(_CFG["seed"] + 1)), (), _CFG["call_seconds"] * 4)
    if _sc[0] != "ok" or not isinstance(_sc[1], list):
        _unverified("requested scale input generation failed or did not return a list")
    if _sc[0] == "ok" and isinstance(_sc[1], list):
        for _i, _args in enumerate(_sc[1][:3]):
            if not isinstance(_args, tuple):
                _unverified("requested scale input was not an argument tuple")
            _summary = ", ".join("%s(len=%s)" % (type(x).__name__, len(x)) if hasattr(x, "__len__") else _rep(x)[:40] for x in _args)
            _t0 = _t.perf_counter()
            _res = _call(_cand, _args, _CFG["scale_seconds"])
            _row = {"index": _i, "input_summary": _summary[:_LIMIT], "timed_out": _res[0] == "timeout"}
            if _res[0] == "ok":
                _row["seconds"] = round(_t.perf_counter() - _t0, 4)
            elif _res[0] == "raise":
                _row["error"] = str(_res[1])
            _OUT["scale"].append(_row)
_done()
"""


_BOOTSTRAP = """import base64, json, zlib
__PB = json.loads(zlib.decompress(base64.b64decode({payload!r})))
exec(compile(__PB["driver"], "<polya-differential>", "exec"), {{"__PB": __PB, "__name__": "__polya_harness__", "__builtins__": __builtins__}})
"""


def build_program(
    *,
    candidate: str,
    reference: str,
    tools: str,
    config: HarnessConfig,
) -> str:
    """Return one self-contained sandbox program, or raise if it cannot fit."""
    payload = json.dumps(
        {
            "driver": _DRIVER,
            "sources": {"candidate": candidate, "reference": reference, "tools": tools},
            "config": config.model_dump(mode="json"),
            "version": HARNESS_VERSION,
            "marker": RESULT_MARKER,
        }
    )
    encoded = base64.b64encode(zlib.compress(payload.encode(), 9)).decode()
    program = _BOOTSTRAP.format(payload=encoded)
    if len(program) > MAX_SANDBOX_CODE:
        raise ValueError(
            f"differential program is {len(program)} characters; the sandbox admits "
            f"{MAX_SANDBOX_CODE}"
        )
    return program


def parse_result(execution: SandboxExecutionResult) -> DifferentialResult:
    """Read the harness marker; any missing or malformed result is a setup failure."""
    if execution.timed_out:
        return DifferentialResult(setup_error="sandbox timed out before completion")
    if execution.output_truncated:
        return DifferentialResult(setup_error="sandbox output exceeded its bound")
    if execution.exit_code != 0:
        return DifferentialResult(setup_error=f"sandbox failed with exit {execution.exit_code}")
    for line in reversed(execution.stdout.splitlines()):
        if line.startswith(RESULT_MARKER):
            try:
                return DifferentialResult.model_validate_json(line.removeprefix(RESULT_MARKER))
            except ValidationError:
                break
    if execution.timed_out:
        reason = "sandbox timed out before the harness reported"
    elif execution.output_truncated:
        reason = "sandbox output exceeded its bound"
    else:
        tail = execution.stderr.strip().splitlines()[-1:] or ["no harness result"]
        reason = f"harness did not report (exit {execution.exit_code}): {tail[0][:200]}"
    return DifferentialResult(setup_error=reason)


def tools_source(generator: str, same: str = "", scale: str = "") -> str:
    """Combine oracle helper sources into the one oracle-tools namespace."""
    parts: Sequence[str] = [generator, same, scale]
    return "\n\n".join(part for part in parts if part.strip())
