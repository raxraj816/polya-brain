"""Reduced fixed behavior from HTTPie commit 58988793."""


def update_headers(request_headers: dict[str, bytes | None]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in request_headers.items():
        if value is None:
            continue
        value = value.decode("utf8")
        if name == "User-Agent" and value.startswith("HTTPie/"):
            continue
        headers[name] = value
    return headers
