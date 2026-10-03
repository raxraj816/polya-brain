"""Check-validation solutions: one correct implementation and plausible mutants per case.

Never shown to solvers. A check set is only trusted when every correct solution
passes and every mutant (a realistic misreading of the spec) fails.
"""

from __future__ import annotations

CORRECT: dict[str, str] = {
    "lower_median": """
def lower_median(a, b):
    if len(a) > len(b):
        a, b = b, a
    m, n = len(a), len(b)
    k = (m + n - 1) // 2 + 1  # 1-based rank of the lower median
    lo, hi = max(0, k - n), min(k, m)
    while lo <= hi:
        i = (lo + hi) // 2
        j = k - i
        a_left = a[i - 1] if i > 0 else float('-inf')
        a_right = a[i] if i < m else float('inf')
        b_left = b[j - 1] if j > 0 else float('-inf')
        b_right = b[j] if j < n else float('inf')
        if a_left > b_right:
            hi = i - 1
        elif b_left > a_right:
            lo = i + 1
        else:
            return a_left if a_left > b_left else b_left
""",
    "dl_distance": """
def dl_distance(a, b):
    n, m = len(a), len(b)
    INF = n + m
    H = [[INF] * (m + 2) for _ in range(n + 2)]
    for i in range(n + 1):
        H[i + 1][1] = i
    for j in range(m + 1):
        H[1][j + 1] = j
    da = {}
    for i in range(1, n + 1):
        db = 0
        for j in range(1, m + 1):
            k = da.get(b[j - 1], 0)
            l = db
            if a[i - 1] == b[j - 1]:
                cost = 0
                db = j
            else:
                cost = 1
            H[i + 1][j + 1] = min(H[i][j] + cost, H[i + 1][j] + 1, H[i][j + 1] + 1,
                                  H[k][l] + (i - k - 1) + 1 + (j - l - 1))
        da[a[i - 1]] = i
    return H[n + 1][m + 1]
""",
    "semver_compare": """
import re
def compare_versions(a, b):
    def parse(v):
        m = re.fullmatch(r'(\\d+)\\.(\\d+)\\.(\\d+)(?:-([0-9A-Za-z.-]+))?(?:\\+[0-9A-Za-z.-]+)?', v)
        core = tuple(int(m.group(i)) for i in (1, 2, 3))
        pre = m.group(4)
        return core, (pre.split('.') if pre is not None else None)
    (ca, pa), (cb, pb) = parse(a), parse(b)
    if ca != cb:
        return (ca > cb) - (ca < cb)
    if pa is None and pb is None:
        return 0
    if pa is None:
        return 1
    if pb is None:
        return -1
    def key(x):
        return (0, int(x), '') if x.isdigit() else (1, 0, x)
    for x, y in zip(pa, pb):
        kx, ky = key(x), key(y)
        if kx != ky:
            return -1 if kx < ky else 1
    return (len(pa) > len(pb)) - (len(pa) < len(pb))
""",
    "sticky_cache": """
def run_cache(capacity, ops):
    store = {}
    order = {}  # dict preserves insertion order; recency via re-insertion
    out = []
    for op in ops:
        if op[0] == 'get':
            k = op[1]
            if k in store:
                del order[k]
                order[k] = None
                out.append(store[k])
            else:
                out.append(-1)
        else:
            _, k, v = op
            if capacity == 0:
                continue
            if k in store:
                store[k] = v
                continue
            store[k] = v
            order[k] = None
            if len(store) > capacity:
                victim = next(iter(order))
                del order[victim]
                del store[victim]
    return out
""",
    "largest_remainder": """
def allocate(total, weights):
    n = len(weights)
    if n == 0:
        return []
    W = sum(weights)
    if W == 0:
        return [total // n + (1 if i < total % n else 0) for i in range(n)]
    result, rems = [], []
    for i, w in enumerate(weights):
        q, r = divmod(total * w, W)
        result.append(q)
        rems.append((r, w, -i))
    left = total - sum(result)
    for r, w, neg_i in sorted(rems, reverse=True)[:left]:
        result[-neg_i] += 1
    return result
""",
    "parse_duration": """
import re
_PAT = re.compile(r'(?:([0-9]+)w)?(?:([0-9]+)d)?(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?', re.ASCII)
def parse_duration(s):
    if not s or s[0] == ' ' or s[-1] == ' ' or '  ' in s:
        return None
    pieces = s.split(' ')
    # Each space must sit between two components: the text before it must end in a unit.
    compact = ''.join(pieces)
    if any(not p or p[-1] not in 'wdhms' for p in pieces):
        return None
    m = _PAT.fullmatch(compact)
    if not m or not compact:
        return None
    total = 0
    for g, mult in zip(m.groups(), (604800, 86400, 3600, 60, 1)):
        if g is not None:
            total += int(g) * mult
    return total
""",
    "observed_business_days": """
from datetime import date, timedelta
def business_days(start, end, holidays):
    days = (end - start).days
    if days <= 0:
        return 0
    weeks, extra = divmod(days, 7)
    count = weeks * 5
    wd = start.weekday()
    for k in range(extra):
        if (wd + k) % 7 < 5:
            count += 1
    observed = set()
    for h in holidays:
        w = h.weekday()
        observed.add(h + timedelta(days=-1 if w == 5 else 1 if w == 6 else 0))
    return count - sum(1 for d in observed if start <= d < end)
""",
    "torus_islands": """
def count_islands(grid):
    R, C = len(grid), len(grid[0])
    parent = list(range(R * C))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for r in range(R):
        row = grid[r]
        for c in range(C):
            if row[c] != '#':
                continue
            a = r * C + c
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                nr, nc = (r + dr) % R, (c + dc) % C
                if grid[nr][nc] == '#':
                    x, y = find(a), find(nr * C + nc)
                    if x != y:
                        parent[x] = y
    return len({find(r * C + c) for r in range(R) for c in range(C) if grid[r][c] == '#'})
""",
    "cleanup_meetings": """
def max_meetings(meetings, gap):
    count = 0
    boundary = None
    for s, e in sorted(meetings, key=lambda m: m[1]):
        if boundary is None or s > boundary:
            count += 1
            boundary = e + gap
    return count
""",
    "hard_wrap": """
def wrap(text, width):
    out, line = [], []
    length = 0
    for word in text.split(' '):
        if not word:
            continue
        if len(word) > width:
            if line:
                out.append(' '.join(line))
            cut = (len(word) - 1) // width * width
            out.extend(word[i:i + width] for i in range(0, cut, width))
            line, length = [word[cut:]], len(word) - cut
            continue
        if line and length + 1 + len(word) <= width:
            line.append(word)
            length += 1 + len(word)
        elif line:
            out.append(' '.join(line))
            line, length = [word], len(word)
        else:
            line, length = [word], len(word)
    if line:
        out.append(' '.join(line))
    return out
""",
    "kth_distinct": """
def kth_distinct(nums, k):
    values = sorted(set(nums), reverse=True)
    return values[k - 1] if 1 <= k <= len(values) else None
""",
    "merge_labeled": """
def merge_labeled(ranges):
    out = []
    for lo, hi, label in sorted(ranges, key=lambda r: (r[2], r[0], r[1])):
        if out and out[-1][2] == label and lo <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], hi), label)
        else:
            out.append((lo, hi, label))
    return sorted(out)
""",
    "strict_roman": """
_TABLE = ((1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I'))
def _encode(n):
    out = []
    for v, s in _TABLE:
        q, n = divmod(n, v)
        out.append(s * q)
    return ''.join(out)
def roman_value(s):
    vals = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
    if not s or any(ch not in vals for ch in s):
        return None
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        total += -v if i + 1 < len(s) and vals[s[i + 1]] > v else v
    return total if 1 <= total <= 3999 and _encode(total) == s else None
""",
    "csv_fields": """
def csv_fields(line):
    fields, i, n = [], 0, len(line)
    while True:
        if i < n and line[i] == '"':
            j = i + 1
            chunk = []
            while True:
                k = line.find('"', j)
                if k == -1:
                    return None
                chunk.append(line[j:k])
                if k + 1 < n and line[k + 1] == '"':
                    chunk.append('"')
                    j = k + 2
                    continue
                i = k + 1
                break
            fields.append(''.join(chunk))
            if i == n:
                return fields
            if line[i] != ',':
                return None
            i += 1
        else:
            k = line.find(',', i)
            if k == -1:
                fields.append(line[i:])
                return fields
            fields.append(line[i:k])
            i = k + 1
""",
    "integer_gaps": """
def gaps(lo, hi, covered):
    result, nxt = [], lo
    for a, b in sorted(covered):
        if a > hi:
            break
        if b < nxt:
            continue
        if a > nxt:
            result.append((nxt, a - 1))
        nxt = b + 1
        if nxt > hi:
            return result
    if nxt <= hi:
        result.append((nxt, hi))
    return result
""",
    "dense_leaderboard": """
def leaderboard(scores):
    best = {}
    for name, points in scores:
        if name not in best or points > best[name]:
            best[name] = points
    ordered = sorted(best, key=lambda name: (-best[name], name))
    result, rank, previous = [], 0, object()
    for name in ordered:
        if best[name] != previous:
            rank += 1
            previous = best[name]
        result.append((rank, name, best[name]))
    return result
""",
}

# Realistic misreadings. Each must fail its case's checks.
MUTANTS: dict[str, list[str]] = {
    "lower_median": [
        # Averages the two middles like LeetCode 4.
        "def lower_median(a, b):\n    m = sorted(a + b)\n    n = len(m)\n    return m[n // 2] if n % 2 else (m[n // 2 - 1] + m[n // 2]) / 2\n",
        # Correct value but O(n) per call.
        "import heapq\ndef lower_median(a, b):\n    t = len(a) + len(b)\n    for i, x in enumerate(heapq.merge(a, b)):\n        if i == (t - 1) // 2:\n            return x\n",
        # Upper median.
        "def lower_median(a, b):\n    m = sorted(a + b)\n    return m[len(m) // 2]\n",
    ],
    "dl_distance": [
        # Restricted optimal string alignment.
        "def dl_distance(a, b):\n    n, m = len(a), len(b)\n    d = [[0] * (m + 1) for _ in range(n + 1)]\n    for i in range(n + 1): d[i][0] = i\n    for j in range(m + 1): d[0][j] = j\n    for i in range(1, n + 1):\n        for j in range(1, m + 1):\n            c = 0 if a[i-1] == b[j-1] else 1\n            d[i][j] = min(d[i-1][j] + 1, d[i][j-1] + 1, d[i-1][j-1] + c)\n            if i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:\n                d[i][j] = min(d[i][j], d[i-2][j-2] + 1)\n    return d[n][m]\n",
        # Plain Levenshtein.
        "def dl_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i, x in enumerate(a, 1):\n        cur = [i]\n        for j, y in enumerate(b, 1):\n            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (x != y)))\n        prev = cur\n    return prev[-1]\n",
    ],
    "semver_compare": [
        # Splits on the first '-' before removing build metadata.
        "def compare_versions(a, b):\n    def key(v):\n        core, _, pre = v.partition('-')\n        core = core.split('+')[0]\n        pre = pre.split('+')[0]\n        ids = [(0, int(x), '') if x.isdigit() else (1, 0, x) for x in pre.split('.')] if pre else None\n        return tuple(map(int, core.split('.'))), ids\n    (ca, pa), (cb, pb) = key(a), key(b)\n    if ca != cb: return -1 if ca < cb else 1\n    if pa is None and pb is None: return 0\n    if pa is None: return 1\n    if pb is None: return -1\n    return (pa > pb) - (pa < pb)\n",
        # Compares prerelease identifiers as plain strings.
        "def compare_versions(a, b):\n    def key(v):\n        v = v.split('+')[0]\n        core, _, pre = v.partition('-')\n        return tuple(map(int, core.split('.'))), pre.split('.') if pre else None\n    (ca, pa), (cb, pb) = key(a), key(b)\n    if ca != cb: return -1 if ca < cb else 1\n    if pa is None and pb is None: return 0\n    if pa is None: return 1\n    if pb is None: return -1\n    return (pa > pb) - (pa < pb)\n",
    ],
    "sticky_cache": [
        # Classic LRU: an update refreshes recency.
        "from collections import OrderedDict\ndef run_cache(capacity, ops):\n    c = OrderedDict(); out = []\n    for op in ops:\n        if op[0] == 'get':\n            if op[1] in c:\n                c.move_to_end(op[1]); out.append(c[op[1]])\n            else: out.append(-1)\n        elif capacity:\n            c[op[1]] = op[2]; c.move_to_end(op[1])\n            if len(c) > capacity: c.popitem(last=False)\n    return out\n",
        # Correct semantics with an O(capacity) list.
        "def run_cache(capacity, ops):\n    order = []; store = {}; out = []\n    for op in ops:\n        if op[0] == 'get':\n            if op[1] in store:\n                order.remove(op[1]); order.append(op[1]); out.append(store[op[1]])\n            else: out.append(-1)\n        elif capacity:\n            if op[1] in store: store[op[1]] = op[2]; continue\n            store[op[1]] = op[2]; order.append(op[1])\n            if len(order) > capacity: del store[order.pop(0)]\n    return out\n",
    ],
    "largest_remainder": [
        # Ties by index only.
        "def allocate(total, w):\n    n = len(w)\n    if not n: return []\n    s = sum(w)\n    if not s: return [total // n + (i < total % n) for i in range(n)]\n    base = [total * x // s for x in w]\n    order = sorted(range(n), key=lambda i: (-(total * w[i] % s), i))\n    for i in order[:total - sum(base)]: base[i] += 1\n    return base\n",
        # Floating point remainders.
        "def allocate(total, w):\n    n = len(w)\n    if not n: return []\n    s = sum(w)\n    if not s: return [total // n + (i < total % n) for i in range(n)]\n    raw = [total * x / s for x in w]\n    base = [int(r) for r in raw]\n    order = sorted(range(n), key=lambda i: (-(raw[i] - base[i]), -w[i], i))\n    for i in order[:total - sum(base)]: base[i] += 1\n    return base\n",
    ],
    "parse_duration": [
        # Unicode digits accepted through \\d.
        "import re\ndef parse_duration(s):\n    if not re.fullmatch(r'(\\d+[wdhms])( ?\\d+[wdhms])*', s): return None\n    units = 'wdhms'; mult = dict(zip(units, (604800, 86400, 3600, 60, 1)))\n    parts = re.findall(r'(\\d+)([wdhms])', s)\n    idx = [units.index(u) for _, u in parts]\n    if any(x >= y for x, y in zip(idx, idx[1:])): return None\n    return sum(int(n) * mult[u] for n, u in parts)\n",
        # Accepts any whitespace run between components.
        "import re\ndef parse_duration(s):\n    if not re.fullmatch(r'([0-9]+[wdhms])(\\s*[0-9]+[wdhms])*', s): return None\n    units = 'wdhms'; mult = dict(zip(units, (604800, 86400, 3600, 60, 1)))\n    parts = re.findall(r'([0-9]+)([wdhms])', s)\n    idx = [units.index(u) for _, u in parts]\n    if any(x >= y for x, y in zip(idx, idx[1:])): return None\n    return sum(int(n) * mult[u] for n, u in parts)\n",
    ],
    "observed_business_days": [
        # Ignores weekend-holiday observation.
        "from datetime import timedelta\ndef business_days(start, end, holidays):\n    hs = set(holidays); c = 0; d = start\n    while d < end:\n        if d.weekday() < 5 and d not in hs: c += 1\n        d += timedelta(1)\n    return c\n",
        # Correct rule, iterates every day.
        "from datetime import timedelta\ndef business_days(start, end, holidays):\n    obs = {h - timedelta(1) if h.weekday() == 5 else h + timedelta(1) if h.weekday() == 6 else h for h in holidays}\n    c = 0; d = start\n    while d < end:\n        if d.weekday() < 5 and d not in obs: c += 1\n        d += timedelta(1)\n    return c\n",
        # Double counts holidays that share an observed date.
        "from datetime import timedelta\ndef business_days(start, end, holidays):\n    n = (end - start).days\n    if n <= 0: return 0\n    full, rem = divmod(n, 7)\n    c = full * 5 + sum((start.weekday() + k) % 7 < 5 for k in range(rem))\n    for h in set(holidays):\n        o = h - timedelta(1) if h.weekday() == 5 else h + timedelta(1) if h.weekday() == 6 else h\n        if start <= o < end: c -= 1\n    return c\n",
    ],
    "torus_islands": [
        # No wraparound.
        "def count_islands(g):\n    R, C = len(g), len(g[0]); seen = set(); n = 0\n    for r in range(R):\n        for c in range(C):\n            if g[r][c] == '#' and (r, c) not in seen:\n                n += 1; seen.add((r, c)); st = [(r, c)]\n                while st:\n                    y, x = st.pop()\n                    for dy in (-1, 0, 1):\n                        for dx in (-1, 0, 1):\n                            ny, nx = y + dy, x + dx\n                            if 0 <= ny < R and 0 <= nx < C and g[ny][nx] == '#' and (ny, nx) not in seen:\n                                seen.add((ny, nx)); st.append((ny, nx))\n    return n\n",
        # Wraparound but 4-neighbourhood.
        "def count_islands(g):\n    R, C = len(g), len(g[0]); seen = set(); n = 0\n    for r in range(R):\n        for c in range(C):\n            if g[r][c] == '#' and (r, c) not in seen:\n                n += 1; seen.add((r, c)); st = [(r, c)]\n                while st:\n                    y, x = st.pop()\n                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n                        ny, nx = (y + dy) % R, (x + dx) % C\n                        if g[ny][nx] == '#' and (ny, nx) not in seen:\n                            seen.add((ny, nx)); st.append((ny, nx))\n    return n\n",
        # Recursive DFS.
        "import sys\nsys.setrecursionlimit(10000)\ndef count_islands(g):\n    R, C = len(g), len(g[0]); seen = set()\n    def go(y, x):\n        seen.add((y, x))\n        for dy in (-1, 0, 1):\n            for dx in (-1, 0, 1):\n                ny, nx = (y + dy) % R, (x + dx) % C\n                if g[ny][nx] == '#' and (ny, nx) not in seen: go(ny, nx)\n    n = 0\n    for r in range(R):\n        for c in range(C):\n            if g[r][c] == '#' and (r, c) not in seen:\n                n += 1; go(r, c)\n    return n\n",
    ],
    "cleanup_meetings": [
        # Half-open intervals: touching meetings allowed.
        "def max_meetings(ms, gap):\n    n = 0; last = None\n    for s, e in sorted(ms, key=lambda m: m[1]):\n        if last is None or s >= last + gap:\n            n += 1; last = e\n    return n\n",
        # Sorted by start time.
        "def max_meetings(ms, gap):\n    n = 0; last = None\n    for s, e in sorted(ms):\n        if last is None or s > last + gap:\n            n += 1; last = e\n    return n\n",
    ],
    "hard_wrap": [
        # str.split() treats tabs and NBSP as separators.
        "def wrap(text, width):\n    lines, cur = [], ''\n    for w in text.split():\n        while len(w) > width:\n            if cur: lines.append(cur); cur = ''\n            lines.append(w[:width]); w = w[width:]\n        if not cur: cur = w\n        elif len(cur) + 1 + len(w) <= width: cur += ' ' + w\n        else: lines.append(cur); cur = w\n    if cur: lines.append(cur)\n    return lines\n",
        # Fills the current line with a partial chunk.
        "def wrap(text, width):\n    lines, cur = [], ''\n    for w in [x for x in text.split(' ') if x]:\n        if cur and len(cur) + 1 + len(w) <= width:\n            cur += ' ' + w; continue\n        if cur and len(w) > width and len(cur) + 2 <= width:\n            room = width - len(cur) - 1\n            lines.append(cur + ' ' + w[:room]); w = w[room:]; cur = ''\n        elif cur:\n            lines.append(cur); cur = ''\n        while len(w) > width:\n            lines.append(w[:width]); w = w[width:]\n        cur = w\n    if cur: lines.append(cur)\n    return lines\n",
    ],
    "kth_distinct": [
        "def kth_distinct(nums, k):\n    s = sorted(nums, reverse=True)\n    return s[k - 1] if 1 <= k <= len(s) else None\n",
    ],
    "merge_labeled": [
        "def merge_labeled(ranges):\n    out = []\n    for lo, hi, l in sorted(ranges, key=lambda r: (r[2], r[0], r[1])):\n        if out and out[-1][2] == l and lo <= out[-1][1]:\n            out[-1] = (out[-1][0], max(out[-1][1], hi), l)\n        else: out.append((lo, hi, l))\n    return sorted(out)\n",
    ],
    "strict_roman": [
        "def roman_value(s):\n    v = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}\n    if not s or any(c not in v for c in s): return None\n    t = 0\n    for i, c in enumerate(s):\n        t += -v[c] if i + 1 < len(s) and v[s[i+1]] > v[c] else v[c]\n    return t if 1 <= t <= 3999 else None\n",
    ],
    "csv_fields": [
        "import csv\ndef csv_fields(line):\n    rows = list(csv.reader([line]))\n    return rows[0] if rows else ['']\n",
        "def csv_fields(line):\n    return line.split(',')\n",
    ],
    "integer_gaps": [
        "def gaps(lo, hi, cov):\n    out, cur = [], lo\n    for a, b in sorted(cov):\n        if a > cur + 1:\n            out.append((cur, a - 1))\n        cur = max(cur, b + 1)\n    if cur <= hi: out.append((cur, hi))\n    return out\n",
        "def gaps(lo, hi, cov):\n    out, cur = [], lo\n    for a, b in sorted(cov):\n        if a > cur: out.append((cur, min(a - 1, hi)))\n        cur = max(cur, b + 1)\n    if cur <= hi: out.append((cur, hi))\n    return out\n",
    ],
    "dense_leaderboard": [
        "def leaderboard(scores):\n    best = {}\n    for n, p in scores: best[n] = max(p, best.get(n, p))\n    rows = sorted(best.items(), key=lambda kv: (-kv[1], kv[0]))\n    out = []\n    for i, (n, p) in enumerate(rows):\n        r = out[-1][0] if out and out[-1][2] == p else i + 1\n        out.append((r, n, p))\n    return out\n",
        "def leaderboard(scores):\n    best = {}\n    for n, p in scores: best[n] = max(p, best.get(n, p))\n    rows = sorted(best.items(), key=lambda kv: (-kv[1], kv[0].lower()))\n    out, r, prev = [], 0, None\n    for n, p in rows:\n        if p != prev: r += 1; prev = p\n        out.append((r, n, p))\n    return out\n",
    ],
}
