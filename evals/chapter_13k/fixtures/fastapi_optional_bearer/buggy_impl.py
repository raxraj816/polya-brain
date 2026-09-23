"""Reduced reproduction of FastAPI bug 12 at d61f5e4b."""


class AuthenticationError(RuntimeError):
    pass


class HTTPBearer:
    def __init__(self, auto_error: bool = True) -> None:
        self.auto_error = auto_error

    def authenticate(self, authorization: str | None) -> tuple[str, str] | None:
        if not authorization:
            if self.auto_error:
                raise AuthenticationError("Not authenticated")
            return None
        scheme, credentials = authorization.split(" ", 1)
        if scheme.casefold() != "bearer":
            raise AuthenticationError("Invalid authentication credentials")
        return scheme, credentials
