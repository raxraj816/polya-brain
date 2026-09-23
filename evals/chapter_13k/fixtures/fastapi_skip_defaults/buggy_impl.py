"""Reduced reproduction of FastAPI bug 10 at b77a43bc."""


class ResponseModel:
    def __init__(self, name: str, note: str | None = None) -> None:
        self.name = name
        self.note = note

    def dict(self, *, skip_defaults: bool = False) -> dict[str, str | None]:
        result: dict[str, str | None] = {"name": self.name, "note": self.note}
        if skip_defaults and self.note is None:
            result.pop("note")
        return result


def serialize_response(response: ResponseModel, *, skip_defaults: bool) -> dict[str, str | None]:
    value = {"name": response.name, "note": response.note}
    return dict(value)
