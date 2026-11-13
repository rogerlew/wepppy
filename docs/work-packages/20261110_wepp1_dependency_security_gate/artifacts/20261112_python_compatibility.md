# Python dependency compatibility remediation

Status: corrected clean image and scan complete; full Python gate running.
Native remediation remains open. Deployment resume is deferred; no activation.

## Corrected clean image

Revision `64cc736c2cc5217b6ae7eccdfd83ce936d80e3d4` builds clean image
`sha256:af7643725c95242e874a0ae218ecf8395a9641120aebcfb26822ad61aa50ee15`
in 534.85 seconds. All 187 focused tests pass. Actual PATH report generation
passes in 50.73 seconds, and decoded plot bytes match the earlier validated
artifact. Separate installed-package/source readback confirms OAuthlib 4.0.1,
sole libpass ownership and all seven selected copied-source hashes.

Fresh collection completes in 718.05 seconds with 2,716 matches/332 ignored and
zero OAuthlib matches. Manifest SHA-256:
`9f66a9c241686d763324517cbc345b3d4b1f6bf9d56f73f0be4c4545b6e40869`;
scan SHA-256:
`381e994b0dd421b39739bc37183365e2dc7a39e761d15d1025bfad81b961f53b`.
Private root: `python-repairs-final-20261112/`. This does not clear remaining
native coverage or advisory dispositions. Node 20 lint and all 1,076 Jest plus
three Node tests pass. The exact-image full Python suite is running without
overlapping heavy builds; receipt is `/tmp/f6-python-final-full-pytest.log`.

Later native work is recorded in
[GDAL/Rasterio qualification](20261113_gdal_qualification.md). Those private
drafts are not included in this frozen Python image or its acceptance evidence.

## Clean image acceptance continuation

Candidate `63ae6f9401bd733e0bc561f899d8953f74124250` built without cache in
519.35 seconds as image
`sha256:9f9e75e6515a9075769f07b6fba18c158e49cc4aec86b36553564af7f5b3920a`.
All 187 focused consumer tests pass. The actual PATH report passes in 57.49
seconds as UID 1002/GID 130; its decoded 864-by-1127 plot is nonblank and has
the same SHA-256 as the earlier native candidate. A separate container without
the checkout bind confirms installed package versions, sole libpass namespace
ownership and seven copied-source hashes against the committed candidate.
Private receipts are under `python-repairs-batch-20261112/validation/`.
The fresh collector completed successfully in 775.32 seconds, with 2,717 scan
matches and 332 ignored matches (previous native batch: 2,799/332). Scan SHA-256:
`6d75dfd6b21777fd6b161556dbfaa6e024a45b85db54a97805a7d78943c69f40`.
This is evidence collection, not policy clearance. The complete gate remains open.

The scan caught OAuthlib 4.0.0 still affected by
[GHSA-3jp2-3mrg-2vxc](https://github.com/oauthlib/oauthlib/security/advisories/GHSA-3jp2-3mrg-2vxc).
The candidate pin is corrected to the upstream fixed 4.0.1 release. Six runtime
files differ, primarily device authorization and validation; no owned device-flow
consumer was found. The derived trial passes 717 upstream tests, two explicit
skips and 21 subtests against the installed package; 38 existing OAuth/account
consumer tests also pass. A direct grant/token probe with a supplied validator
confirms missing and unknown codes issue/save tokens in 4.0.0 and are rejected
with HTTP 400 and no saved token in 4.0.1. The first attempt to run the new
upstream module against 4.0.0 fails collection on new constants and is not
counted as defect reproduction. Official wheel SHA-256:
`498a298876e996301950a5b053d12c31628bb7b895db03666430c69ce182eb61`.
Inputs, runtime diff and source tests are retained in
`oauthlib-followup-20261112/`. The earlier clean image remains bound to 4.0.0;
it does not prove the corrected pin. Another clean build/scan is required.
Independent follow-up correctness/security reviews report no High/Medium
findings within this pin correction. Private addendum hashes:
`ab2952237f3cdaff806b01ecfb0dfeece113badcd7ee6f28c9ad8f2905107c82`
(correctness) and
`00dac60c3168f5720e408de4ccc4fe506c2f876332d5b623002c0e06c1637320`
(security). These do not approve final-image acceptance or rollout.

The separate Rasterio 1.4.4 trial is not adopted. It supports NumPy 1.26 but
fails the existing `PROJ_LIB=/usr/share/proj` configuration because its bundled
PROJ expects a newer coordinate database layout. Removing that override only
for diagnosis gives identical raster arrays and metadata for eight operations;
GeoTIFF bytes differ and four drivers disappear (ARG, KML, MapInfo File and
OGR_VRT). This is insufficient workflow parity. Retained evidence lives under
`rasterio-compat-20261112/`; no runtime setting or package pin was changed.

The system-GDAL backport remains a private build trial. Before repair, all six
upstream hostile HDF4 fixtures crash both raster and multidimensional reads
(12 isolated process failures); valid Deflate64 decompression succeeds. The
probe uses bounded subprocesses and the evidence-owner UID to read private
fixtures, so it is defect reproduction, not production-identity acceptance.
Receipts: `gdal-repair-input-review-20261112/baseline-regressions-4.json` and
`regression-inputs.json`. Candidate ABI, drivers and regressions remain open.

## Qualified consumer batch

Tornado 6.6.1, SoupSieve 4.1, Jupyter Core 5.8.1, Bleach 6.4.0, OAuthlib 4.0.0,
Werkzeug 3.1.9, Mako 1.4.2 and fsspec 2026.6.0 install together without dependency
conflicts. The derived image `4e177fe111e2dbd1f162f0a4b611fdaa842a47b0e4e335efdb0bb0608a00f085`
passes 145 application tests and actual PATH report generation in 47.22 seconds.
Tornado's official runner passes 607 tests with six explicit skips. The initial
pytest invocation failed on logging-harness configuration, retained separately.

These tests exercise actual HTTP/TLS/compression, notebook HTML, migration
Python rendering, CSV/reference-filesystem/NetCDF values, form limits, CSRF and
remember-cookie consumers. They do not establish every advisory disposition.
Bleach's separately reported email-linkification issue still needs a narrow
reachability review; upgrading its version is not blanket clearance.

## Starlette adaptation

Trial Starlette 1.3.1 satisfies installed FastAPI's declared constraints. Replace
removed middleware decorators with their equivalent BaseHTTPMiddleware
registration in the same order, and supply explicit request/name/context to
TemplateResponse. Preserve the existing query-engine HTTP access, lifecycle,
request-payload and response contracts. This is API adaptation to preserve those
contracts, with no intended auth, CORS, abuse-control or page behavior change.

## Libpass evaluation before integration

Precedent search found no earlier libpass decision in the registry or developer
notes. Flask-Security 5.8.3 requires libpass >=1.9.3; it replaces the existing
external Passlib provider, with no owned-stack capability displaced. The BSD
wheel has no mandatory dependencies and optional bcrypt, Argon2 and TOTP extras.
Keep the existing bcrypt 3.2.2 backend, password algorithm, salt, schema, cookies,
CAP and custom registration forms. Do not install both distributions: each owns
the same `passlib` namespace.

The [upstream changelog](https://github.com/notypecheck/passlib/blob/main/CHANGELOG.md)
records 1.9.3 on 2025-10-09 and several compatibility releases since the 2024 fork.
It removes deprecated runtime APIs and fixes bcrypt version detection. Maintainer
continuity and funding are not independently established; no broad maintenance
or security guarantee is claimed. It uses the existing hash format and imposes
no new datastore or environment. This is an authentication dependency, outside
the scientific performance paths; no hydrology benchmark is applicable.

Accept for an isolated compatibility trial, conditional on bidirectional old/new
hash verification, exact namespace ownership, unchanged real login/confirmation/
reset/remember/CSRF/CAP behavior and fresh scan. A clean final build must replace
Passlib rather than overlay it. Full runtime acceptance remains required before
integration. Flask-Security 5.8.3 avoids the unrelated auth-default and schema
changes in 5.9; both existing Flask-Security distribution pins must stay aligned.
Email-validator 2.3 requires explicit strict local-part length validation to
preserve the previous boundary. Retain its newer Unicode security checks.

Private evidence root: `python-compat-batch-20261112/` under the F6 evidence
store. Exact wheel URLs, SHA-256 and dependency metadata are retained in trial
input receipts; required independent review packets are retained alongside.

## Tooling implementation and focused proof

System pip and ensurepip both upgrade to 26.3. A disposable virtualenv created
as UID 1002/GID 130 bootstraps pip 26.3 and installs the owned setuptools wheel
offline. The owned 80.10.2+wepp1 setuptools retains pkg_resources, applies four
exact upstream fixes and replaces its actual wheel/jaraco.context vendors.
Independent readback validates all 456 members and every RECORD. Four archive,
namespace and Unicode-manifest tests fail on the old image; their normal controls
pass. The upgraded focused tooling/auth selection passes all 19 cases, including
actual vendored tarball/conversion, generated sdist/wheel readback, registration,
confirmation/reset persistence, byte-salt/trackable auth and browser-relevant
redirect containment. An earlier oracle incorrectly demanded HTTP 200 for safely
encoded local redirects; revised checks inspect the emitted Location and reject
browser host-reference forms explicitly.

Starlette's query/shape/form selection passes 555 tests with two benchmark skips;
auth's existing selection passes 103 tests. Selected upstream SoupSieve tests
pass 10 with one parser-specific skip; DNS tests pass eight without external
network access or source-package shadowing. The opt-in nbconvert sanitizer
preserves readable output while removing active links/attributes.

The full suite stopped after 1,263 passes/43 skips on a disabled-feature test
fixture. The old dependency image reproduces it. Enabling the prerequisite only
inside that fixture makes all 83 malformed-route cases pass; production behavior
is unchanged. Full acceptance must be rerun. Node 20.20.2 lint passes and npm
passes 1,076 Jest tests plus three Node tests; these are candidate-source checks,
not final-image/M4 acceptance.

The host Pillow build initially rejected Ubuntu-added libc hardening imports.
Retained ABI readback proves only __memcpy_chk@GLIBC_2.3.4 and
__stack_chk_fail@GLIBC_2.4 are added; exports/loader remain identical and GLIBC
maximum remains 2.14. The qualified helper permits exactly those additions,
retains all original imports and enforces every other ABI/GLIBC/ISA guard. Host
wheel construction and dry-run shared dependency resolution now pass; actual
fresh and incremental disposable host installer runs now pass. Incremental
validation first introduces old Passlib, reruns the real installer, verifies
sole libpass ownership and verifies all old password fixtures. The working host
virtualenv is unchanged.

Fresh common-image construction/scan, complete regressions, remaining GDAL/native
coverage and advisory dispositions remain open. No rollout or risk acceptance.

Independent correctness packet SHA-256:
`342239b1f0f680d8ece23c62eee473a5dd05d61c88e7c66230a2652a282e6049`;
security/host-ABI packet SHA-256:
`c2fbd738884e5e5c1f9098068c74603b0625f5d276692a717bc6060e1aca99c9`.
Both have no unresolved Medium/High source findings; their final-image and native
coverage limits remain explicit. Packets live under the private Python batch
root in `correctness-implementation-20261112/` and
`security-host-abi-20261112T232239Z/` respectively.
