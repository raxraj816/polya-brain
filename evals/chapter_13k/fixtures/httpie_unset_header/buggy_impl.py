"""Reduced reproduction of HTTPie bug 3 at 8c33e5e3."""


def update_headers(request_headers: dict[str, bytes | None]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in request_headers.items():
        value = value.decode("utf8")
        if name == "User-Agent" and value.startswith("HTTPie/"):
            continue
        headers[name] = value
    return headers
