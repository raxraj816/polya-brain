"""Check validation for the v2 set: correct solutions and realistic mutants."""

from __future__ import annotations

CORRECT_V2: dict[str, str] = {
    "semver_satisfies": r"""
import re
def _parse(v):
    core, _, pre = v.partition('-')
    return tuple(map(int, core.split('.'))), (pre.split('.') if pre else [])
def _cmp(a, b):
    (ca, pa), (cb, pb) = _parse(a), _parse(b)
    if ca != cb:
        return -1 if ca < cb else 1
    if not pa or not pb:
        return (not pa) - (not pb)
    for x, y in zip(pa, pb):
        if x == y:
            continue
        if x.isdigit() and y.isdigit():
            return -1 if int(x) < int(y) else 1
        if x.isdigit() != y.isdigit():
            return -1 if x.isdigit() else 1
        return -1 if x < y else 1
    return (len(pa) > len(pb)) - (len(pa) < len(pb))
def _expand(c):
    m = re.fullmatch(r'(<=|>=|<|>|=)?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)', c)
    if m:
        return [(m.group(1) or '=', m.group(2))], True
    if c[0] in '^~':
        M, n, p = map(int, c[1:].split('.'))
        if c[0] == '~':
            upper = f'{M}.{n + 1}.0-0'
        elif M:
            upper = f'{M + 1}.0.0-0'
        elif n:
            upper = f'0.{n + 1}.0-0'
        else:
            upper = f'0.0.{p + 1}-0'
        return [('>=', c[1:]), ('<', upper)], False
    parts = [x for x in c.split('.') if x not in ('x', '*')]
    if not parts:
        return [('>=', '0.0.0')], False
    if len(parts) == 1:
        M = int(parts[0])
        return [('>=', f'{M}.0.0'), ('<', f'{M + 1}.0.0-0')], False
    M, n = map(int, parts)
    return [('>=', f'{M}.{n}.0'), ('<', f'{M}.{n + 1}.0-0')], False
_OPS = {'<': lambda r: r < 0, '<=': lambda r: r <= 0, '>': lambda r: r > 0, '>=': lambda r: r >= 0, '=': lambda r: r == 0}
def satisfies(version, rng):
    core = version.partition('-')[0]
    has_pre = '-' in version
    for group in rng.split(' || '):
        allowed = not has_pre
        good = True
        for c in group.split(' '):
            comps, plain = _expand(c)
            for op, v in comps:
                if not _OPS[op](_cmp(version, v)):
                    good = False
                if plain and '-' in v and v.partition('-')[0] == core:
                    allowed = True
        if good and allowed:
            return True
    return False
""",
    "multi_window_limiter": r"""
from collections import deque
def admit(times, limits):
    queues = [deque() for _ in limits]
    out = []
    for t in times:
        ok = True
        for q, (w, c) in zip(queues, limits):
            while q and q[0] <= t - w:
                q.popleft()
            if len(q) >= c:
                ok = False
        if ok:
            for q in queues:
                q.append(t)
        out.append(ok)
    return out
""",
    "overdraft_ledger": r"""
def run_ledger(ops, overdraft, fee):
    balances, failed = {}, []
    for index, op in enumerate(ops):
        kind = op[0]
        if kind == 'deposit':
            balances[op[1]] = balances.get(op[1], 0) + op[2]
            continue
        source, amount = op[1], op[-1]
        exists = source in balances
        valid = exists and (kind == 'withdraw' or op[1] != op[2])
        if valid and balances[source] - amount >= -overdraft:
            balances[source] -= amount
            if kind == 'transfer':
                balances[op[2]] = balances.get(op[2], 0) + amount
            continue
        failed.append(index)
        if exists and balances[source] - fee >= -overdraft:
            balances[source] -= fee
    return balances, failed
""",
    "cron_next": r"""
import datetime
def _values(text, lo, hi):
    out = set()
    for item in text.split(','):
        if '/' in item:
            base, step = item.split('/')
            step = int(step)
        else:
            base, step = item, 1
        if base == '*':
            start, stop = lo, hi
        elif '-' in base:
            start, stop = map(int, base.split('-'))
        else:
            start = int(base)
            stop = hi if '/' in item else start
        out.update(range(start, stop + 1, step))
    return out
def next_fire(expr, after):
    m, h, dom, mon, dow = expr.split(' ')
    minutes = sorted(_values(m, 0, 59)); hours = sorted(_values(h, 0, 23))
    doms, mons, dows = _values(dom, 1, 31), _values(mon, 1, 12), _values(dow, 0, 6)
    end = after + datetime.timedelta(days=1830)
    day = after.date()
    while day <= end.date():
        if day.month in mons:
            in_dom, in_dow = day.day in doms, day.isoweekday() % 7 in dows
            if dom != '*' and dow != '*':
                match = in_dom or in_dow
            elif dom != '*':
                match = in_dom
            elif dow != '*':
                match = in_dow
            else:
                match = True
            if match:
                for hour in hours:
                    for minute in minutes:
                        t = datetime.datetime(day.year, day.month, day.day, hour, minute)
                        if t > after:
                            return t if t <= end else None
        day += datetime.timedelta(days=1)
    return None
""",
    "phaseout_tax": r"""
def tax_due(income, brackets, deduction, phase_start):
    effective = max(0, deduction - max(0, income - phase_start) // 2)
    taxable = max(0, income - effective)
    numerator = 0
    lower = 0
    for upper, rate in brackets:
        top = taxable if upper is None else min(taxable, upper)
        if top > lower:
            numerator += (top - lower) * rate
        if upper is None or upper >= taxable:
            break
        lower = upper
    return (numerator * 2 + 10000) // 20000
""",
}

MUTANTS_V2: dict[str, list[str]] = {
    "semver_satisfies": [
        # Caret treated like ^1.x for 0.x versions.
        CORRECT_V2["semver_satisfies"].replace(
            "elif M:\n            upper = f'{M + 1}.0.0-0'\n        elif n:\n            upper = f'0.{n + 1}.0-0'\n        else:\n            upper = f'0.0.{p + 1}-0'",
            "else:\n            upper = f'{M + 1}.0.0-0'",
        ),
        # Prereleases treated like ordinary versions.
        CORRECT_V2["semver_satisfies"].replace("allowed = not has_pre", "allowed = True"),
        # Exact-version comparator without operator treated as a caret range.
        CORRECT_V2["semver_satisfies"].replace(
            "return [(m.group(1) or '=', m.group(2))], True",
            "return ([(m.group(1), m.group(2))], True) if m.group(1) else _expand('^' + m.group(2))",
        ),
    ],
    "multi_window_limiter": [
        # Rejected requests are counted.
        "from collections import deque\ndef admit(times, limits):\n    qs = [deque() for _ in limits]; out = []\n    for t in times:\n        ok = True\n        for q, (w, c) in zip(qs, limits):\n            while q and q[0] <= t - w: q.popleft()\n            if len(q) >= c: ok = False\n        for q in qs: q.append(t)\n        out.append(ok)\n    return out\n",
        # Closed window [t - w, t].
        CORRECT_V2["multi_window_limiter"].replace("q[0] <= t - w", "q[0] < t - w"),
        # A request rejected by one limit still consumes the others.
        "from collections import deque\ndef admit(times, limits):\n    qs = [deque() for _ in limits]; out = []\n    for t in times:\n        ok = True\n        for q, (w, c) in zip(qs, limits):\n            while q and q[0] <= t - w: q.popleft()\n            if len(q) < c: q.append(t)\n            else: ok = False\n        out.append(ok)\n    return out\n",
    ],
    "overdraft_ledger": [
        # Fee always charged.
        CORRECT_V2["overdraft_ledger"].replace(
            "if exists and balances[source] - fee >= -overdraft:", "if exists:"
        ),
        # Self-transfer treated as success.
        CORRECT_V2["overdraft_ledger"].replace("(kind == 'withdraw' or op[1] != op[2])", "True"),
        # Overdraft bound applied as strictly greater.
        CORRECT_V2["overdraft_ledger"].replace(
            "balances[source] - amount >= -overdraft", "balances[source] - amount > -overdraft"
        ),
    ],
    "cron_next": [
        # AND instead of Vixie OR rule.
        CORRECT_V2["cron_next"].replace("match = in_dom or in_dow", "match = in_dom and in_dow"),
        # Python weekday numbering (Monday = 0).
        CORRECT_V2["cron_next"].replace("day.isoweekday() % 7", "day.weekday()"),
        # '*/n' treated as unrestricted.
        CORRECT_V2["cron_next"]
        .replace(
            "if dom != '*' and dow != '*':",
            "if not dom.startswith('*') and not dow.startswith('*'):",
        )
        .replace("elif dom != '*':", "elif not dom.startswith('*'):")
        .replace("elif dow != '*':", "elif not dow.startswith('*'):"),
        # 'n/s' treated as just n.
        CORRECT_V2["cron_next"].replace("stop = hi if '/' in item else start", "stop = start"),
    ],
    "phaseout_tax": [
        # Python round (banker's rounding).
        "from fractions import Fraction\ndef tax_due(income, brackets, deduction, phase_start):\n    eff = max(0, deduction - max(0, income - phase_start) // 2)\n    taxable = max(0, income - eff)\n    total, lower = Fraction(0), 0\n    for upper, rate in brackets:\n        top = taxable if upper is None else min(taxable, upper)\n        if top > lower: total += Fraction((top - lower) * rate, 10000)\n        if upper is None: break\n        lower = upper\n    return round(total)\n",
        # Rounds each bracket separately.
        "def tax_due(income, brackets, deduction, phase_start):\n    eff = max(0, deduction - max(0, income - phase_start) // 2)\n    taxable = max(0, income - eff)\n    total, lower = 0, 0\n    for upper, rate in brackets:\n        top = taxable if upper is None else min(taxable, upper)\n        if top > lower: total += ((top - lower) * rate * 2 + 10000) // 20000\n        if upper is None: break\n        lower = upper\n    return total\n",
        # Floating point.
        "def tax_due(income, brackets, deduction, phase_start):\n    eff = max(0, deduction - max(0, income - phase_start) / 2)\n    taxable = max(0, income - eff)\n    total, lower = 0.0, 0\n    for upper, rate in brackets:\n        top = taxable if upper is None else min(taxable, upper)\n        if top > lower: total += (top - lower) * rate / 10000\n        if upper is None: break\n        lower = upper\n    return int(total + 0.5)\n",
    ],
}
