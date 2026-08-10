"""Regression expectation for the pagination fixture."""

from pagination_service import collect_pages


def test_each_record_is_returned_once() -> None:
    assert collect_pages(["alpha", "beta", "gamma"], page_size=2) == [
        "alpha",
        "beta",
        "gamma",
    ]
