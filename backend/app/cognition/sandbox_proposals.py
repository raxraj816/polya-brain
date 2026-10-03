"""Existing sandbox admission bounds, also checked before bounded model repair."""

from collections.abc import Sequence

from app.models.contracts import PlanTask


def validate_sandbox_proposals(tasks: Sequence[PlanTask]) -> None:
    issues = []
    for index, task in enumerate(tasks):
        if task.tool_name != "python_sandbox":
            continue
        code, tests = task.params.get("code"), task.params.get("tests")
        if not isinstance(code, str) or not code.strip() or len(code) > 20000:
            issues.append(
                f"tasks[{index}].params.code requires 1..20000 characters of nonblank code"
            )
        if not isinstance(tests, list) or not 1 <= len(tests) <= 20:
            issues.append(f"tasks[{index}].params.tests requires 1..20 assertion strings")
        elif any(
            not isinstance(test, str) or not test.strip() or len(test) > 2000 for test in tests
        ):
            for test_index, test in enumerate(tests):
                if not isinstance(test, str) or not test.strip() or len(test) > 2000:
                    issues.append(
                        f"tasks[{index}].params.tests[{test_index}] requires 1..2000 nonblank characters"
                    )
    if issues:
        raise ValueError(
            "Sandbox proposal bounds: "
            + "; ".join(issues[:10])
            + ". Return compact complete code and checks without dropping assertions or weakening expected results."
        )
