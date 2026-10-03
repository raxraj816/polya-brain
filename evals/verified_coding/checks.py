"""Independent scoring checks, withheld from every solver arm and from PolyaBrain.

Each list item is one sandbox test string (at most 2000 characters). Items share
one interpreter, so an earlier item may define a private ``_x_*`` reference that
later items use. References are agent-authored and validated against brute force
and mutants by ``validate_checks.py``; they are not an external judge.
"""

from __future__ import annotations

CHECKS: dict[str, list[str]] = {
    "lower_median": [
        """import random
rng = random.Random(7101)
for _ in range(3000):
    a = sorted(rng.randrange(-20, 21) for _ in range(rng.randrange(0, 9)))
    b = sorted(rng.randrange(-20, 21) for _ in range(rng.randrange(0 if a else 1, 9)))
    oa, ob = a[:], b[:]
    m = sorted(a + b)
    want = m[(len(m) - 1) // 2]
    got = lower_median(a, b)
    assert got == want and isinstance(got, int) and not isinstance(got, bool), (a, b, want, got)
    assert a == oa and b == ob, 'input mutated'
print('random_cases', 3000)""",
        """assert lower_median([1, 3], [2]) == 2
assert lower_median([1, 2], [3, 4]) == 2
assert lower_median([], [5]) == 5
assert lower_median([7], []) == 7
assert lower_median([4, 4], [4]) == 4
assert lower_median([-10**9, 10**9], [0, 0]) == 0
assert lower_median([1, 2, 3, 4], []) == 2
assert lower_median([10**9] * 3, [-10**9] * 3) == -10**9
print('boundaries', 8)""",
        """import time
a = list(range(0, 200000, 2)); b = list(range(1, 200000, 2))
c = [5]; d = list(range(200000))
t = time.perf_counter()
for _ in range(3000):
    assert lower_median(a, b) == 99999
    assert lower_median(c, d) == 99999
    assert lower_median(d, c) == 99999
elapsed = time.perf_counter() - t
assert elapsed < 6, elapsed
print('scale_seconds', round(elapsed, 3))""",
    ],
    "dl_distance": [
        """def _x_dl(a, b):
    n, m = len(a), len(b)
    inf = n + m
    d = [[0] * (m + 2) for _ in range(n + 2)]
    d[0][0] = inf
    for i in range(n + 1):
        d[i + 1][0] = inf; d[i + 1][1] = i
    for j in range(m + 1):
        d[0][j + 1] = inf; d[1][j + 1] = j
    last = {}
    for i in range(1, n + 1):
        db = 0
        for j in range(1, m + 1):
            i1 = last.get(b[j - 1], 0); j1 = db
            cost = 1
            if a[i - 1] == b[j - 1]:
                cost = 0; db = j
            d[i + 1][j + 1] = min(d[i][j] + cost, d[i + 1][j] + 1, d[i][j + 1] + 1,
                                  d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1))
        last[a[i - 1]] = i
    return d[n + 1][m + 1]
import random
rng = random.Random(7202)
for _ in range(2500):
    a = ''.join(rng.choice('abc') for _ in range(rng.randrange(7)))
    b = ''.join(rng.choice('abc') for _ in range(rng.randrange(7)))
    got = dl_distance(a, b)
    assert got == _x_dl(a, b), (a, b, _x_dl(a, b), got)
print('random_cases', 2500)""",
        """assert dl_distance('', 'abc') == 3
assert dl_distance('abc', '') == 3
assert dl_distance('', '') == 0
assert dl_distance('abc', 'acb') == 1
assert dl_distance('ca', 'abc') == 2
assert dl_distance('kitten', 'sitting') == 3
assert dl_distance('abcdef', 'badcfe') == 3
assert dl_distance('a\\u00e9\\U0001F600', '\\u00e9a\\U0001F600') == 1
assert dl_distance('Ab', 'ab') == 1
assert dl_distance('abc', 'ca') == 2
print('boundaries', 10)""",
        """import random
rng = random.Random(7203)
a = ''.join(rng.choice('abcd') for _ in range(400))
b = ''.join(rng.choice('abcd') for _ in range(400))
assert dl_distance(a, b) == _x_dl(a, b)
assert dl_distance('x' * 600, 'y' * 600) == 600
print('scale', 1)""",
    ],
    "semver_compare": [
        """def _x_sv(a, b):
    def key(v):
        v = v.split('+', 1)[0]
        core, _, pre = v.partition('-')
        return tuple(map(int, core.split('.'))), (pre.split('.') if pre else None)
    (ca, pa), (cb, pb) = key(a), key(b)
    if ca != cb:
        return -1 if ca < cb else 1
    if pa is None or pb is None:
        if pa is None and pb is None:
            return 0
        return 1 if pa is None else -1
    for x, y in zip(pa, pb):
        if x == y:
            continue
        xd, yd = x.isdigit(), y.isdigit()
        if xd and yd:
            return -1 if int(x) < int(y) else 1
        if xd or yd:
            return -1 if xd else 1
        return -1 if x < y else 1
    return (len(pa) > len(pb)) - (len(pa) < len(pb))
import random
rng = random.Random(7303)
nums = ['0', '1', '2', '10', '99999999999999999999']
pre = ['alpha', 'beta', 'rc', '0', '1', '2', '10', 'x-y', '-', 'a1', '1a', '--', '0a', 'Alpha', 'ALPHA', 'alpha-1']
build = ['001', 'build-5', 'x', 'exp', 'sha-5114f85', '0']
def gen():
    v = '.'.join(rng.choice(nums[:3] if rng.random() < .7 else nums) for _ in range(3))
    if rng.random() < .6:
        v += '-' + '.'.join(rng.choice(pre) for _ in range(rng.randrange(1, 4)))
    if rng.random() < .4:
        v += '+' + '.'.join(rng.choice(build) for _ in range(rng.randrange(1, 3)))
    return v
for _ in range(6000):
    a, b = gen(), gen()
    got = compare_versions(a, b)
    assert got == _x_sv(a, b), (a, b, _x_sv(a, b), got)
print('random_pairs', 6000)""",
        """chain = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta',
         '1.0.0-beta.2', '1.0.0-beta.11', '1.0.0-rc.1', '1.0.0', '1.0.1-0', '1.0.1-1',
         '1.0.1-1a', '1.0.1-A', '1.0.1-a', '1.0.1', '1.1.0', '2.0.0', '10.0.0']
for i, x in enumerate(chain):
    for j, y in enumerate(chain):
        assert compare_versions(x, y) == (i > j) - (i < j), (x, y)
assert compare_versions('1.0.0+build-5', '1.0.0') == 0
assert compare_versions('1.0.0+build-5', '1.0.0-5') == 1
assert compare_versions('1.0.0-x-y+a-b', '1.0.0-x-y') == 0
assert compare_versions('1.0.0-x-y', '1.0.0-x') == 1
assert compare_versions('1.0.0-99999999999999999999', '1.0.0-100000000000000000000') == -1
assert compare_versions('1.0.0-alpha+001', '1.0.0-alpha+002') == 0
print('ordered_chain', len(chain))""",
    ],
    "sticky_cache": [
        """def _x_cache(cap, ops):
    from collections import OrderedDict
    c = OrderedDict(); out = []
    for op in ops:
        if op[0] == 'get':
            if op[1] in c:
                c.move_to_end(op[1]); out.append(c[op[1]])
            else:
                out.append(-1)
        elif cap > 0:
            if op[1] in c:
                c[op[1]] = op[2]
            else:
                c[op[1]] = op[2]
                if len(c) > cap:
                    c.popitem(last=False)
    return out
import random
rng = random.Random(7404)
for _ in range(3000):
    cap = rng.randrange(0, 5)
    ops = [('get', rng.randrange(6)) if rng.random() < .45 else ('put', rng.randrange(6), rng.randrange(-3, 50)) for _ in range(rng.randrange(0, 30))]
    original = list(ops)
    got = run_cache(cap, ops)
    assert got == _x_cache(cap, ops), (cap, ops, _x_cache(cap, ops), got)
    assert ops == original, 'input mutated'
print('random_cases', 3000)""",
        """assert run_cache(2, [('put',1,1),('put',2,2),('put',1,10),('put',3,3),('get',1),('get',2),('get',3)]) == [-1, 2, 3]
assert run_cache(0, [('put',1,1),('get',1)]) == [-1]
assert run_cache(1, [('put',1,1),('put',1,2),('get',1),('put',2,3),('get',1),('get',2)]) == [2, -1, 3]
assert run_cache(2, [('put',1,1),('put',2,2),('get',1),('put',2,20),('put',3,3),('get',1),('get',2),('get',3)]) == [1, 1, -1, 3]
assert run_cache(3, []) == []
print('boundaries', 5)""",
        """import random, time
rng = random.Random(7405)
ops = [('get', rng.randrange(80000)) if rng.random() < .5 else ('put', rng.randrange(80000), rng.randrange(10**6)) for _ in range(200000)]
t = time.perf_counter()
got = run_cache(50000, ops)
elapsed = time.perf_counter() - t
assert got == _x_cache(50000, ops)
assert elapsed < 8, elapsed
print('scale_seconds', round(elapsed, 3))""",
    ],
    "largest_remainder": [
        """def _x_alloc(total, w):
    n = len(w)
    if n == 0:
        return []
    s = sum(w)
    if s == 0:
        q, r = divmod(total, n)
        return [q + (i < r) for i in range(n)]
    base = [total * x // s for x in w]
    order = sorted(range(n), key=lambda i: (-(total * w[i] % s), -w[i], i))
    for i in order[:total - sum(base)]:
        base[i] += 1
    return base
import random
rng = random.Random(7505)
for _ in range(4000):
    total = rng.randrange(0, 60)
    w = [rng.randrange(0, 6) for _ in range(rng.randrange(0, 7))]
    original = w[:]
    got = allocate(total, w)
    assert got == _x_alloc(total, w), (total, w, _x_alloc(total, w), got)
    assert w == original, 'input mutated'
print('random_cases', 4000)""",
        """assert allocate(100, [1, 1, 1]) == [34, 33, 33]
assert allocate(10, [1, 2]) == [3, 7]
assert allocate(5, [0, 0]) == [3, 2]
assert allocate(2, [1, 3]) == [0, 2]
assert allocate(7, []) == []
assert allocate(0, [0]) == [0]
assert allocate(1, [5, 0, 5]) == [1, 0, 0]
assert allocate(3, [1, 2, 1, 2]) == [1, 1, 0, 1]
print('boundaries', 8)""",
        """import random
rng = random.Random(7506)
w = [rng.randrange(0, 10**9 + 1) for _ in range(100000)]
for total in (10**12, 10**12 - 1, 999999999989):
    got = allocate(total, w)
    assert got == _x_alloc(total, w)
    assert sum(got) == total
w = [10**9] * 99999 + [10**9 - 1]
assert allocate(10**12, w) == _x_alloc(10**12, w)
print('large_exact', 4)""",
    ],
    "parse_duration": [
        """def _x_pd(s):
    unit = {'w': 604800, 'd': 86400, 'h': 3600, 'm': 60, 's': 1}
    order = 'wdhms'
    i, n, total, last = 0, len(s), 0, -1
    if n == 0:
        return None
    while i < n:
        if i > 0 and s[i] == ' ':
            i += 1
        j = i
        while j < n and s[j] in '0123456789':
            j += 1
        if j == i or j >= n or s[j] not in unit:
            return None
        k = order.index(s[j])
        if k <= last:
            return None
        last = k
        total += int(s[i:j]) * unit[s[j]]
        i = j + 1
    return total
import random
rng = random.Random(7606)
noise = '0123456789wdhms ' * 3 + 'H\\t-.+x\\u0661\\u00b2'
for _ in range(6000):
    if rng.random() < .5:
        parts = [str(rng.randrange(0, 1000)).zfill(rng.randrange(1, 4)) + u for u in 'wdhms' if rng.random() < .5]
        s = ''.join(p + rng.choice(['', ' ', ' ', '  ']) for p in parts).rstrip(' ') if rng.random() < .9 else ' '.join(parts) + ' '
        if rng.random() < .2 and parts:
            s = s.replace(rng.choice('wdhms'), rng.choice('wdhms'), 1)
    else:
        s = ''.join(rng.choice(noise) for _ in range(rng.randrange(0, 10)))
    got = parse_duration(s)
    assert got == _x_pd(s), (s, _x_pd(s), got)
print('random_strings', 6000)""",
        """cases = {'1h30m': 5400, '1h 30m': 5400, '90m': 5400, '0s': 0, '007s': 7, '30m1h': None,
         '1h  30m': None, '1H': None, '': None, '1h30': None, ' 1h': None, '1h ': None,
         '1w1d1h1m1s': 694861, '1w 1d 1h 1m 1s': 694861, '1h1h': None, '1s1m': None,
         '-1s': None, '1.5h': None, '\\u0661s': None, '\\u00b2s': None, 'h': None, '1': None,
         '1h\\t30m': None, '99999999999999999999w': 99999999999999999999 * 604800, ' ': None,
         '0w0d0h0m0s': 0, '1d 2h3m': 93780}
for s, want in cases.items():
    assert parse_duration(s) == want, (s, want, parse_duration(s))
print('boundaries', len(cases))""",
    ],
    "observed_business_days": [
        """from datetime import date, timedelta
def _x_obs(h):
    return h - timedelta(1) if h.weekday() == 5 else h + timedelta(1) if h.weekday() == 6 else h
def _x_bd(s, e, hol):
    obs = {_x_obs(h) for h in hol}
    n = (e - s).days
    if n <= 0:
        return 0
    full, rem = divmod(n, 7)
    c = full * 5 + sum((s.weekday() + k) % 7 < 5 for k in range(rem))
    return c - sum(1 for d in obs if s <= d < e)
import random
rng = random.Random(7707)
for _ in range(2500):
    s = date(2023, 1, 1) + timedelta(rng.randrange(900))
    e = s + timedelta(rng.randrange(-3, 40))
    hol = [s + timedelta(rng.randrange(-6, 46)) for _ in range(rng.randrange(0, 7))]
    original = hol[:]
    want = sum(1 for k in range((e - s).days) if (s + timedelta(k)).weekday() < 5 and s + timedelta(k) not in {_x_obs(h) for h in hol})
    assert want == _x_bd(s, e, hol)
    got = business_days(s, e, hol)
    assert got == want, (s, e, hol, want, got)
    assert hol == original, 'input mutated'
print('random_cases', 2500)""",
        """from datetime import date
assert business_days(date(2024,1,1), date(2024,1,8), []) == 5
assert business_days(date(2024,1,1), date(2024,1,8), [date(2024,1,6)]) == 4
assert business_days(date(2024,1,8), date(2024,1,9), [date(2024,1,7)]) == 0
assert business_days(date(2024,1,9), date(2024,1,1), []) == 0
assert business_days(date(2024,1,5), date(2024,1,6), [date(2024,1,5), date(2024,1,6), date(2024,1,6)]) == 0
assert business_days(date(2024,1,1), date(2024,1,6), [date(2023,12,31)]) == 4
assert business_days(date(2024,1,6), date(2024,1,8), [date(2024,1,6), date(2024,1,7)]) == 0
assert business_days(date(1900,1,1), date(1900,1,1), []) == 0
print('boundaries', 8)""",
        """import random, time
from datetime import date, timedelta
rng = random.Random(7708)
s, e = date(1900, 1, 1), date(2100, 12, 31)
hol = [s + timedelta(rng.randrange((e - s).days + 1)) for _ in range(100000)]
assert business_days(s, e, hol) == _x_bd(s, e, hol)
assert business_days(date(1950, 3, 4), date(2090, 7, 9), hol) == _x_bd(date(1950, 3, 4), date(2090, 7, 9), hol)
t = time.perf_counter()
for k in range(2000):
    a = s + timedelta(k)
    assert business_days(a, e, []) == _x_bd(a, e, [])
elapsed = time.perf_counter() - t
assert elapsed < 8, elapsed
print('scale_seconds', round(elapsed, 3))""",
    ],
    "torus_islands": [
        """def _x_isl(g):
    R, C = len(g), len(g[0])
    seen = [[False] * C for _ in range(R)]
    count = 0
    for r in range(R):
        for c in range(C):
            if g[r][c] == '#' and not seen[r][c]:
                count += 1
                seen[r][c] = True
                stack = [(r, c)]
                while stack:
                    y, x = stack.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = (y + dy) % R, (x + dx) % C
                            if g[ny][nx] == '#' and not seen[ny][nx]:
                                seen[ny][nx] = True
                                stack.append((ny, nx))
    return count
import random
rng = random.Random(7809)
for _ in range(3000):
    R, C, p = rng.randrange(1, 7), rng.randrange(1, 7), rng.random() * .6
    g = [''.join('#' if rng.random() < p else '.' for _ in range(C)) for _ in range(R)]
    original = g[:]
    got = count_islands(g)
    assert got == _x_isl(g), (g, _x_isl(g), got)
    assert g == original, 'input mutated'
print('random_grids', 3000)""",
        """assert count_islands(['#..', '...', '..#']) == 1
assert count_islands(['#.#']) == 1
assert count_islands(['#.#.']) == 2
assert count_islands(['....']) == 0
assert count_islands(['#']) == 1
assert count_islands(['.']) == 0
assert count_islands(['#', '.', '#']) == 1
assert count_islands(['#', '.', '#', '.']) == 2
assert count_islands(['#...', '....', '..#.', '....']) == 2
assert count_islands(['#' * 250000]) == 1
assert count_islands(['#.' * 125000]) == 125000
assert count_islands(['#'] * 250000) == 1
print('boundaries', 12)""",
        """import random
rng = random.Random(7810)
g = [''.join('#' if rng.random() < .45 else '.' for _ in range(500)) for _ in range(500)]
assert count_islands(g) == _x_isl(g)
snake = [('#' * 499 + '.') if r % 4 == 0 else ('.' * 499 + '#') if r % 4 == 1 else ('#' + '.' * 498 + '#')[::-1] if r % 4 == 2 else ('#' + '.' * 499) for r in range(500)]
assert count_islands(snake) == _x_isl(snake)
print('scale', 2)""",
    ],
    "cleanup_meetings": [
        """def _x_greedy(ms, gap):
    count, last = 0, None
    for s, e in sorted(ms, key=lambda x: x[1]):
        if last is None or s > last + gap:
            count += 1
            last = e
    return count
def _x_brute(ms, gap):
    best = 0
    for mask in range(1 << len(ms)):
        chosen = sorted((ms[i] for i in range(len(ms)) if mask >> i & 1))
        if all(chosen[k + 1][0] > chosen[k][1] + gap for k in range(len(chosen) - 1)):
            best = max(best, len(chosen))
    return best
import random
rng = random.Random(7911)
for _ in range(1500):
    ms = []
    for _ in range(rng.randrange(0, 9)):
        s = rng.randrange(-5, 11)
        ms.append((s, s + rng.randrange(0, 5)))
    gap = rng.randrange(0, 4)
    original = ms[:]
    want = _x_brute(ms, gap)
    assert want == _x_greedy(ms, gap)
    got = max_meetings(ms, gap)
    assert got == want, (ms, gap, want, got)
    assert ms == original, 'input mutated'
print('random_cases', 1500)""",
        """assert max_meetings([(1, 2), (2, 3)], 0) == 1
assert max_meetings([(1, 2), (3, 4)], 0) == 2
assert max_meetings([(1, 2), (3, 4)], 1) == 1
assert max_meetings([(1, 2), (4, 4)], 1) == 2
assert max_meetings([], 5) == 0
assert max_meetings([(3, 3), (3, 3)], 0) == 1
assert max_meetings([(0, 0), (1, 1), (2, 2)], 0) == 3
assert max_meetings([(-10**9, 10**9), (0, 0)], 10**9) == 1
assert max_meetings([(-10**9, -10**9), (10**9, 10**9)], 10**9) == 2
assert max_meetings([(-10**9, -10**9), (0, 0)], 10**9) == 1
print('boundaries', 10)""",
        """import random
rng = random.Random(7912)
ms = []
for _ in range(200000):
    s = rng.randrange(-10**9, 10**9 - 1000)
    ms.append((s, s + rng.randrange(0, 1000)))
for gap in (0, 7, 5000):
    assert max_meetings(ms, gap) == _x_greedy(ms, gap)
print('scale', 3)""",
    ],
    "hard_wrap": [
        """def _x_wrap(text, width):
    lines, cur = [], ''
    for w in [x for x in text.split(' ') if x]:
        if len(w) > width:
            if cur:
                lines.append(cur)
            while len(w) > width:
                lines.append(w[:width])
                w = w[width:]
            cur = w
        elif not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
import random
rng = random.Random(8013)
alphabet = 'ab' * 6 + ' ' * 5 + '\\t\\n\\u00a0x'
for _ in range(5000):
    text = ''.join(rng.choice(alphabet) for _ in range(rng.randrange(0, 25)))
    width = rng.randrange(1, 8)
    got = wrap(text, width)
    assert got == _x_wrap(text, width), (text, width, _x_wrap(text, width), got)
print('random_texts', 5000)""",
        """assert wrap('the quick brown fox', 10) == ['the quick', 'brown fox']
assert wrap('  a  b ', 3) == ['a b']
assert wrap('abcdefgh ij', 3) == ['abc', 'def', 'gh', 'ij']
assert wrap('ab abcdefg', 3) == ['ab', 'abc', 'def', 'g']
assert wrap('', 5) == []
assert wrap('     ', 5) == []
assert wrap('abcdef', 3) == ['abc', 'def']
assert wrap('abcdef g', 3) == ['abc', 'def', 'g']
assert wrap('abcd e f', 3) == ['abc', 'd e', 'f']
assert wrap('a\\tb c', 3) == ['a\\tb', 'c']
assert wrap('a\\u00a0b c', 5) == ['a\\u00a0b c']
assert wrap('x', 1) == ['x']
print('boundaries', 12)""",
        """import random
rng = random.Random(8014)
text = ''.join(rng.choice('abcdefg   ') for _ in range(100000))
for width in (1, 7, 1000):
    assert wrap(text, width) == _x_wrap(text, width)
print('scale', 3)""",
    ],
    "kth_distinct": [
        """import random
rng = random.Random(9101)
for _ in range(3000):
    nums = [rng.randrange(-5, 6) for _ in range(rng.randrange(0, 10))]
    k = rng.randrange(-1, 8)
    original = nums[:]
    values = sorted(set(nums), reverse=True)
    want = values[k - 1] if 1 <= k <= len(values) else None
    got = kth_distinct(nums, k)
    assert got == want, (nums, k, want, got)
    assert nums == original, 'input mutated'
assert kth_distinct(list(range(200000)) * 2, 200000) == 0
print('random_cases', 3000)""",
    ],
    "merge_labeled": [
        """def _x_merge(ranges):
    out = []
    for label in sorted({r[2] for r in ranges}):
        items = sorted((lo, hi) for lo, hi, l in ranges if l == label)
        cur = None
        for lo, hi in items:
            if cur and lo <= cur[1] + 1:
                cur[1] = max(cur[1], hi)
            else:
                if cur:
                    out.append((cur[0], cur[1], label))
                cur = [lo, hi]
        if cur:
            out.append((cur[0], cur[1], label))
    return sorted(out)
import random
rng = random.Random(9202)
for _ in range(3000):
    ranges = []
    for _ in range(rng.randrange(0, 8)):
        lo = rng.randrange(-5, 8)
        ranges.append((lo, lo + rng.randrange(0, 4), rng.choice('ab')))
    original = ranges[:]
    got = merge_labeled(ranges)
    assert got == _x_merge(ranges), (ranges, _x_merge(ranges), got)
    assert ranges == original, 'input mutated'
print('random_cases', 3000)""",
    ],
    "strict_roman": [
        """def _x_enc(n):
    out = ''
    for v, s in ((1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')):
        while n >= v:
            out += s; n -= v
    return out
table = {_x_enc(n): n for n in range(1, 4000)}
for s, n in table.items():
    assert roman_value(s) == n, (s, n)
import random
rng = random.Random(9303)
for _ in range(20000):
    s = ''.join(rng.choice('IVXLCDM') for _ in range(rng.randrange(0, 9)))
    assert roman_value(s) == table.get(s), (s, table.get(s))
for s in ('iv', 'MMMM', 'IIII', 'IC', 'XM', 'IIV', 'VV', '', ' IV', 'IV '):
    assert roman_value(s) is None, s
print('table_and_random', 3999 + 20000)""",
    ],
    "csv_fields": [
        '''def _x_csv(line):
    out, i, n = [], 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    return None
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"'); i += 2; continue
                    i += 1
                    break
                buf.append(line[i]); i += 1
            out.append(''.join(buf))
            if i == n:
                return out
            if line[i] != ',':
                return None
            i += 1
        else:
            j = line.find(',', i)
            if j == -1:
                out.append(line[i:])
                return out
            out.append(line[i:j]); i = j + 1
import random
rng = random.Random(9404)
for _ in range(8000):
    line = ''.join(rng.choice('a,"" ') for _ in range(rng.randrange(0, 12)))
    got = csv_fields(line)
    assert got == _x_csv(line), (line, _x_csv(line), got)
big = ','.join(['"x,""y"""', 'plain', ''] * 20000)
assert csv_fields(big) == _x_csv(big)
print('random_lines', 8000)''',
        '''cases = {'a,b': ['a', 'b'], '': [''], 'a,': ['a', ''], '"x,y",z': ['x,y', 'z'],
         '"a""b"': ['a"b'], 'a"b,c': ['a"b', 'c'], '"ab"c': None, '"ab': None,
         ' "a"': [' "a"'], ',': ['', ''], '""': [''], '"",""': ['', ''], '""""': ['"'],
         '"a",': ['a', ''], '"a" ,b': None, '"': None, 'a""b': ['a""b']}
for line, want in cases.items():
    assert csv_fields(line) == want, (line, want, csv_fields(line))
print('boundaries', len(cases))''',
    ],
    "integer_gaps": [
        """def _x_gaps(lo, hi, cov):
    s = set()
    for a, b in cov:
        s.update(range(max(a, lo), min(b, hi) + 1))
    out, start = [], None
    for x in range(lo, hi + 2):
        if x <= hi and x not in s:
            if start is None:
                start = x
        elif start is not None:
            out.append((start, x - 1)); start = None
    return out
def _x_fast(lo, hi, cov):
    out, cur = [], lo
    for a, b in sorted(cov):
        if b < cur or a > hi:
            continue
        if a > cur:
            out.append((cur, a - 1))
        cur = max(cur, b + 1)
        if cur > hi:
            return out
    if cur <= hi:
        out.append((cur, hi))
    return out
import random
rng = random.Random(9505)
for _ in range(4000):
    lo = rng.randrange(-6, 6); hi = lo + rng.randrange(0, 12)
    cov = []
    for _ in range(rng.randrange(0, 6)):
        a = rng.randrange(-10, 18); cov.append((a, a + rng.randrange(0, 5)))
    original = cov[:]
    want = _x_gaps(lo, hi, cov)
    assert want == _x_fast(lo, hi, cov)
    got = gaps(lo, hi, cov)
    assert got == want, (lo, hi, cov, want, got)
    assert cov == original, 'input mutated'
cov = [(a, a + rng.randrange(0, 50)) for a in (rng.randrange(-10**9, 10**9) for _ in range(100000))]
assert gaps(-10**9, 10**9, cov) == _x_fast(-10**9, 10**9, cov)
assert gaps(0, 10, [(1, 3), (4, 6)]) == [(0, 0), (7, 10)]
assert gaps(-10**9, 10**9, []) == [(-10**9, 10**9)]
print('random_cases', 4000)""",
    ],
    "dense_leaderboard": [
        """def _x_lb(scores):
    best = {}
    for name, pts in scores:
        best[name] = max(pts, best.get(name, pts))
    rows = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))
    out, rank, prev = [], 0, None
    for name, pts in rows:
        if pts != prev:
            rank += 1; prev = pts
        out.append((rank, name, pts))
    return out
import random
rng = random.Random(9606)
names = ['al', 'bo', 'Cy', 'cy', 'a', 'Zed', 'amy', 'b']
for _ in range(4000):
    scores = [(rng.choice(names), rng.randrange(-3, 4)) for _ in range(rng.randrange(0, 9))]
    original = scores[:]
    got = leaderboard(scores)
    assert got == _x_lb(scores), (scores, _x_lb(scores), got)
    assert scores == original, 'input mutated'
big = [('p%d' % rng.randrange(50000), rng.randrange(-10**9, 10**9)) for _ in range(200000)]
assert leaderboard(big) == _x_lb(big)
print('random_cases', 4000)""",
    ],
}
