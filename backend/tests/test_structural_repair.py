"""Bounded syntax transfer and its negative boundary cases."""

import pytest

from app.cognition.structural_repair import structural_candidates


def test_return_edit_transfers_to_renamed_assignment():
    source = "def charge(units, rate):\n    value = units + rate\n    return value\n"
    edits = structural_candidates(source, "return quantity + price", "return quantity * price")
    assert len(edits) == 1
    assert edits[0].names == {"quantity": "units", "price": "rate"}
    assert edits[0].old_text == "units + rate"
    assert edits[0].new_text == "(units * rate)"


def test_parentheses_preserve_precedence_and_unicode_offsets():
    source = "def total(数量, 単価):\n    return 7 * (数量 * 単価)\n"
    edits = structural_candidates(source, "x * y", "x + y")
    assert len(edits) == 1
    assert (
        source.replace(edits[0].old_text, edits[0].new_text)
        == "def total(数量, 単価):\n    return 7 * ((数量 + 単価))\n"
    )


@pytest.mark.parametrize(
    "old,new,source",
    [
        ("x + x", "x * x", "result = a + b"),
        ("x + y", "x * y", "result = a + a"),
        ("x + y", "x * unknown", "result = a + b"),
        ("x + 1", "x + 2", "result = a + True"),
        ("x + 1", "x + 2", "result = a + 3"),
        ("x + y", "x + y", "result = a + b"),
        ("sum(x) + y", "sum(x) * y", "result = sum(a) + b"),
        ("x + y", "func(x, y)", "result = a + b"),
        ("x + y", "x.attr * y", "result = a + b"),
        ("x + y", "x[0] * y", "result = a + b"),
        ("x + y", "(lambda z: z)(x)", "result = a + b"),
        ("x + y", "[z for z in x]", "result = a + b"),
        ("x + y", "(z := x * y)", "result = a + b"),
        ("x + y", "x * y", "text = 'a + b'\n# c + d"),
        ("x + y", "x * y", "result = obj.value + b"),
        ("+", "*", "result = a + b"),
        ("x + y", "x * y", "invalid python!"),
    ],
)
def test_unsupported_or_inconsistent_transfer_produces_no_edit(old, new, source):
    assert structural_candidates(source, old, new) == []


def test_multiple_distinct_sites_are_ambiguous():
    edits = structural_candidates("first = a + b\nsecond = c + d\n", "x + y", "x * y")
    assert edits is None


def test_size_and_node_limits_do_not_produce_candidates():
    assert structural_candidates("#" * 100001, "x + y", "x * y") == []
    assert structural_candidates("a = b + c\n" * 2000, "x + y", "x * y") == []


def test_ambiguous_text_or_sites_cannot_be_hidden_by_another_unique_site():
    source = "one = a + b\n# a + b is mentioned again\ntwo = c + d\n"
    assert structural_candidates(source, "x + y", "x * y") is None
