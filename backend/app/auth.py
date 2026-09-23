"""OIDC sign-in and server-side browser sessions for the private beta."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings
from app.db.models import AuthSession, utc_now

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
COOKIE = "__Host-polya_session"
STATE_COOKIE = "polya_oidc"
PUBLIC_PATHS = {"/health", "/api/v1/auth/session", "/api/v1/auth/login", "/api/v1/auth/callback"}


def cookie_name(settings: Settings) -> str:
    return COOKIE if settings.public_origin.startswith("https://") else "polya_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def user_id_for(issuer: str, subject: str) -> str:
    # JSON prevents ambiguous issuer/subject separators. No email or display name stored.
    return hashlib.sha256(json.dumps([issuer, subject], separators=(",", ":")).encode()).hexdigest()


def admitted_users(settings: Settings) -> set[str]:
    return {
        user_id_for(settings.oidc_issuer, sub.strip())
        for sub in settings.oidc_allowed_subjects.split(",")
        if sub.strip()
    }


def configure_auth(app: Any, settings: Settings) -> None:
    if not settings.auth_required:
        return
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=(
            "__Host-" + STATE_COOKIE
            if settings.public_origin.startswith("https://")
            else STATE_COOKIE
        ),
        max_age=600,
        same_site="lax",
        https_only=settings.public_origin.startswith("https://"),
        path="/",
    )
    oauth = OAuth()
    app.state.oidc = oauth.register(
        "identity",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret.get_secret_value(),
        server_metadata_url=settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration",
        client_kwargs={"scope": "openid", "code_challenge_method": "S256", "timeout": 10},
    )


async def validated_provider(request: Request) -> Any:
    settings: Settings = request.app.state.settings
    provider = request.app.state.oidc
    metadata = await provider.load_server_metadata()
    if metadata.get("issuer") != settings.oidc_issuer:
        raise ValueError("Issuer mismatch")
    for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        endpoint = urlsplit(metadata.get(field, ""))
        if (
            not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.fragment
            or (
                endpoint.scheme != "https"
                and not (
                    settings.environment in {"local", "test"}
                    and endpoint.scheme == "http"
                    and endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
                )
            )
        ):
            raise ValueError("Unsafe identity endpoint")
    # Independently pin algorithms on every process handling a login or callback.
    provider.server_metadata["id_token_signing_alg_values_supported"] = ["RS256", "ES256"]
    return provider


def authenticated_user(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    if not settings.auth_required:
        return None
    token = request.cookies.get(cookie_name(settings), "")
    if not token or len(token) > 128:
        return None
    with request.app.state.session_factory() as db:
        record = db.get(AuthSession, token_hash(token))
        if record and record.expires_at > utc_now() and record.user_id in admitted_users(settings):
            return str(record.user_id)
    return None


def require_principal(request: Request) -> str | None:
    """Run for every route, independently of UI state and repository dependencies."""
    settings: Settings = request.app.state.settings
    if not settings.auth_required or request.url.path in PUBLIC_PATHS:
        return None
    user_id = authenticated_user(request)
    if user_id is None:
        raise HTTPException(401, "Sign in to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("origin") != settings.public_origin:
            raise HTTPException(403, "A same-origin action is required.")
        if not request.headers.get("content-type", "").lower().startswith("application/json"):
            raise HTTPException(415, "Actions require JSON.")
    return user_id


@router.get("/session")
def auth_status(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    user = authenticated_user(request)
    return JSONResponse(
        {
            "required": settings.auth_required,
            "authenticated": user is not None,
            "workspace_id": user,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.auth_required:
        raise HTTPException(404, "Sign-in is disabled in local bypass mode.")
    try:
        provider = await validated_provider(request)
        request.session.clear()
        nonce = secrets.token_urlsafe(32)
        request.session["nonce"] = nonce
        response: RedirectResponse = await provider.authorize_redirect(
            request,
            settings.public_origin + "/api/backend/api/v1/auth/callback",
            nonce=nonce,
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    except Exception as exc:
        request.session.clear()
        # Provider error text can contain credentials; do not reflect or log it.
        raise HTTPException(503, "Sign-in provider is unavailable or misconfigured.") from exc


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    settings: Settings = request.app.state.settings
    if not settings.auth_required:
        raise HTTPException(404, "Sign-in is disabled in local bypass mode.")
    try:
        nonce = request.session.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise ValueError("Missing nonce")
        provider = await validated_provider(request)
        token = await provider.authorize_access_token(
            request,
            claims_options={"iss": {"essential": True, "value": settings.oidc_issuer}},
            leeway=30,
        )
        claims = token.get("userinfo", {})
        subject = claims.get("sub")
        if (
            not token.get("id_token")
            or claims.get("iss") != settings.oidc_issuer
            or claims.get("nonce") != nonce
            or not isinstance(subject, str)
            or not subject
        ):
            raise ValueError("Invalid identity")
        user = user_id_for(settings.oidc_issuer, subject)
        if user not in admitted_users(settings):
            raise ValueError("Subject is not admitted")
    except Exception as exc:
        request.session.clear()
        raise HTTPException(401, "Sign-in could not be verified. Start sign-in again.") from exc
    request.session.clear()
    handle = secrets.token_urlsafe(32)
    now = utc_now()
    with request.app.state.session_factory() as db:
        # Rotate any previous browser session, remove expired handles opportunistically.
        db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
        old = request.cookies.get(cookie_name(settings))
        if old:
            db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(old)))
        db.add(
            AuthSession(
                token_hash=token_hash(handle),
                user_id=user,
                created_at=now,
                expires_at=now + timedelta(seconds=settings.auth_session_seconds),
            )
        )
        db.commit()
    response = RedirectResponse(
        settings.public_origin + "/",
        status_code=303,
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
    )
    response.set_cookie(
        cookie_name(settings),
        handle,
        max_age=settings.auth_session_seconds,
        httponly=True,
        secure=settings.public_origin.startswith("https://"),
        samesite="lax",
        path="/",
    )
    return response


@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    settings: Settings = request.app.state.settings
    handle = request.cookies.get(cookie_name(settings))
    if handle:
        with request.app.state.session_factory() as db:
            db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(handle)))
            db.commit()
    response = JSONResponse({"signed_out": True}, headers={"Cache-Control": "no-store"})
    response.delete_cookie(
        cookie_name(settings),
        path="/",
        secure=settings.public_origin.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return response
