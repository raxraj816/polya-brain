from types import ModuleType


def verify(implementation: ModuleType) -> None:
    original = implementation.CaseInsensitiveHeaders([("host", "custom.example")])
    result = implementation.rendered_headers(original, "url.example")
    host_values = [value for key, value in result.items() if key.casefold() == "host"]
    assert host_values == ["custom.example"]
