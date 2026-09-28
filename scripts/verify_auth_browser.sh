#!/usr/bin/env bash
# Isolated, loopback-only test identities; no real identity/provider credentials.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
python_bin=${PYTHON_BIN:-.venv/bin/python}
export POLYABRAIN_ENV=test
export POLYABRAIN_AUTH_REQUIRED=true
export POLYABRAIN_PUBLIC_ORIGIN=http://127.0.0.1:3014
export POLYABRAIN_SECRET_KEY=browser-test-signing-secret-32-characters
export OIDC_ISSUER=http://127.0.0.1:18005
export OIDC_CLIENT_ID=browser-client
export OIDC_CLIENT_SECRET=browser-secret
export OIDC_REGISTRATION_MODE=${OIDC_REGISTRATION_MODE:-invite_only}
if [[ "$OIDC_REGISTRATION_MODE" == self_service ]]; then
  export OIDC_ALLOWED_SUBJECTS=''
else
  export OIDC_ALLOWED_SUBJECTS=alice,bob
fi
export OIDC_BLOCKED_SUBJECTS=''
export OPENROUTER_API_KEY='' OPENROUTER_MODEL='' SEARCH_API_KEY='' SEARCH_PROVIDER=''
export POLYABRAIN_API_URL=http://127.0.0.1:18004
export PORT=3014 POLYABRAIN_TEST_AUTH=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3014
# Fail before spawning if ports are occupied; never test against somebody else's process.
"$python_bin" - <<'PY'
import socket
for port in (18004, 18005, 3014):
    with socket.socket() as server:
        server.bind(('127.0.0.1', port))
PY
log_dir=$(mktemp -d)
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  if [[ ${1:-0} != 0 ]]; then
    cat "$log_dir"/*.log
  fi
  rm -rf "$log_dir"
}
trap 'cleanup $?' EXIT
"$python_bin" backend/tests/fixtures/oidc_server.py > "$log_dir/identity.log" 2>&1 &
pids+=("$!")
"$python_bin" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18004 --no-access-log > "$log_dir/api.log" 2>&1 &
pids+=("$!")
# Start Node directly so cleanup owns the server process rather than npm's wrapper.
(cd frontend && exec node scripts/start.mjs) > "$log_dir/ui.log" 2>&1 &
pids+=("$!")
"$python_bin" - <<'PY'
import time, urllib.request
for url in ('http://127.0.0.1:18005/.well-known/openid-configuration', 'http://127.0.0.1:18004/health', 'http://127.0.0.1:3014/api/backend/api/v1/auth/session'):
    for attempt in range(60):
        try:
            urllib.request.urlopen(url, timeout=1).close()
            break
        except OSError:
            time.sleep(0.5)
    else:
        raise SystemExit(f'Service did not start: {url}')
PY
npm --prefix frontend run test:e2e -- --grep 'OIDC browser'
