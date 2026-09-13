"""Reduced fixed behavior from HTTPie commit 040d981f."""


class CaseInsensitiveHeaders:
    def __init__(self, values: list[tuple[str, str]]) -> None:
        self._values = values

    def items(self) -> list[tuple[str, str]]:
        return list(self._values)

    def __contains__(self, name: str) -> bool:
        return any(key.casefold() == name.casefold() for key, _value in self._values)


def rendered_headers(original: CaseInsensitiveHeaders, url_host: str) -> dict[str, str]:
    headers = dict(original.items())
    if "Host" not in original:
        headers["Host"] = url_host
    return headers
