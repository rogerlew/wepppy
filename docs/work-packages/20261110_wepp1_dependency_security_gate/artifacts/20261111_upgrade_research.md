# Candidate upgrade research and isolated validation

**Status**: M0 accepted at `d4b175436`; M1 dispositions remain open. A bounded
crypto/TLS batch is implemented only in the detached candidate checkout.
Primary application dependencies, workflows and production deploy code are unchanged.

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

## Bundled Brotli boundary

Independent review rejects the upstream Pillow 13.0.0 wheel as a complete repair:
the tagged build selects Brotli 1.2.0 without the decoder correction, and the
actual wheel library lacks the fix marker found in the proven patched Python
Brotli extension. A bounded owned build with fixed Brotli or verified patched
distribution linkage needs codec/font feature parity before adoption. The
verified PyCurl 7.49.0 candidate wheel names Brotli 1.2.1, but actual patch and
runtime validation remain required. See the dedicated security review; no
library is cleared merely from a wheel or shared-library version string.

## Disposable authentication/transport trial

A derived disposable image, not the canonical final candidate, evaluates the
first proposed batch without changing repository requirements or running
services. Image ID:
`sha256:3d78af7e460a8239862a5bcf5a8b0ad1f060c7b4bc5652a25feb2aea07f02bac`.
The retained build and installed inventory confirm exactly four replacements
(Authlib 1.9.1, cryptography 50.0.2, certifi 2026.10.18, urllib3 2.8.0) and one
addition (joserfc 1.8.0). No other installed distribution changes.

The no-network/read-only trial runs as UID 1002/GID 130 with capabilities dropped.
Actual Authlib/JWK/RSA verification accepts a valid token and rejects 15 hostile
or invalid cases: issuer/audience/nonce errors, missing required claims, expired
or non-finite/boolean times, bad signatures and malformed tokens. Every rejection
raises a joserfc error outside the callback's current exception tuple. The future
batch therefore needs a narrow `JoseError` translation and actual callback tests;
library rejection alone does not preserve the user-facing failure contract.
Fernet tamper rejection and real Paramiko RSA-SHA256 signature checks pass.

Seven additional loopback TLS checks pass with generated test certificates:
trusted response, same-origin redirect, cross-origin authorization stripping in
Requests and urllib3, untrusted CA rejection, read timeout, and HTTP error
translation. No external service or production credentials are involved.

Raw scripts, image/build identity, direct version delta and command receipts are
retained in private `evidence/auth-candidate-trial-20261111/`. Its scan identifies
the new installed versions with no matching advisories in the retained database;
20 selected-package findings remain in inherited old build-cache copies. The
original database is stale. A separate fresh scan uses the November 11 06:21:32
UTC database and confirms zero matches for the newly installed versions; all
20 selected-package matches remain inherited old cache copies. Its report SHA-256
is `ae75221f36be0a0004fe0bdbd185f7c654885f97b667e7277a2c311a6f092c75`.
The native SBOM retains
all 2,099 executable coverage gaps. The actual callback probe confirms
`InvalidClaimError` escapes through `LoggedBlueprint`; it does not prove real
provider transport/state validation or full-login success.
These probes are compatibility evidence, not a replacement for a clean canonical
build, committed boundary tests, current advisory data or the full final gates.

The [joserfc changelog](https://jose.authlib.org/en/changelog/) records maintenance
through 1.8.0 on November 3, 2026 and compatibility changes during 2026, including
Python-version drops and an error-class removal. Pinning the evaluated version
limits surprise transitive upgrades. Python 3.12 satisfies its floor; the measured
callback exception change remains the concrete integration cost. The observed
upstream maintainer concentration and public sponsor links do not establish a
verified bus factor or future funding guarantee. Exact-version advisory evaluation remains required before
adoption; no scientific-path performance claim or replacement is proposed.

## First canonical build trial

A clean no-cache Compose build now evaluates only cryptography 50.0.2,
certifi 2026.10.18 and urllib3 2.8.0, plus pinning existing Brotli to its already
verified commit. The detached checkout is
`/workdir/wepppy-security-auth-candidate-20261111`, based on `d4b175436` with its
requirements diff retained privately in `evidence/crypto-batch-20261111/`.
LFS checkout/fsck/materialization checks pass. Base/vendor inputs and UID/GID
match the unchanged baseline. The build passes in 727.24 seconds and produces
`sha256:f0f3fbb48f4afe636eb8bfcc491d7fa28514543cc1fe4bc628bce8fda373da48`.
No production service is activated.

Direct baseline/candidate comparison confirms exactly the three intended
installed-version changes. Native GDAL/Fiona/Rasterio/PyProj versions and the
WEPPpyo3 import path are unchanged. Real RSA/Authlib, Fernet and Paramiko cases
have identical results, including the existing Authlib nonce-support bypass;
this batch does not clear that authentication finding. All seven loopback TLS
checks pass. The separate isolated test Compose project passes 51 focused
authentication/session tests. Raw receipts are retained with the candidate.

The fresh candidate scan completes with 3,034 matches and 330 ignored records;
none name cryptography, certifi or urllib3, including cache artifacts. Report
SHA-256 is `ba07f596350334e0242e830da11cdfb31b81333887029b7eb9fd0ba7f35f0b51`.
This is not whole-image clearance. A fresh baseline rescan against the same
database is being retained to separate advisory-database changes from upgrades.

The separate test-image extension builds successfully in 90.73 seconds with
the explicit local candidate base argument; its immutable default remains
unchanged. Its image is
`sha256:c52f34545097d7a46c88b381eeaefcd1852192474646b320cd6c94036f643d38`.
All candidate layers are its initial layers; the candidate tag remains stable.
Direct installed Python versions, native version/import readback and real
cryptographic case results are identical to the common candidate. Its running
test container consumes that exact extension image and all 51 focused tests
pass again. Compose uses test UID 1000/GID 993; separate direct probes use
production UID 1002/GID 130. This does not establish full production workflow
parity. Neither step publishes an image or changes production's Docker Compose path.

Independent correctness review caught a duplicate default digest in Compose.
The final wiring passes the optional environment variable through and leaves
the sole default in `Dockerfile.test`. Actual Compose build readback omits the
argument when unset; an explicitly empty argument fails the real build, and
the explicit local candidate rebuild passes. Correctness and operations reviews
pass for this bounded component. Browser provisioning adds 90 Debian packages
without changing or removing any common-image Debian package.

The same-database baseline has 3,056 matches and 330 ignored records. The
package/version/advisory multiset loses exactly 22 rows across the three upgraded
packages and gains none. Clean-build cache paths change for other packages;
both exact-path and package-level comparisons are retained, and no prior
path/layer applicability approval is automatically transferred.

An independently reviewed qualified repeat verifies unchanged database and SBOM
hashes before/after scanning, with identical match and ignored-match arrays.
Its report SHA-256 is
`6c545912cdabb69223c598ab3a504902cec72ed663deebeb2bce245c688193d8`.
Missing metadata for 12 CVE IDs leaves 73 explicit UNKNOWN finding rows in both
baseline and candidate; these remain review blockers. The scoped security review
passes continuation of validation, not release clearance.

Authlib and its new joserfc dependency are excluded from this first batch pending
the OAuth contract checkpoint. This separates compatible TLS/crypto repairs from
the confirmed callback error-contract change without silently dropping that
authentication finding.

## Authorized continuation (2026-11-12)

Promoted the previously clean-built, independently reviewed crypto/TLS batch
from the detached candidate into the main source: cryptography 50.0.2, certifi
2026.10.18, urllib3 2.8.0, and exact existing Brotli commit pin. This is the same
retained requirements patch, not a new compatibility claim. A new final image
from the eventual combined revision and all M4 gates remain required.
