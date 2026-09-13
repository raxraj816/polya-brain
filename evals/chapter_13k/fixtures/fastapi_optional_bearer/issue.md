# Optional bearer dependency rejects another scheme

An HTTP bearer dependency configured with `auto_error=False` correctly returns
no credentials when the header is absent, but still raises 403 when the header
uses another authentication scheme. Determine the inconsistent control path and
the correction required by the optional-dependency contract.
