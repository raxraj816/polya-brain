"""Loopback-only identity fixture for browser CI; NEVER an application auth provider.

Run alongside the real API with: python backend/tests/fixtures/oidc_server.py
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from urllib.parse import parse_qs, urlencode

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from joserfc import jwt
from joserfc.jwk import RSAKey

ISSUER = "http://127.0.0.1:18005"
CALLBACK = "http://127.0.0.1:3014/api/backend/api/v1/auth/callback"
app = FastAPI()
key = RSAKey.generate_key(2048, parameters={"kid": "browser-fixture"})
codes: dict[str, dict[str, str]] = {}


@app.get("/.well-known/openid-configuration")
def discovery():
    return {
        "issuer": ISSUER,
        "authorization_endpoint": ISSUER + "/authorize",
        "token_endpoint": ISSUER + "/token",
        "jwks_uri": ISSUER + "/jwks",
        "id_token_signing_alg_values_supported": ["RS256"],
        "code_challenge_methods_supported": ["S256"],
    }


@app.get("/jwks")
def jwks():
    return {"keys": [key.as_dict(private=False)]}


@app.get("/authorize")
def authorize(request: Request):
    params = dict(request.query_params)
    if (
        params.get("redirect_uri") != CALLBACK
        or params.get("client_id") != "browser-client"
        or params.get("code_challenge_method") != "S256"
    ):
        raise HTTPException(400, "Invalid fixture authorization")
    # The test fixture simulates the identity provider's authenticated account chooser.
    import html

    fields = "".join(
        f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(v)}">'
        for k, v in params.items()
    )
    return HTMLResponse(
        f'<h1>Test identity provider</h1><form action="/choose">{fields}<button name="subject" value="alice">Alice</button><button name="subject" value="bob">Bob</button></form>'
    )


@app.get("/choose")
def choose(request: Request):
    params = dict(request.query_params)
    if params.get("redirect_uri") != CALLBACK or params.get("subject") not in {"alice", "bob"}:
        raise HTTPException(400)
    code = secrets.token_urlsafe(32)
    codes[code] = params | {"issued_at": str(time.time())}
    return RedirectResponse(
        CALLBACK + "?" + urlencode({"code": code, "state": params["state"]}), status_code=302
    )


@app.post("/token")
async def token(request: Request):
    body = parse_qs((await request.body()).decode())
    code = codes.pop(body.get("code", [""])[0], None)
    if code is None or time.time() - float(code["issued_at"]) > 60:
        raise HTTPException(400, "Invalid or reused code")
    expected_auth = "Basic " + base64.b64encode(b"browser-client:browser-secret").decode()
    verifier = body.get("code_verifier", [""])[0]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    if (
        request.headers.get("authorization") != expected_auth
        or challenge != code["code_challenge"]
        or body.get("redirect_uri") != [CALLBACK]
    ):
        raise HTTPException(400, "Invalid client or PKCE verifier")
    now = int(time.time())
    signed = jwt.encode(
        {"alg": "RS256", "kid": "browser-fixture"},
        {
            "iss": ISSUER,
            "sub": code["subject"],
            "aud": "browser-client",
            "iat": now,
            "exp": now + 300,
            "nonce": code["nonce"],
        },
        key,
    )
    return {"access_token": "browser-fixture-access", "token_type": "Bearer", "id_token": signed}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=18005, access_log=False)
