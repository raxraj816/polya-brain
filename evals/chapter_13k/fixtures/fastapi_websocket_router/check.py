from types import ModuleType


def verify(implementation: ModuleType) -> None:
    child = implementation.APIRouter()
    child.routes.extend(
        [
            implementation.APIRoute("/items", "items"),
            implementation.WebSocketRoute("/events", "events"),
        ]
    )
    parent = implementation.APIRouter()
    parent.include_router(child, "/v1")
    routes = {(type(route).__name__, route.path, route.name) for route in parent.routes}
    assert routes == {
        ("APIRoute", "/v1/items", "items"),
        ("WebSocketRoute", "/v1/events", "events"),
    }
