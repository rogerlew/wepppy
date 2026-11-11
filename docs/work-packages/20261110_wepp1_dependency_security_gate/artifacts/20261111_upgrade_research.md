# Candidate upgrade research (not implemented)

**Status**: Research only; M0 baseline rerun and M1 dispositions remain open.
No dependency, application, workflow, or deploy-code changes are included yet.

## Initial compatible-batch candidates

Exact-image findings and upstream package metadata motivate evaluating Authlib
1.9.1, cryptography 50.0.2, urllib3 2.8.0, certifi 2026.10.18, and Pillow 13.0.0.
These are candidates, not accepted upgrades or fixed dispositions. PyPI metadata
and distribution hashes are retained privately under the baseline evidence root's
`upstream-metadata/`. Each requires actual candidate-image resolution, scan and
focused/full regression evidence.

Authlib 1.9.1 requires cryptography >=45.0.1 and adds joserfc >=1.6.8. The current
joserfc release observed is 1.8.0 (2026-11-03), requiring Python >=3.11 and the
already-used cryptography; optional pycryptodome is not requested. This is one
additional pure-Python runtime distribution, without a service or separate
environment. Its BSD-3-Clause metadata and upstream source are recorded, but
security and compatibility evaluation remains open before integration.

Precedent: the dependency evaluation registry has no joserfc evaluation. It is
the upstream Authlib JOSE implementation replacing Authlib's embedded JOSE
implementation. It must not replace the application's owned service-token HMAC
implementation or any owned native/scientific component. It does not touch a
geospatial/model critical path; no performance claim is made. Remaining tax
checks include exact-version advisory scan, API/history and maintenance review,
actual token validation, and error translation under the application contract.

The [Authlib 1.9.1 OpenID implementation](https://github.com/authlib/authlib/blob/v1.9.1/authlib/integrations/base_client/sync_openid.py)
uses joserfc verification and keeps the application's expected nonce authoritative.
Existing app OAuth route tests replace the client, so they cannot establish
actual JWK/signature/issuer/audience/nonce validation. Google configuration uses
OpenID Connect. Add real-library success and rejection checks when implementing
the batch, alongside the existing route regressions.

The verified PyPI joserfc wheel defines `JoseError(Exception)`, distinct from
the callback's current OAuthError/RequestException/TypeError/ValueError catch.
Exercise actual verification exceptions through the callback before accepting the
upgrade. Preserve the established login-failure redirect contract with narrow
translation if required; do not broaden authentication acceptance or add a broad
exception handler. The wheel SHA-256 is
`176b836ac7ed9a46a88629e24076314b475f33a75d0bad7f26146e572eed7c79`.

The [cryptography changelog](https://cryptography.io/en/latest/changelog/)
records API removals and stricter key/certificate parsing across 47-50. Python
3.12 and the current cffi 2.0.0 satisfy its metadata requirements, but consumers
such as Paramiko still need actual import and cryptographic operation checks.

Native GDAL findings cannot be repaired by blindly changing the Python pin:
exact-image readback identifies system GDAL 3.10.3 and a separate Rasterio-bundled
GDAL 3.8.4. Native compatibility and bundled-library coverage remain separate
M1/M2 work; no native migration or advisory-risk acceptance is inferred.
