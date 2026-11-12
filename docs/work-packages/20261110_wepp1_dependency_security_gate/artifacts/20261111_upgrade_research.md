# Candidate upgrade research and isolated validation

**Status**: M0 accepted at `d4b175436`; M1 dispositions remain open. A bounded
crypto/TLS batch has been promoted to main source, followed by the reviewed
three-package parser candidate. Clean candidate builds and focused tests are
recorded below; final advisory clearance and M4 remain open. No production
activation has occurred.

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

## Small Python candidate batch (2026-11-12)

A disposable container based on exact crypto image `f0f3fbb48...` passed the same
operations before and after pyasn1 0.6.5, msgpack 1.2.3, nbconvert 7.17.2,
jupyter-core 5.8.1 and Werkzeug 3.1.9. These are retained fixed-version targets
from the qualified advisory report. pyasn1, msgpack and nbconvert are now
promoted as candidate requirements; the two OS-specific cases below retain their
existing versions to avoid unnecessary compatibility changes.
ASN.1 DER and MessagePack roundtrips/malformed input, actual notebook HTML/table/
output rendering, Jupyter secure-write permissions and Werkzeug multipart upload
all passed. No host runtime or production dependency installation changed.

Primary-source checks included [pyasn1 release metadata](https://pypi.org/project/pyasn1/0.6.5/),
[nbconvert changes](https://nbconvert.readthedocs.io/en/latest/changelog.html),
and [Werkzeug changes](https://werkzeug.palletsprojects.com/en/stable/changes/).
These document releases; compatibility comes from the actual trial, with the
final clean-image and full regression gates still outstanding. nbconvert output
filename behavior warrants representative report-output coverage at that gate.

Private evidence: `evidence/small-python-trial-20261112/` under the approved
store. Probe SHA-256 `0cc4220b0eb9a5df544f3e1f1b680c8d06a54a09e18b8e50df47bd901177d144`;
log SHA-256 `86aee9b13837ebc43c8bbb2af4ff1b9d6edbc5a32cdcef898e8e24ccca359406`.
Exit 0. The mutable-container trial is not a canonical rebuild, dependency
closure/parity proof, fresh scanner result, or M2/M4 milestone acceptance.

Independent applicability review confirms the Jupyter-core and Werkzeug findings
are Windows-specific in the upstream advisories, while this exact image is
Linux/amd64. Retain existing 5.7.2/3.1.6 versions and prepare candidate-bound
not-affected evidence rather than upgrade solely for those four rows:
[Jupyter advisory](https://github.com/jupyter/jupyter_core/security/advisories/GHSA-33p9-3p43-82vq),
[Werkzeug advisory](https://github.com/pallets/werkzeug/security/advisories/GHSA-g6x2-hccm-hh4m).
No owner disposition approval is inferred. pyasn1 needs OID/constructed-string
regressions; msgpack needs streaming/C-extension cases and resolution of the
upstream affected-range discrepancy; nbconvert needs output-extraction and
actual PATH-CE render coverage. Ordinary compatibility probes do not clear those
security boundaries or substitute for final clean-image tests.

## Clean parser candidate (2026-11-12)

Committed `6c0c213a262d1ed89de8bdfa4941b5caf00cb0fa`: pyasn1 0.6.5,
Msgpack 1.2.3, nbconvert 7.17.2. Jupyter-core 5.7.2 and Werkzeug 3.1.6 remain
unchanged. The clean detached no-cache Compose build passes in 584.36s, producing
`sha256:05f4d047b5460e0a867876aeff6af27b5515afab1a54b31b6b4a5df6d31931a9`.
The isolated test image is
`sha256:e285bdcbc5511728fe163ae022a8dfed7a3213f82e565ccf2fe2509e2d98847d`;
all 22 common-image layers are preserved. Python and native GDAL/Rasterio sentinel
readbacks agree across common/test images. No live forest dependency upgrade or
production deployment was performed.

Actual exact-candidate probes pass normal ASN.1/Msgpack/HTML operations, the
retained invalid-map memory and extracted-filename checks, partial Msgpack skip
recovery followed by another object, and nbconvert FilesWriter output containment.
The latter reads actual PNG bytes and generated Markdown links and preserves an
outside-directory sentinel. Pyasn1 timing remains compatibility evidence rather
than proof of its reported performance repair.

The real PATH-CE Quarto integration test passes (one test, zero skips, 208.02s).
The generated report and exact-threshold CSV are retained privately:
HTML SHA-256 `057af83ff2520b8f609aa0eb86bd0e454a9c31ba68a29720ab259dc7d78af49b`;
CSV SHA-256 `2aaab2616424346ce90f9a418433d0a1990d570e16926f3247050197bd65f6b3`.
The test verifies report assets and exact agreement between report/job selections
and costs. First disposable database startup exceeded its health window while
image export contended for I/O; its failed receipt is retained. After initialization
completed, the same standard startup passed without changing the health contract.

Private receipts, probe sources/logs, build inputs and artifact copies are under
`evidence/parser-batch-20261112/`. A complete fresh scan/reconciliation remains
required before this batch can receive fixed dispositions. These focused successes
do not establish final full pytest/npm acceptance or F6 M4.
