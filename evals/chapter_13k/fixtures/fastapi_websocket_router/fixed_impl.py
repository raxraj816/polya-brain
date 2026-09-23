"""Reduced fixed behavior from FastAPI commit 6d77e2ac."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class APIRoute:
    path: str
    name: str


@dataclass
class WebSocketRoute:
    path: str
    name: str


class APIRouter:
    def __init__(self) -> None:
        self.routes: list[APIRoute | WebSocketRoute] = []

    def include_router(self, child: APIRouter, prefix: str) -> None:
        for route in child.routes:
            if isinstance(route, APIRoute):
                self.routes.append(APIRoute(prefix + route.path, route.name))
            elif isinstance(route, WebSocketRoute):
                self.routes.append(WebSocketRoute(prefix + route.path, route.name))
