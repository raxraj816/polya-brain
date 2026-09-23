from types import ModuleType


def verify(implementation: ModuleType) -> None:
    result = implementation.update_headers({"Authorization": None, "X-Request-ID": b"request-7"})
    assert result == {"X-Request-ID": "request-7"}
