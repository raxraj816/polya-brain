# Explicitly unset session header crashes update

When a request uses a persisted session and explicitly unsets one header, the
session-update path raises an exception before saving the remaining headers.
Determine how the unset value reaches the failing operation and propose a
correction that preserves ordinary byte-valued headers.
