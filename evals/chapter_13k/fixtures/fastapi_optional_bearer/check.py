from types import ModuleType


def verify(implementation: ModuleType) -> None:
    optional = implementation.HTTPBearer(auto_error=False)
    assert optional.authenticate(None) is None
    assert optional.authenticate("Basic abc123") is None
    assert optional.authenticate("Bearer token-7") == ("Bearer", "token-7")
