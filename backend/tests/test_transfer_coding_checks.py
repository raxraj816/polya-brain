"""The new frozen oracle accepts a reference and rejects targeted faulty algorithms."""

from collections import deque

import pytest
from evals.chapter_13p.coding_execution.verify import CHECKS


def reference(values, threshold):
    candidates = deque([(0, 0)])
    total, best = 0, len(values) + 1
    for end, value in enumerate(values, 1):
        total += value
        while candidates and total - candidates[0][1] >= threshold:
            best = min(best, end - candidates.popleft()[0])
        while candidates and candidates[-1][1] >= total:
            candidates.pop()
        candidates.append((end, total))
    return best if best <= len(values) else -1


def test_transfer_oracle_accepts_independent_reference():
    for check in CHECKS["shortest_span"]:
        exec(check, {"shortest_span": reference})


@pytest.mark.parametrize(
    "defect", ["empty_allowed", "strict_threshold", "mutates", "positive_window"]
)
def test_transfer_oracle_rejects_common_semantic_errors(defect):
    def faulty(values, threshold):
        if defect == "empty_allowed":
            return 0 if threshold <= 0 else reference(values, threshold)
        if defect == "strict_threshold":
            return reference(values, threshold + 1)
        if defect == "mutates":
            values.sort()
            return reference(values, threshold)
        start, total, best = 0, 0, len(values) + 1
        for end, value in enumerate(values):
            total += value
            while start <= end and total >= threshold:
                best = min(best, end - start + 1)
                total -= values[start]
                start += 1
        return best if best <= len(values) else -1

    with pytest.raises(AssertionError):
        for check in CHECKS["shortest_span"]:
            exec(check, {"shortest_span": faulty})


def graph_reference(n, edges):
    forward, backward = [[] for _ in range(n)], [[] for _ in range(n)]
    for u, v in edges:
        forward[u].append(v)
        backward[v].append(u)

    def reachable(start, graph):
        seen, stack = {start}, [start]
        while stack:
            for node in graph[stack.pop()]:
                if node not in seen:
                    seen.add(node)
                    stack.append(node)
        return seen

    active = reachable(0, forward) & reachable(n - 1, backward)
    if 0 not in active:
        return 0
    indegree = [0] * n
    for u, v in edges:
        if u in active and v in active:
            indegree[v] += 1
    ready = deque(u for u in active if indegree[u] == 0)
    ways, visited = [0] * n, 0
    ways[0] = 1
    while ready:
        u = ready.popleft()
        visited += 1
        for v in forward[u]:
            if v in active:
                ways[v] = (ways[v] + ways[u]) % 1000000007
                indegree[v] -= 1
                if indegree[v] == 0:
                    ready.append(v)
    return ways[-1] if visited == len(active) else None


def test_graph_oracle_accepts_separate_linear_reference():
    for check in CHECKS["finite_routes"]:
        exec(check, {"route_count": graph_reference})


@pytest.mark.parametrize(
    "defect", ["any_cycle", "deduplicates", "empty_walk", "ignores_infinity", "mutates"]
)
def test_graph_oracle_rejects_semantic_and_preservation_errors(defect):
    def faulty(n, edges):
        if defect == "any_cycle" and any(u == v for u, v in edges):
            return None
        if defect == "deduplicates":
            return graph_reference(n, list(set(edges)))
        if defect == "empty_walk" and n == 1 and not edges:
            return 0
        if defect == "mutates":
            edges.reverse()
        answer = graph_reference(n, edges)
        return 0 if defect == "ignores_infinity" and answer is None else answer

    with pytest.raises(AssertionError):
        for check in CHECKS["finite_routes"]:
            exec(check, {"route_count": faulty})
