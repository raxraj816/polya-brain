# Path output fails on first write

Configuring the tracer with a filesystem path succeeds initially, but the first
attempt to write trace output raises `NameError`. Writing to an existing stream
does not show the failure. Identify the failure mechanism and the smallest safe
correction, then name a regression check.
