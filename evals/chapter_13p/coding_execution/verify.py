"""Independent developer checks, never supplied to the model; not a blind benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from app.cognition.execution_verification import (
    coding_delivery_failures,
    sandbox_verification_failures,
)
from app.execution import DockerPythonSandbox, DockerSandboxLimits
from app.graph.state import ExecutionOutput, create_initial_state
from app.models.contracts import PlanTask, StructuredProblem

try:
    from .evidence import checks_digest, digest, execution_passed, extract_code
except ImportError:  # direct script execution
    from evidence import checks_digest, digest, execution_passed, extract_code

CHECKS = {
    "finite_routes": [
        """import random
rng = random.Random(9252701)
for _ in range(600):
    n = rng.randrange(1,8)
    edges = [(u,v) for u in range(n) for v in range(n) if rng.random()<0.18]
    if edges and rng.random()<0.5: edges += edges[:2]
    original = edges[:]
    reach = [[False]*n for _ in range(n)]
    for u,v in edges: reach[u][v] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] |= reach[i][k] and reach[k][j]
    infinite = any(reach[u][u] and (u==0 or reach[0][u])
                   and (u==n-1 or reach[u][n-1]) for u in range(n))
    if infinite:
        want = None
    else:
        # Every walk that can reach the sink is simple when no relevant cycle exists.
        counts = [1]+[0]*(n-1)
        want = counts[-1]
        for length in range(1,n):
            following = [0]*n
            for u,v in edges: following[v] += counts[u]
            counts = following
            want += counts[-1]
        want %= 1000000007
    assert route_count(n,edges) == want, (n,edges,want)
    assert edges == original, 'input mutated'
print('random_multigraph_cases', 600)""",
        """assert route_count(1,[]) == 1
assert route_count(1,[(0,0)]) is None
assert route_count(3,[(0,1),(1,1)]) == 0
assert route_count(4,[(0,3),(0,1),(1,1)]) == 1
assert route_count(3,[(0,1),(1,1),(1,2)]) is None
assert route_count(2,[(0,1),(0,1)]) == 2
n = 100000
assert route_count(n,[(i,i+1) for i in range(n-1)]) == 1
n = 5000
parallel = [(i,i+1) for i in range(n-1) for _ in range(2)]
assert route_count(n,parallel) == pow(2,n-1,1000000007)
print('boundary_and_scale_checks', 8)""",
    ],
    "shortest_span": [
        """import random
rng = random.Random(92526)
for _ in range(3000):
    values = [rng.randrange(-8,9) for _ in range(rng.randrange(20))]
    threshold = rng.randrange(-12,25)
    original = values[:]
    lengths = [j-i for i in range(len(values)) for j in range(i+1,len(values)+1)
               if sum(values[i:j]) >= threshold]
    want = min(lengths, default=-1)
    assert shortest_span(values,threshold) == want, (values,threshold,want)
    assert values == original, 'input mutated'
print('random_signed_array_cases', 3000)""",
        """assert shortest_span([],0) == -1
assert shortest_span([0],0) == 1
assert shortest_span([-5],-4) == -1
assert shortest_span([-5],-5) == 1
assert shortest_span([2,-1,2],3) == 3
assert shortest_span([84,-37,32,40,95],167) == 3
assert shortest_span([1]*100000,100000) == 100000
assert shortest_span([-1]*100000,1) == -1
assert shortest_span([1000000000,-1000000000,1000000000],1000000001) == -1
print('boundary_and_scale_checks', 9)""",
    ],
    "common_slot": [
        """import random, copy
rng = random.Random(923201)
for _ in range(1200):
    calendars = []
    for person in range(rng.randrange(5)):
        intervals = []
        for item in range(rng.randrange(7)):
            a = rng.randrange(-8, 9)
            intervals.append((a, rng.randrange(a+1, 11)))
        calendars.append(intervals)
    duration = rng.randrange(1, 7)
    original = copy.deepcopy(calendars)
    want = 0 if not calendars else next((t for t in range(-8, 11)
        if all(all(any(a <= x < b for a,b in person)
                   for x in range(t, t+duration)) for person in calendars)), None)
    assert first_slot(calendars, duration) == want, (calendars, duration, want)
    assert calendars == original, 'input mutated'
print('random_calendar_sets', 1200)""",
        """assert first_slot([], 1) == 0
assert first_slot([[], [(1,2)]], 1) is None
assert first_slot([[(1,3),(3,6)],[(2,5)]],3) == 2
assert first_slot([[(1,3)],[(3,6)]],1) is None
assert first_slot([[(-1000000000,1000000000)]],2000000000) == -1000000000
# Overlapping intervals must not count as different people.
assert first_slot([[(0,10),(0,10)],[(11,20)]],1) is None
many = [(i*100000, i*100000+5) for i in range(10000)]
assert first_slot([list(reversed(many)), [(0,1000000000)]],6) is None
print('boundary_and_scale_checks', 7)""",
    ],
    "median": [
        """from itertools import combinations_with_replacement
arrays = [list(a) for n in range(5) for a in combinations_with_replacement(range(-2, 3), n)]
sol = Solution()
count = 0
for a in arrays:
    for b in arrays:
        if not a and not b: continue
        merged = sorted(a + b)
        want = (merged[(len(merged)-1)//2] + merged[len(merged)//2]) / 2
        assert sol.findMedianSortedArrays(a[:], b[:]) == want, (a, b)
        count += 1
print('exhaustive_pairs', count)""",
        """import random
rng = random.Random(92317)
for _ in range(2000):
    a = sorted(rng.randint(-1000000, 1000000) for _ in range(rng.randrange(1001)))
    b = sorted(rng.randint(-1000000, 1000000) for _ in range(rng.randrange(1001)))
    if not a and not b: b = [0]
    merged = sorted(a+b)
    want = (merged[(len(merged)-1)//2] + merged[len(merged)//2])/2
    assert Solution().findMedianSortedArrays(a, b) == want
print('random_pairs', 2000)""",
        """import math
class Indexed:
    def __init__(self, data): self.data, self.reads = data, 0
    def __len__(self): return len(self.data)
    def __getitem__(self, index):
        assert isinstance(index, int), 'slicing is not logarithmic'
        self.reads += 1
        return self.data[index]
for m, n in [(0,1000),(1,1000),(3,997),(1000,1),(1000,1000)]:
    a, b = Indexed(list(range(0,2*m,2))), Indexed(list(range(1,2*n,2)))
    merged = sorted(a.data+b.data)
    assert Solution().findMedianSortedArrays(a,b) == (merged[(m+n-1)//2]+merged[(m+n)//2])/2
    assert a.reads+b.reads <= 8*math.ceil(math.log2(min(m,n)+1))+12
print('bounded_index_access_cases', 5)""",
    ],
    "integer_coverage": [
        """import random
rng=random.Random(92318)
for _ in range(5000):
    spans=[tuple(sorted([rng.randrange(-20,21),rng.randrange(-20,21)])) for _ in range(rng.randrange(20))]
    original=spans[:]
    want=len({x for a,b in spans for x in range(a,b+1)})
    assert covered_count(spans)==want, spans
    assert spans==original, 'input mutated'
assert covered_count([])==0
assert covered_count([(-1000000000,1000000000)])==2000000001
assert covered_count([(1,1),(2,2),(1,1)])==2
print('random_interval_sets', 5000)""",
    ],
    "lexicographic_toposort": [
        """from itertools import permutations
import random
rng=random.Random(92319)
for n in range(7):
    for _ in range(50):
        edges=[(u,v) for u in range(n) for v in range(n) if rng.random()<0.15]
        if edges and rng.random()<0.5: edges+=edges[:2]
        original=edges[:]
        want=[]
        for order in permutations(range(n)):
            pos={v:i for i,v in enumerate(order)}
            if all(pos[u]<pos[v] for u,v in edges):
                want=list(order)
                break
        assert task_order(n,edges)==want, (n,edges,want)
        assert edges==original, 'input mutated'
assert task_order(10000,[(i,i+1) for i in range(9999)])==list(range(10000))
assert task_order(3,[(0,1),(0,1)])==[0,1,2]
assert task_order(3,[(2,2)])==[]
print('bruteforce_graph_cases', 350)""",
    ],
}


def verify(case: str, directory: Path) -> dict[str, object]:
    """Replay delivered code and separately audit the saved runtime's acceptance."""
    summary: dict[str, object] = {"case": case, "passed": False}
    try:
        raw = json.loads((directory / "state.json").read_text())
        state = create_initial_state(raw["raw_input"])
        state["plan"] = [PlanTask.model_validate(task) for task in raw["plan"]]
        state["execution_outputs"] = [
            ExecutionOutput.model_validate(item) for item in raw["execution_outputs"]
        ]
        state["structured_problem"] = StructuredProblem.model_validate(raw["structured_problem"])
        state["final_answer"] = raw.get("final_answer")
        ids = [task.id for task in state["plan"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate task ids")
        checks = CHECKS[case]
        answer = state["final_answer"] or ""
        code = extract_code(answer)
        failures = sandbox_verification_failures(state)
        failures.extend(coding_delivery_failures(state, answer))
        if not any(task.tool_name == "python_sandbox" for task in state["plan"]):
            failures.append("No sandbox implementation produced.")
        if code is None:
            failures.append("Expected exactly one complete delivered Python code block.")
        verdict = raw.get("verification") or {}
        reported_pass = verdict.get("passed") is True and not verdict.get("failed_checks")
        summary.update(
            prompt_sha256=digest(raw["raw_input"]),
            checks_sha256=checks_digest(checks),
            runtime_reported_pass=reported_pass,
            current_execution_contract_passed=not failures,
            acceptance_failures=failures,
            delivered_code_identical_to_executed=(
                code is not None
                and any(
                    task.tool_name == "python_sandbox"
                    and isinstance(task.params.get("code"), str)
                    and task.params["code"].strip() == code
                    for task in state["plan"]
                )
                and not coding_delivery_failures(state, answer)
            ),
        )
        if code is None:
            return summary
        sandbox = DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=20))
        result = sandbox.execute(code, checks)
        independent_pass = execution_passed(result, len(checks))
        summary.update(
            code_sha256=digest(code),
            independent_checks=result.model_dump(mode="json"),
            independent_checks_passed=independent_pass,
            passed=bool(
                independent_pass
                and reported_pass
                and not failures
                and summary["delivered_code_identical_to_executed"]
            ),
            limits="Developer-authored checks, not a formal proof or external judge acceptance.",
        )
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as exc:
        summary["failure"] = type(exc).__name__
        summary["reason"] = "Artifact validation or independent execution failed."
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=CHECKS)
    parser.add_argument("run_directory", type=Path)
    args = parser.parse_args()
    summary = verify(args.case, args.run_directory)
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary["passed"] else 1)
