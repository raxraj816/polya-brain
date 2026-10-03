from decimal import Decimal

import pytest
from evals.chapter_13p.coding_execution.budgeted import SpendGuard

from app.llm import (
    FakeLLMClient,
    LLMMessage,
    LLMRequest,
    LLMRequestOptions,
    LLMResponse,
    LLMRole,
    LLMTokenUsage,
)


def request(**options):
    return LLMRequest(
        model="test",
        messages=[LLMMessage(role=LLMRole.USER, content="Solve the supplied task.")],
        options=LLMRequestOptions(max_retries=0, max_output_tokens=100, **options),
    )


def guard(tmp_path, *, cost=0.01, model="test", cap="5"):
    client = FakeLLMClient(
        [
            LLMResponse(
                provider="fake",
                model=model,
                text="{}",
                usage=LLMTokenUsage(input_tokens=10, output_tokens=10, estimated_cost_usd=cost),
            )
        ]
    )
    return SpendGuard(
        client,
        model="test",
        dollars=cap,
        input_rate="0.000001",
        output_rate="0.000004",
        directory=tmp_path / "spend",
    ), client


def test_known_charge_replaces_reservation_and_keeps_response(tmp_path):
    meter, client = guard(tmp_path)
    meter.complete(request())
    assert meter.spent == Decimal("0.01")
    assert len(client.requests) == 1 and not meter.blocked
    assert (tmp_path / "spend/1.response.json").exists()


@pytest.mark.parametrize("cost,model", [(None, "test"), (0.01, "wrong-model"), (1.0, "test")])
def test_unknown_route_or_over_reservation_stops_batch_and_preserves_response(
    tmp_path, cost, model
):
    meter, client = guard(tmp_path, cost=cost, model=model)
    with pytest.raises(ValueError):
        meter.complete(request())
    assert meter.blocked and len(client.requests) == 1
    assert (tmp_path / "spend/1.response.json").exists()
    with pytest.raises(ValueError):
        meter.complete(request())
    assert len(client.requests) == 1


def test_unaffordable_reservation_prevents_any_dispatch(tmp_path):
    meter, client = guard(tmp_path, cap="0.001")
    with pytest.raises(ValueError, match="does not fit"):
        meter.complete(request())
    assert not client.requests and meter.spent == 0


def test_crash_or_provider_failure_retains_reservation_and_stops(tmp_path):
    meter, client = guard(tmp_path)

    def fail(_request):
        raise RuntimeError("simulated provider failure")

    client.complete = fail
    with pytest.raises(RuntimeError):
        meter.complete(request())
    assert meter.blocked and meter.spent > 0
    assert (tmp_path / "spend/1.unknown.json").exists()


def test_invalid_batch_budget_is_rejected_before_dispatch(tmp_path):
    with pytest.raises(ValueError):
        guard(tmp_path, cap="NaN")
