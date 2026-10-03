"""Withheld checks for the v2 dense-rule held-out set (same conventions as checks.py)."""

from __future__ import annotations

CHECKS_V2: dict[str, list[str]] = {
    "semver_satisfies": [
        """def _x_key(v):
    core, _, pre = v.partition('-')
    nums = tuple(int(x) for x in core.split('.'))
    if not pre:
        return (nums, 1, ())
    ids = tuple((0, int(i), '') if i.isdigit() else (1, 0, i) for i in pre.split('.'))
    return (nums, 0, ids)
def _x_cmp(a, b):
    ka, kb = _x_key(a), _x_key(b)
    return (ka > kb) - (ka < kb)
def _x_desugar(c):
    if c[0] == '^':
        M, m, p = map(int, c[1:].split('.'))
        hi = f'{M+1}.0.0-0' if M else f'0.{m+1}.0-0' if m else f'0.0.{p+1}-0'
        return [('>=', c[1:]), ('<', hi)], False
    if c[0] == '~':
        M, m, p = map(int, c[1:].split('.'))
        return [('>=', c[1:]), ('<', f'{M}.{m+1}.0-0')], False
    parts = c.split('.')
    if c in ('*', 'x') or (len(parts) >= 2 and parts[-1] in ('x', '*')):
        if c in ('*', 'x'):
            return [('>=', '0.0.0')], False
        if len(parts) == 2:
            M = int(parts[0]); return [('>=', f'{M}.0.0'), ('<', f'{M+1}.0.0-0')], False
        M, m = int(parts[0]), int(parts[1])
        return [('>=', f'{M}.{m}.0'), ('<', f'{M}.{m+1}.0-0')], False
    for op in ('<=', '>=', '<', '>', '='):
        if c.startswith(op):
            return [(op, c[len(op):])], True
    return [('=', c)], True
def _x_sat(version, rng):
    for cset in rng.split(' || '):
        ok, allow = True, '-' not in version
        for c in cset.split(' '):
            comps, plain = _x_desugar(c)
            for op, v in comps:
                r = _x_cmp(version, v)
                if not {'<': r < 0, '<=': r <= 0, '>': r > 0, '>=': r >= 0, '=': r == 0}[op]:
                    ok = False
                if plain and '-' in v and v.partition('-')[0] == version.partition('-')[0]:
                    allow = True
        if ok and allow:
            return True
    return False""",
        """import random
rng = random.Random(8101)
cores = ['0.0.3', '0.0.4', '0.2.3', '0.2.9', '0.3.0', '1.0.0', '1.2.3', '1.2.4', '1.9.9', '2.0.0', '2.5.0', '3.0.0']
pres = ['', '', '', '-0', '-alpha', '-alpha.1', '-beta', '-rc.1', '-1']
def ver():
    return rng.choice(cores) + rng.choice(pres)
def comp():
    k = rng.random()
    if k < .45:
        return rng.choice(['', '=', '<', '<=', '>', '>=']) + ver()
    if k < .65:
        return rng.choice('^~') + rng.choice(cores)
    return rng.choice(['*', '1.x', '0.x', '2.*', '1.2.x', '0.2.*', '0.0.x'])
for _ in range(8000):
    r = ' || '.join(' '.join(comp() for _ in range(rng.randrange(1, 3))) for _ in range(rng.randrange(1, 3)))
    v = ver()
    got = satisfies(v, r)
    assert got == _x_sat(v, r), (v, r, _x_sat(v, r), got)
print('random_pairs', 8000)""",
        """cases = [('1.2.3', '^1.0.0', True), ('2.0.0', '^1.0.0', False), ('0.3.0', '^0.2.3', False),
    ('0.0.4', '^0.0.3', False), ('1.2.4-beta', '>=1.2.3', False), ('1.2.4-beta', '>=1.2.4-alpha', True),
    ('1.2.5-beta', '>=1.2.4-alpha', False), ('3.0.0', '1.x || >=2.5.0 <3.0.0', False),
    ('1.9.9', '1.x || >=2.5.0 <3.0.0', True), ('1.0.0-rc.1', '*', False), ('2.0.0-0', '<2.0.0', False),
    ('2.0.0-alpha', '^1.0.0', False), ('1.2.3', '1.2.3', True), ('1.2.3-alpha', '1.2.3-alpha', True),
    ('1.2.3-alpha', '<1.2.3', False), ('1.2.3-alpha', '<1.2.3 >=1.2.3-0', True), ('0.2.9', '~0.2.3', True),
    ('0.3.0-0', '~0.2.3', False), ('10.0.0', '>9.99.99', True), ('1.2.3', '>=1.0.0 <1.2.3 || =1.2.3', True),
    ('0.0.3', '^0.0.3', True), ('0.2.3', '0.2.*', True), ('1.0.0', '1.0.x', True), ('1.0.0-alpha.10', '>1.0.0-alpha.9', True)]
for v, r, want in cases:
    assert satisfies(v, r) is want or satisfies(v, r) == want, (v, r, want)
print('boundaries', len(cases))""",
    ],
    "multi_window_limiter": [
        """def _x_admit(times, limits):
    kept, out = [], []
    for t in times:
        ok = all(sum(1 for a in kept if t - w < a <= t) < c for w, c in limits)
        out.append(ok)
        if ok:
            kept.append(t)
    return out
import random
rng = random.Random(8202)
for _ in range(3000):
    times = sorted(rng.randrange(0, 12) for _ in range(rng.randrange(0, 12)))
    limits = [(rng.randrange(1, 6), rng.randrange(0, 4)) for _ in range(rng.randrange(0, 3))]
    ot, ol = times[:], limits[:]
    got = admit(times, limits)
    assert got == _x_admit(times, limits), (times, limits, _x_admit(times, limits), got)
    assert times == ot and limits == ol, 'input mutated'
print('random_cases', 3000)""",
        """assert admit([1, 1, 1], [(10, 2)]) == [True, True, False]
assert admit([0, 5, 10], [(10, 1)]) == [True, False, True]
assert admit([1, 2, 11, 12], [(10, 2)]) == [True, True, True, True]
assert admit([0, 0], [(1, 0)]) == [False, False]
assert admit([3], []) == [True]
assert admit([0, 1, 2, 3], [(2, 1), (100, 3)]) == [True, False, True, False]
assert admit([], [(5, 1)]) == []
assert admit([10**9, 10**9], [(10**9, 1)]) == [True, False]
import time
from collections import deque
times = sorted(__import__('random').Random(8203).randrange(0, 10**6) for _ in range(200000))
limits = [(1000, 50), (60000, 900), (7, 3), (10**9, 10**9), (500000, 20000)]
def _x_fast(times, limits):
    qs = [deque() for _ in limits]; out = []
    for t in times:
        for q, (w, c) in zip(qs, limits):
            while q and q[0] <= t - w:
                q.popleft()
        ok = all(len(q) < c for q, (w, c) in zip(qs, limits))
        if ok:
            for q in qs:
                q.append(t)
        out.append(ok)
    return out
s = time.perf_counter()
got = admit(times, limits)
assert time.perf_counter() - s < 10
assert got == _x_fast(times, limits)
print('boundaries_and_scale', 9)""",
    ],
    "overdraft_ledger": [
        """def _x_ledger(ops, overdraft, fee):
    bal, failed = {}, []
    for i, op in enumerate(ops):
        if op[0] == 'deposit':
            bal[op[1]] = bal.get(op[1], 0) + op[2]
            continue
        src = op[1]
        amount = op[-1]
        ok = src in bal and bal[src] - amount >= -overdraft
        if op[0] == 'transfer' and op[1] == op[2]:
            ok = False
        if ok:
            bal[src] -= amount
            if op[0] == 'transfer':
                bal[op[2]] = bal.get(op[2], 0) + amount
        else:
            failed.append(i)
            if src in bal and bal[src] - fee >= -overdraft:
                bal[src] -= fee
    return bal, failed
import random
rng = random.Random(8303)
for _ in range(4000):
    ops = []
    for _ in range(rng.randrange(0, 10)):
        k = rng.random()
        if k < .3:
            ops.append(('deposit', rng.choice('abc'), rng.randrange(1, 6)))
        elif k < .6:
            ops.append(('withdraw', rng.choice('abc'), rng.randrange(1, 6)))
        else:
            ops.append(('transfer', rng.choice('abc'), rng.choice('abc'), rng.randrange(1, 6)))
    overdraft, fee = rng.randrange(0, 4), rng.randrange(0, 4)
    original = list(ops)
    got = run_ledger(ops, overdraft, fee)
    want = _x_ledger(ops, overdraft, fee)
    assert got[0] == want[0] and list(got[1]) == want[1], (ops, overdraft, fee, want, got)
    assert ops == original, 'input mutated'
print('random_cases', 4000)""",
        """assert run_ledger([('deposit', 'a', 5), ('withdraw', 'a', 8)], 2, 1) == ({'a': 4}, [1])
assert run_ledger([('withdraw', 'x', 1)], 0, 5) == ({}, [0])
assert run_ledger([('deposit', 'a', 1), ('transfer', 'a', 'b', 3)], 2, 1) == ({'a': -2, 'b': 3}, [])
assert run_ledger([('deposit', 'a', 1), ('transfer', 'a', 'a', 1)], 0, 1) == ({'a': 0}, [1])
assert run_ledger([('deposit', 'a', 1), ('transfer', 'a', 'b', 9)], 0, 5) == ({'a': 1}, [1])
assert run_ledger([('transfer', 'x', 'y', 1)], 5, 0) == ({}, [0])
assert run_ledger([], 0, 0) == ({}, [])
assert run_ledger([('deposit', 'a', 1), ('withdraw', 'a', 1), ('withdraw', 'a', 1)], 0, 0) == ({'a': 0}, [2])
import random
rng = random.Random(8304)
ops = [('deposit', 'a%d' % rng.randrange(1000), 5) if rng.random() < .4 else ('transfer', 'a%d' % rng.randrange(1000), 'a%d' % rng.randrange(1000), rng.randrange(1, 9)) for _ in range(200000)]
got = run_ledger(ops, 3, 2)
want = _x_ledger(ops, 3, 2)
assert got[0] == want[0] and list(got[1]) == want[1]
print('boundaries_and_scale', 9)""",
    ],
    "cron_next": [
        """import datetime as _x_dtm
def _x_field(text, lo, hi):
    out = set()
    for item in text.split(','):
        base, slash, step = item.partition('/')
        step = int(step) if step else 1
        if base == '*':
            a, b = lo, hi
        elif '-' in base:
            a, b = map(int, base.split('-'))
        else:
            a = int(base)
            b = hi if slash else a
        out.update(range(a, b + 1, step))
    return out
def _x_next(expr, after):
    f = expr.split(' ')
    mins, hours, doms, mons, dows = (_x_field(f[0], 0, 59), _x_field(f[1], 0, 23),
        _x_field(f[2], 1, 31), _x_field(f[3], 1, 12), _x_field(f[4], 0, 6))
    dom_r, dow_r = f[2] != '*', f[4] != '*'
    limit = after + _x_dtm.timedelta(days=1830)
    day = after.date()
    while _x_dtm.datetime(day.year, day.month, day.day) <= limit:
        dm, dw = day.day in doms, (day.weekday() + 1) % 7 in dows
        ok_day = (dm or dw) if dom_r and dow_r else dm if dom_r else dw if dow_r else True
        if day.month in mons and ok_day:
            for h in sorted(hours):
                for m in sorted(mins):
                    t = _x_dtm.datetime(day.year, day.month, day.day, h, m)
                    if t > after:
                        return t if t <= limit else None
        day += _x_dtm.timedelta(days=1)
    return None""",
        """import random as _x_random
_x_rng = _x_random.Random(8404)
def _x_item(lo, hi):
    k = _x_rng.random()
    if k < .3:
        return '*' + (('/%d' % _x_rng.randrange(1, 5)) if _x_rng.random() < .4 else '')
    a = _x_rng.randrange(lo, hi + 1)
    if k < .6:
        return str(a) + (('/%d' % _x_rng.randrange(1, 4)) if _x_rng.random() < .3 else '')
    b = _x_rng.randrange(a, hi + 1)
    return '%d-%d' % (a, b) + (('/%d' % _x_rng.randrange(1, 4)) if _x_rng.random() < .3 else '')
def _x_fieldtext(lo, hi):
    return ','.join(_x_item(lo, hi) for _ in range(_x_rng.randrange(1, 3)))
for _x_i in range(700):
    _x_expr = ' '.join([_x_fieldtext(0, 59), _x_fieldtext(0, 23),
        _x_fieldtext(1, 31) if _x_rng.random() < .6 else '*',
        _x_fieldtext(1, 12) if _x_rng.random() < .5 else '*',
        _x_fieldtext(0, 6) if _x_rng.random() < .6 else '*'])
    _x_after = _x_dtm.datetime(2023, 1, 1) + _x_dtm.timedelta(minutes=_x_rng.randrange(0, 2 * 525600), seconds=_x_rng.choice([0, 0, 30]))
    _x_got = next_fire(_x_expr, _x_after)
    assert _x_got == _x_next(_x_expr, _x_after), (_x_expr, _x_after, _x_next(_x_expr, _x_after), _x_got)
print('random_exprs', 700)""",
        """_x_d = _x_dtm.datetime
_x_cases = [('*/15 * * * *', _x_d(2024, 1, 1, 0, 0), _x_d(2024, 1, 1, 0, 15)),
    ('0 0 13 * 5', _x_d(2024, 1, 1), _x_d(2024, 1, 5, 0, 0)),
    ('0 0 30 2 *', _x_d(2024, 1, 1), None),
    ('30 9 * * 1-5', _x_d(2024, 1, 6, 12, 0), _x_d(2024, 1, 8, 9, 30)),
    ('0 12 * * *', _x_d(2024, 1, 1, 12, 0, 30), _x_d(2024, 1, 2, 12, 0)),
    ('0 0 29 2 *', _x_d(2024, 3, 1), _x_d(2028, 2, 29, 0, 0)),
    ('0 0 * * 0', _x_d(2024, 1, 1), _x_d(2024, 1, 7, 0, 0)),
    ('0 0 1 * */2', _x_d(2024, 1, 1), _x_d(2024, 1, 2, 0, 0)),
    ('5/20 * * * *', _x_d(2024, 1, 1, 0, 6), _x_d(2024, 1, 1, 0, 25)),
    ('59 23 31 12 *', _x_d(2024, 12, 31, 23, 59), _x_d(2025, 12, 31, 23, 59)),
    ('0 0 31 4,6,9,11 *', _x_d(2024, 1, 1), None)]
for _x_expr, _x_after, _x_want in _x_cases:
    assert next_fire(_x_expr, _x_after) == _x_want, (_x_expr, _x_after, _x_want, next_fire(_x_expr, _x_after))
print('boundaries', len(_x_cases))""",
    ],
    "phaseout_tax": [
        """from fractions import Fraction
def _x_tax(income, brackets, deduction, phase_start):
    eff = max(0, deduction - max(0, income - phase_start) // 2)
    taxable = max(0, income - eff)
    total, prev = Fraction(0), 0
    for upper, rate in brackets:
        top = taxable if upper is None else min(taxable, upper)
        if top > prev:
            total += Fraction((top - prev) * rate, 10000)
        if upper is not None:
            prev = max(prev, upper)
    return int(total + Fraction(1, 2)) if total >= 0 else 0
import random
rng = random.Random(8505)
for _ in range(6000):
    bounds = sorted(rng.sample(range(1, 60), rng.randrange(0, 4)))
    brackets = [(b, rng.randrange(0, 10001, rng.choice([1, 25, 500]))) for b in bounds] + [(None, rng.randrange(0, 10001, rng.choice([1, 25, 500])))]
    income, deduction, phase = rng.randrange(0, 90), rng.randrange(0, 40), rng.randrange(0, 90)
    original = list(brackets)
    got = tax_due(income, brackets, deduction, phase)
    want = _x_tax(income, brackets, deduction, phase)
    assert got == want and type(got) is int, (income, brackets, deduction, phase, want, got)
    assert brackets == original, 'input mutated'
print('random_cases', 6000)""",
        """assert tax_due(100000, [(50000, 1000), (None, 2000)], 0, 10**15) == 15000
assert tax_due(10005, [(None, 1000)], 0, 10**15) == 1001
assert tax_due(1000, [(None, 1000)], 300, 600) == 90
assert tax_due(5, [(10, 1000), (None, 1000)], 0, 0) == 1
assert tax_due(15, [(10, 500), (None, 500)], 0, 10**15) == 1
assert tax_due(0, [(None, 10000)], 5, 0) == 0
assert tax_due(3, [(1, 5000), (2, 5000), (None, 5000)], 0, 10**15) == 2
assert tax_due(10**15, [(None, 3333)], 10**12, 0) == 333300000000000
assert tax_due(10**15 - 1, [(None, 1)], 0, 10**15) == 100000000000
assert tax_due(25, [(10, 1250), (20, 1250), (None, 1250)], 0, 10**15) == 3
assert tax_due(7, [(None, 5000)], 4, 3) == 3
print('boundaries', 11)""",
    ],
}
