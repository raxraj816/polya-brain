"""Verified claims: every number in a data answer is independently re-derived."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.execution import DockerPythonSandbox, DockerSandboxLimits, image_available
from app.llm import FakeLLMClient, LLMResponse, LLMTokenUsage
from app.verified_claims.pipeline import AnswerStatus, ClaimLimits, ClaimStatus, ClaimVerifier
from app.verified_claims.runner import same, stated_tolerance
from app.verified_claims.tables import TableError, load_tables

ORDERS = """order_id,customer,region,amount,status
1,Acme,North,120.50,paid
2,Bolt,South,80.00,paid
3,Acme,North,200.00,refunded
4,Cora,East,,paid
5,Dyno,South,310.25,paid
6,Bolt,South,45.00,paid
7,Eon,East,99.99,refunded
8,Acme,North,15.00,paid
"""
QUESTION = (
    "What is the total revenue from paid orders (blank amounts count as zero), and which "
    "region has the highest paid revenue?"
)
PAID_TOTAL = 570.75  # 120.50 + 80 + 0 + 310.25 + 45 + 15
ANSWER_CODE = (
    "def compute(tables):\n"
    "    total = 0.0\n"
    "    by_region = {}\n"
    "    for row in tables['orders']:\n"
    "        if row['status'] != 'paid':\n"
    "            continue\n"
    "        amount = float(row['amount'] or 0)\n"
    "        total += amount\n"
    "        by_region[row['region']] = by_region.get(row['region'], 0.0) + amount\n"
    "    top = max(sorted(by_region), key=lambda r: by_region[r]) if by_region else None\n"
    "    return {'c1': round(total, 2), 'c2': top}\n"
)
COUNTS_REFUNDS = ANSWER_CODE.replace(
    "        if row['status'] != 'paid':\n            continue\n", ""
)
HARDCODED = "def compute(tables):\n    return {'c1': 570.75, 'c2': 'South'}\n"
ORACLE_CODE = (
    "import sqlite3\n"
    "def compute(tables):\n"
    "    db = sqlite3.connect(':memory:')\n"
    "    db.execute('create table o (region text, amount real, status text)')\n"
    "    db.executemany('insert into o values (?,?,?)', [(r['region'], float(r['amount'] or 0), r['status']) for r in tables['orders']])\n"
    "    total = db.execute(\"select coalesce(sum(amount),0) from o where status='paid'\").fetchone()[0]\n"
    "    top = db.execute(\"select region from o where status='paid' group by region order by sum(amount) desc, region limit 1\").fetchone()\n"
    "    return {'c1': round(total, 2), 'c2': top[0] if top else None}\n"
)
CLAIMS = [
    {
        "id": "c1",
        "statement": "Total amount of paid orders, blanks as zero, rounded to 2 decimals",
        "value": 570.75,
    },
    {
        "id": "c2",
        "statement": "Region with the highest total amount of paid orders",
        "value": "South",
    },
]


def response(payload: object) -> LLMResponse:
    return LLMResponse(
        provider="fake",
        model="fake-model",
        text=payload if isinstance(payload, str) else json.dumps(payload),
        usage=LLMTokenUsage(input_tokens=10, output_tokens=5, estimated_cost_usd=0.0001),
    )


def answer(code: str = ANSWER_CODE, claims: list[dict] | None = None) -> LLMResponse:
    return response(
        {
            "answer": "Paid revenue is 570.75 and South leads.",
            "claims": claims if claims is not None else CLAIMS,
            "code": code,
        }
    )


def oracle(code: str = ORACLE_CODE, issues: list[dict] | None = None) -> LLMResponse:
    return response({"code": code, "definition_issues": issues or [], "assumptions": []})


def test_tolerance_and_value_comparison() -> None:
    assert stated_tolerance(570.8) == pytest.approx(0.05)
    assert stated_tolerance("1,234") == 0.5
    assert same(570.8, 570.75, absolute=stated_tolerance(570.8))
    assert not same(571, 570.75, absolute=0.0)
    assert same(" south ", "South") and same(["a", 1.0], ["A", 1])
    assert not same(True, 1)


def test_tables_are_bounded_and_named(tmp_path: Path) -> None:
    table = tmp_path / "2024 orders.csv"
    table.write_text(ORDERS)
    (loaded,) = load_tables([table])
    assert loaded.name == "t_2024_orders" and loaded.row_count == 8 and "status" in loaded.columns
    with pytest.raises(TableError):
        load_tables([tmp_path / "missing.csv"])
    (tmp_path / "bad.json").write_text('{"not": "a list"}')
    with pytest.raises(TableError):
        load_tables([tmp_path / "bad.json"])


docker = pytest.mark.skipif(
    shutil.which("docker") is None or not image_available(DockerPythonSandbox().image),
    reason="Docker sandbox image unavailable",
)


def verify(tmp_path: Path, script: list[LLMResponse]):  # noqa: ANN201
    table = tmp_path / "orders.csv"
    table.write_text(ORDERS)
    client = FakeLLMClient(script)
    verifier = ClaimVerifier(
        client,
        "fake-model",
        DockerPythonSandbox(limits=DockerSandboxLimits(timeout_seconds=30, memory_megabytes=128)),
        limits=ClaimLimits(call_seconds=3.0),
    )
    return verifier.verify(QUESTION, load_tables([table])), client


@docker
def test_correct_answer_is_proven_on_data_and_perturbations(tmp_path: Path) -> None:
    outcome, client = verify(tmp_path, [answer(), oracle()])
    certificate = outcome.certificate
    assert certificate.status is AnswerStatus.VERIFIED
    assert [c.status for c in certificate.claims] == [ClaimStatus.PROVEN, ClaimStatus.PROVEN]
    assert certificate.claims[0].final_value == PAID_TOTAL
    assert all(c.variants_agreed == c.variants_total == 5 for c in certificate.claims)
    verifier_prompt = client.requests[1].messages[0].content
    assert "570.75" not in verifier_prompt and "def compute" not in verifier_prompt


@docker
def test_number_contradicting_its_own_computation_is_corrected(tmp_path: Path) -> None:
    claims = [dict(CLAIMS[0], value=600.0), CLAIMS[1]]
    outcome, _ = verify(tmp_path, [answer(claims=claims), oracle()])
    certificate = outcome.certificate
    assert certificate.status is AnswerStatus.CORRECTED
    first = certificate.claims[0]
    assert first.status is ClaimStatus.CORRECTED and first.final_value == PAID_TOTAL
    assert "600.0" in first.reason


@docker
def test_misread_filter_is_caught_and_corrected_after_adjudication(tmp_path: Path) -> None:
    ruling = response(
        {
            "items": [
                {
                    "id": "c1",
                    "verdict": "verifier_correct",
                    "correct_value": PAID_TOTAL,
                    "explanation": "Refunds are not paid.",
                },
                {
                    "id": "c2",
                    "verdict": "verifier_correct",
                    "correct_value": "South",
                    "explanation": "Paid only.",
                },
            ]
        }
    )
    outcome, _ = verify(tmp_path, [answer(COUNTS_REFUNDS), oracle(), ruling])
    certificate = outcome.certificate
    first = certificate.claims[0]
    assert first.computed_value == 870.74 and first.final_value == PAID_TOTAL
    assert first.status is ClaimStatus.CORRECTED
    assert certificate.status in {AnswerStatus.CORRECTED, AnswerStatus.NEEDS_REVIEW}


@docker
def test_hardcoded_numbers_agree_on_real_data_but_fail_on_perturbed_copies(tmp_path: Path) -> None:
    outcome, _ = verify(tmp_path, [answer(HARDCODED), oracle(), response("{}")])
    first = outcome.certificate.claims[0]
    assert first.variants_agreed >= 1 and first.variants_agreed < first.variants_total
    assert first.status is ClaimStatus.DISPUTED
    assert outcome.certificate.status is AnswerStatus.NEEDS_REVIEW


@docker
def test_definition_that_misses_the_question_is_never_proven(tmp_path: Path) -> None:
    issue = [{"id": "c1", "issue": "The question asks for paid orders only."}]
    outcome, _ = verify(tmp_path, [answer(), oracle(issues=issue)])
    assert outcome.certificate.claims[0].status is ClaimStatus.DISPUTED
    assert outcome.certificate.status is AnswerStatus.NEEDS_REVIEW


@docker
def test_failing_answer_code_gets_one_repair_and_unusable_verifier_stays_unverified(
    tmp_path: Path,
) -> None:
    broken = ANSWER_CODE.replace("float(row['amount'] or 0)", "float(row['amount'])")
    outcome, client = verify(
        tmp_path, [answer(broken), answer(), response("nope"), response("nope")]
    )
    assert "FAILED ON THE DATA" in client.requests[1].messages[0].content
    assert outcome.certificate.status is AnswerStatus.UNVERIFIED
    assert all(c.status is ClaimStatus.UNVERIFIED for c in outcome.certificate.claims)


@docker
def test_cli_writes_report_and_certificate(tmp_path: Path, monkeypatch) -> None:
    from app.investigator.cli import main

    table = tmp_path / "orders.csv"
    table.write_text(ORDERS)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "fake-model")
    monkeypatch.setenv("FAILURE_PATTERNS_PATH", str(tmp_path / "patterns.jsonl"))
    monkeypatch.setattr(
        "app.verified_claims.cli.OpenRouterLLMClient.from_settings",
        lambda settings: FakeLLMClient(
            [answer(claims=[dict(CLAIMS[0], value=600.0), CLAIMS[1]]), oracle()]
        ),
    )
    code = main(
        [
            "ask-data",
            QUESTION,
            "--table",
            str(table),
            "--output-root",
            str(tmp_path / "out"),
            "--run-id",
            "r1",
        ]
    )
    assert code == 0
    report = (tmp_path / "out" / "r1" / "report.md").read_text()
    assert report.startswith("# Corrected and verified")
    assert "| Corrected |" in report and "5/5 data versions agree" in report
    certificate = json.loads((tmp_path / "out" / "r1" / "certificate.json").read_text())
    assert certificate["status"] == "corrected_and_verified"


def test_provider_refusal_is_reported_with_an_actionable_reason(tmp_path: Path) -> None:
    from app.llm import LLMClientError, LLMErrorCode

    refusal = LLMClientError(
        LLMErrorCode.PERMISSION,
        "OpenRouter request failed (http_402).",
        provider="openrouter",
        status_code=402,
    )
    table = tmp_path / "orders.csv"
    table.write_text(ORDERS)
    verifier = ClaimVerifier(FakeLLMClient([refusal]), "fake-model", sandbox=None)
    certificate = verifier.verify(QUESTION, load_tables([table])).certificate
    assert certificate.status is AnswerStatus.UNVERIFIED
    assert "payment required" in certificate.reason and "credits" in certificate.reason
