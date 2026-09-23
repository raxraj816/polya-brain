from types import ModuleType


def verify(implementation: ModuleType) -> None:
    response = implementation.ResponseModel(name="Ada")
    assert implementation.serialize_response(response, skip_defaults=True) == {"name": "Ada"}
    assert implementation.serialize_response(response, skip_defaults=False) == {
        "name": "Ada",
        "note": None,
    }
