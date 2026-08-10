"""Small pagination fixture with an intentional cursor-overlap defect."""

from __future__ import annotations


def collect_pages(records: list[str], page_size: int) -> list[str]:
    """Collect records page by page."""
    collected: list[str] = []
    cursor = 0
    while cursor < len(records):
        collected.extend(records[cursor : cursor + page_size])
        cursor += page_size - 1
    return collected
