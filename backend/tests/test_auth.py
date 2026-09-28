"""Exercise real OIDC validation and ownership against isolated Postgres records."""

from __future__ import annotations

import base64
import hashlib
import os
import time
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey
from sqlalchemy import select

from app.auth import COOKIE, token_hash, user_id_for
from app.config import Settings, get_settings
from app.db.models import AuthSession, ProblemSession, utc_now
from app.main import create_app
from app.memory import SQLAlchemyMemoryRepository

DB = pytest.mark.skipif(
    os.environ.get("POLYABRAIN_RUN_DB_TESTS") != "1", reason="requires migrated Postgres"
)
ORIGIN = "https://workbench.example"
ISSUER = "https://identity.example"


def configuration(**changes):
    values = dict(
        _env_file=None,
        DATABASE_URL=get_settings().database_url,
        POLYABRAIN_ENV="test",
        POLYABRAIN_AUTH_REQUIRED=True,
        POLYABRAIN_PUBLIC_ORIGIN=ORIGIN,
        POLYABRAIN_SECRET_KEY="test-signing-secret-" * 3,
        OIDC_ISSUER=ISSUER,
        OIDC_CLIENT_ID="test-client",
        OIDC_CLIENT_SECRET="test-secret",
        OIDC_ALLOWED_SUBJECTS="alice,bob",
        OPENROUTER_API_KEY="",
        OPENROUTER_MODEL="",
        SEARCH_API_KEY="",
        SEARCH_PROVIDER="",
    )
    return Settings(**(values | changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"POLYABRAIN_ENV": "production", "POLYABRAIN_AUTH_REQUIRED": False},
        {"POLYABRAIN_PUBLIC_ORIGIN": "http://workbench.example"},
        {"POLYABRAIN_PUBLIC_ORIGIN": "https://workbench.example/path"},
        {"OIDC_ISSUER": "http://identity.example"},
        {"POLYABRAIN_SECRET_KEY": "short"},
        {"OIDC_CLIENT_SECRET": ""},
        {"OIDC_ALLOWED_SUBJECTS": ""},
    ],
)
def test_auth_configuration_fails_closed(changes):
    with pytest.raises(ValueError):
        configuration(**changes)


def test_self_service_requires_explicit_mode_and_authentication():
    settings = configuration(OIDC_REGISTRATION_MODE="self_service", OIDC_ALLOWED_SUBJECTS="")
    assert settings.oidc_registration_mode == "self_service"
    with pytest.raises(ValueError):
        configuration(OIDC_REGISTRATION_MODE="public")
    with pytest.raises(ValueError):
        configuration(OIDC_REGISTRATION_MODE="self_service", POLYABRAIN_AUTH_REQUIRED=False)


@pytest.fixture
def identity_app():
    marker = str(uuid4())
    alice, bob = "alice-" + marker, "bob-" + marker
    app = create_app(configuration(OIDC_ALLOWED_SUBJECTS=f"{alice},{bob}"))
    key = RSAKey.generate_key(2048, parameters={"kid": "fixture-signing-key"})
    provider = {"subject": alice, "claims": {}, "nonce": "", "challenge": "", "tokens": 0}

    def transport(request):
        if request.url.path == "/.well-known/openid-configuration":
            return httpx2.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": ISSUER + "/authorize",
                    "token_endpoint": ISSUER + "/token",
                    "jwks_uri": ISSUER + "/jwks",
                    "response_types_supported": ["code"],
                    "id_token_signing_alg_values_supported": ["RS256"],
                    "code_challenge_methods_supported": ["S256"],
                },
            )
        if request.url.path == "/jwks":
            return httpx2.Response(200, json={"keys": [key.as_dict(private=False)]})
        if request.url.path == "/token":
            body = parse_qs(request.content.decode())
            verifier = body["code_verifier"][0]
            actual = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )
            assert actual == provider["challenge"]
            assert body["redirect_uri"] == [ORIGIN + "/api/backend/api/v1/auth/callback"]
            provider["tokens"] += 1
            claims = {
                "iss": ISSUER,
                "sub": provider["subject"],
                "aud": "test-client",
                "exp": int(time.time()) + 300,
                "iat": int(time.time()),
                "nonce": provider["nonce"],
            }
            claims.update(provider["claims"])
            signed = jwt.encode({"alg": "RS256", "kid": "fixture-signing-key"}, claims, key)
            if provider.get("bad_signature"):
                signed = jwt.encode(
                    {"alg": "RS256", "kid": "fixture-signing-key"},
                    claims,
                    RSAKey.generate_key(2048),
                )
            return httpx2.Response(
                200,
                json={
                    "access_token": "fixture-access-token",
                    "token_type": "Bearer",
                    "id_token": signed,
                },
            )
        raise AssertionError(f"Unexpected identity request: {request.url.path}")

    app.state.oidc.client_kwargs["transport"] = httpx2.MockTransport(transport)
    return app, provider, alice, bob


def start_login(client, provider):
    response = client.get("/api/v1/auth/login", follow_redirects=False)
    assert response.status_code == 302, response.text
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["openid"]
    provider["nonce"] = query["nonce"][0]
    provider["challenge"] = query["code_challenge"][0]
    return query["state"][0]


def sign_in(app, provider, subject):
    client = TestClient(
        app, base_url=ORIGIN, headers={"Origin": ORIGIN, "Content-Type": "application/json"}
    )
    provider["subject"] = subject
    state = start_login(client, provider)
    response = client.get(
        "/api/v1/auth/callback",
        params={"code": "fixture-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    assert response.headers["location"] == ORIGIN + "/"
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    return client


@DB
def test_oidc_round_trip_rotation_expiry_and_logout(identity_app):
    app, provider, alice, _ = identity_app
    client = sign_in(app, provider, alice)
    handle = client.cookies.get(COOKIE)
    assert client.get("/api/v1/auth/session").json()["authenticated"] is True
    assert client.get("/api/v1/sessions").status_code == 200
    state = start_login(client, provider)
    assert (
        client.get(
            "/api/v1/auth/callback",
            params={"code": "new-code", "state": state},
            follow_redirects=False,
        ).status_code
        == 303
    )
    assert client.cookies.get(COOKIE) != handle
    with app.state.session_factory() as db:
        assert db.get(AuthSession, token_hash(handle)) is None
        record = db.get(AuthSession, token_hash(client.cookies.get(COOKIE)))
        assert record.user_id == user_id_for(ISSUER, alice)
        record.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/v1/sessions").status_code == 401
    client = sign_in(app, provider, alice)
    handle = client.cookies.get(COOKIE)
    assert client.post("/api/v1/auth/logout", json={}).status_code == 200
    client.cookies.set(COOKIE, handle, domain="workbench.example", path="/")
    assert client.get("/api/v1/sessions").status_code == 401


@DB
@pytest.mark.parametrize(
    "invalid", ["state", "nonce", "issuer", "audience", "expiry", "signature", "uninvited"]
)
def test_invalid_oidc_response_never_creates_session(identity_app, invalid):
    app, provider, _, _ = identity_app
    client = TestClient(app, base_url=ORIGIN)
    state = start_login(client, provider)
    match invalid:
        case "state":
            state = "forged-state"
        case "nonce":
            provider["claims"] = {"nonce": "forged-nonce"}
        case "issuer":
            provider["claims"] = {"iss": "https://other.example"}
        case "audience":
            provider["claims"] = {"aud": "other-client"}
        case "expiry":
            provider["claims"] = {"exp": int(time.time()) - 120}
        case "signature":
            provider["bad_signature"] = True
        case "uninvited":
            provider["subject"] = "uninvited"
    response = client.get("/api/v1/auth/callback", params={"code": "fixture-code", "state": state})
    assert response.status_code == 401, response.text
    assert COOKIE not in client.cookies
    assert "fixture" not in response.text
    assert client.get("/api/v1/sessions").status_code == 401
    if invalid == "state":
        assert provider["tokens"] == 0


@DB
def test_self_service_admits_new_subjects_with_private_workspaces_and_revocation(identity_app):
    app, provider, _, _ = identity_app
    settings = app.state.settings
    settings.oidc_registration_mode = "self_service"
    settings.oidc_allowed_subjects = ""
    first, second = "new-" + str(uuid4()), "new-" + str(uuid4())
    owner = sign_in(app, provider, first)
    other = sign_in(app, provider, second)
    status = owner.get("/api/v1/auth/session").json()
    assert status["registration_mode"] == "self_service"
    assert status["workspace_id"] == user_id_for(ISSUER, first)
    created = owner.post("/api/v1/sessions", json={"raw_input": "Private self-service work"})
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert other.get(f"/api/v1/sessions/{session_id}/report").status_code == 404
    settings.oidc_blocked_subjects = first
    assert owner.get("/api/v1/sessions").status_code == 401
    assert not owner.get("/api/v1/auth/session").json()["authenticated"]
    provider["subject"] = first
    state = start_login(owner, provider)
    assert (
        owner.get("/api/v1/auth/callback", params={"code": "fixture", "state": state}).status_code
        == 401
    )
    assert other.get("/api/v1/sessions").status_code == 200
    settings.oidc_issuer = "https://replacement-identity.example"
    assert other.get("/api/v1/sessions").status_code == 401


@DB
def test_self_service_still_rejects_unverified_identity(identity_app):
    app, provider, _, _ = identity_app
    app.state.settings.oidc_registration_mode = "self_service"
    app.state.settings.oidc_allowed_subjects = ""
    provider["bad_signature"] = True
    provider["subject"] = "new-" + str(uuid4())
    client = TestClient(app, base_url=ORIGIN)
    state = start_login(client, provider)
    result = client.get("/api/v1/auth/callback", params={"code": "fixture", "state": state})
    assert result.status_code == 401
    assert COOKIE not in client.cookies


@DB
def test_every_private_route_requires_auth_and_owner(identity_app):
    app, provider, alice, bob = identity_app
    owner = sign_in(app, provider, alice)
    other = sign_in(app, provider, bob)
    anonymous = TestClient(app, base_url=ORIGIN)
    marker = "private-" + str(uuid4())
    created = owner.post("/api/v1/sessions", json={"raw_input": marker})
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    with app.state.session_factory() as db:
        assert db.get(ProblemSession, UUID(session_id)).user_id == user_id_for(ISSUER, alice)
    paths = [
        f"/api/v1/sessions/{session_id}" + suffix
        for suffix in [
            "",
            "/report",
            "/artifacts",
            "/events",
            "/events/stream",
            "/feedback",
            "/candidate",
        ]
    ]
    for path in paths:
        assert anonymous.get(path).status_code == 401, path
        assert other.get(path).status_code == 404, path
    for suffix, body in [
        ("/run", {}),
        ("/respond", {"answer": "test"}),
        ("/feedback", {"feedback_type": "useful"}),
    ]:
        path = f"/api/v1/sessions/{session_id}{suffix}"
        assert anonymous.post(path, json=body).status_code == 401
        assert other.post(path, json=body).status_code == 404
    for path in [
        "/api/v1/sessions",
        "/api/v1/source-check",
        "/api/v1/memory/semantic?query=x",
        "/api/v1/memory/episodes?query=x",
        "/api/v1/memory/context?query=x",
        "/api/v1/memory/procedures",
    ]:
        assert anonymous.get(path).status_code == 401, path
    assert anonymous.post("/api/v1/source-check", json={}).status_code == 401
    assert len(owner.get("/api/v1/sessions", params={"q": marker}).json()["sessions"]) == 1
    assert other.get("/api/v1/sessions", params={"q": marker}).json()["sessions"] == []
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get("/docs").status_code == 404
    assert (
        owner.post(
            "/api/v1/sessions", json={"raw_input": "x"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    owner.headers.pop("Origin")
    assert owner.post("/api/v1/sessions", json={"raw_input": "x"}).status_code == 403
    owner.headers["Origin"] = ORIGIN
    assert (
        owner.post(
            "/api/v1/sessions", json={"raw_input": "x", "user_id": user_id_for(ISSUER, bob)}
        ).status_code
        == 422
    )
    app.state.settings.oidc_allowed_subjects = bob
    assert owner.get("/api/v1/sessions").status_code == 401


@DB
def test_memory_namespace_includes_dedup_learning_retrieval_and_updates(identity_app):
    app, provider, alice, bob = identity_app
    clients = [sign_in(app, provider, name) for name in (alice, bob)]
    domain = str(uuid4())
    chunks = []
    for subject, client in zip((alice, bob), clients, strict=True):
        response = client.post(
            "/api/v1/sessions", json={"raw_input": "What is 17 * 6?", "domain": domain}
        )
        session_id = response.json()["id"]
        run = client.post(f"/api/v1/sessions/{session_id}/run", json={})
        assert run.status_code == 200, run.text
        assert run.json()["verification_status"] == "passed"
        with app.state.session_factory() as db:
            db.info["owner_id"] = user_id_for(ISSUER, subject)
            repo = SQLAlchemyMemoryRepository(db)
            chunk = repo.ingest_semantic(
                "Private database latency evidence.",
                source_type="test",
                source_uri="test://same-source",
                reliability_score=1,
                domain=domain,
                session_id=UUID(session_id),
            )
            assert (
                repo.ingest_semantic(
                    "Private database latency evidence.",
                    source_type="test",
                    source_uri="test://same-source",
                    reliability_score=1,
                ).id
                == chunk.id
            )
            # Same learned signature must have separate counters/source IDs per user.
            repo._record_procedure_outcome(
                UUID(session_id),
                domain,
                "gap",
                [],
                {"action_type": "calculate", "capability": "calculator"},
                succeeded=True,
            )
            db.commit()
            chunks.append(str(chunk.id))
            preference = repo.preference(domain, "gap")
            assert preference.source_session_ids == [session_id]
            assert preference.verified_successes == 1
        episodes = client.get(
            "/api/v1/memory/episodes", params={"query": "17 * 6", "domain": domain}
        ).json()
        assert [item["source_session_id"] for item in episodes] == [session_id]
        strategies = client.get("/api/v1/memory/procedures", params={"problem_type": domain}).json()
        assert [item["source_session_ids"] for item in strategies] == [[session_id]]
    assert chunks[0] != chunks[1]
    for index, client in enumerate(clients):
        facts = client.get(
            "/api/v1/memory/semantic",
            params={"query": "Private database latency evidence.", "domain": domain},
        ).json()
        assert [item["id"] for item in facts] == [chunks[index]]
    with app.state.session_factory() as db:
        local = SQLAlchemyMemoryRepository(db)
        assert local.search_semantic("Private database latency evidence.", domain=domain) == []
        assert local.search_episodes("17 * 6", domain=domain) == []
        assert local.list_strategies(problem_type=domain) == []
        victim = db.scalar(
            select(ProblemSession).where(ProblemSession.user_id == user_id_for(ISSUER, alice))
        )
        db.info["owner_id"] = user_id_for(ISSUER, bob)
        with pytest.raises(ValueError, match="owner namespace"):
            SQLAlchemyMemoryRepository(db).ingest_semantic(
                "x",
                source_type="test",
                source_uri="test://x",
                reliability_score=1,
                session_id=victim.id,
            )


@DB
def test_uploaded_source_belongs_to_authenticated_uploader(identity_app, monkeypatch):
    from app.api.routes import source_check

    app, provider, alice, bob = identity_app
    owner = sign_in(app, provider, alice)
    other = sign_in(app, provider, bob)
    monkeypatch.setattr(
        source_check,
        "availability",
        lambda settings: source_check.SourceCheckAvailability(available=True, reason="fixture"),
    )
    response = owner.post(
        "/api/v1/source-check",
        json={
            "raw_input": "Check this function",
            "source_code": "def total(): return 1",
            "check_code": "def verify(source): return True",
            "execution_approved": True,
            "provider_approved": True,
        },
    )
    assert response.status_code == 201, response.text
    session_id = response.json()["id"]
    assert other.get(f"/api/v1/sessions/{session_id}/candidate").status_code == 404
    assert other.post(f"/api/v1/sessions/{session_id}/run", json={}).status_code == 404
    with app.state.session_factory() as db:
        assert db.get(ProblemSession, UUID(session_id)).user_id == user_id_for(ISSUER, alice)


@DB
def test_discovery_cannot_downgrade_identity_transport(identity_app):
    app, provider, _, _ = identity_app
    client = TestClient(app, base_url=ORIGIN)
    start_login(client, provider)
    app.state.oidc.server_metadata["token_endpoint"] = "http://identity.example/token"
    assert client.get("/api/v1/auth/login", follow_redirects=False).status_code == 503


@DB
def test_authenticated_api_quota_denial_is_retryable_and_does_not_consume_input(identity_app):
    app, provider, alice, _ = identity_app
    owner = sign_in(app, provider, alice)
    app.state.settings.daily_user_run_limit = 0
    response = owner.post("/api/v1/sessions", json={"raw_input": "What is 17 * 6?"})
    session_id = response.json()["id"]
    denied = owner.post(f"/api/v1/sessions/{session_id}/run", json={})
    assert denied.status_code == 429, denied.text
    assert int(denied.headers["retry-after"]) > 0
    assert owner.get(f"/api/v1/sessions/{session_id}").json()["status"] == "created"
    assert owner.get("/api/v1/usage").json()["daily_remaining"] == 0
    assert owner.get("/api/v1/usage").json()["active_runs"] == 0
    app.state.settings.daily_user_run_limit = 1
    assert owner.post(f"/api/v1/sessions/{session_id}/run", json={}).status_code == 200
    assert owner.get("/api/v1/usage").json()["daily_used"] == 1
    assert owner.get("/api/v1/usage").json()["active_runs"] == 0
