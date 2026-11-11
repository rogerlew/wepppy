# Go JWT dependency evaluation

Status: accepted for the M0 checkpoint; implementation validation pending.
Date: 2026-11-11 UTC.

## Precedent and overlap

The dependency registry contains no JWT evaluation. Neither service Go module
has a JWT library. Existing Python token code cannot be imported by Go; porting
its cryptographic parser would violate this package's explicit prohibition.
Use an owned shared Go policy wrapper around `github.com/golang-jwt/jwt/v5`
version `v5.3.1`, once the contract is accepted. No new service or datastore.

## Dependency tax and maintenance

The [pinned go.mod](https://raw.githubusercontent.com/golang-jwt/jwt/v5.3.1/go.mod)
has zero external requirements and targets Go 1.21, compatible with the existing
Go 1.25 builders. The wrapper exposes owned claims and validation results,
keeping library types out of browser/Python contracts. It introduces one module,
no native build toolchain, and no framework data model.

The [release history](https://github.com/golang-jwt/jwt/releases) shows v5.3.1 as
latest at inspection, with multiple contributors and recent parser-option work.
A precise annual breaking-change rate, funding guarantee and maintainer bus
factor are not established; do not claim them. The /v5 module path isolates
major-version changes; review upgrades and run the negative corpus each time.

The published [allocation advisory](https://github.com/golang-jwt/jwt/security/advisories/GHSA-mh63-6h87-95cp)
affects v5 through 5.2.1 and is patched in 5.2.2. The published
[error-handling advisory](https://github.com/golang-jwt/jwt/security/advisories/GHSA-29wx-vh33-7x7r)
affects v4 through 4.5.0. Neither listed range includes 5.3.1; this is not an
assertion that future/unpublished vulnerabilities do not exist. Reject every
parse/validation error and enforce request-size bounds. Run the repository's
applicable dependency-security gate on the final module graph before deployment.

## Performance and acceptance

This dependency handles handshakes, not raster/hydrology/model execution; the
standard's scientific benchmark gate does not apply. Do not claim measured
throughput. Required acceptance is interoperability with Python-signed tokens,
strict algorithm/issuer/audience/time checks, all negative claim states, and
failure before upgrade/subscription. No marketing performance claim is relied on.
