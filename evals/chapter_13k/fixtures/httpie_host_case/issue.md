# Lowercase Host header is duplicated during rendering

A request carrying an explicit lowercase `host` header is rendered with both
that value and a second `Host` value derived from the URL. Diagnose why an
existing case-insensitive header becomes invisible to the presence check and
recommend a regression check.
