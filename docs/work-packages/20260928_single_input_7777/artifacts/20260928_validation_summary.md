# SUDI-03 validation evidence

Contract ancestor: `e3a12ba42`. Implementation: `84caefd61`.
Independent correctness and security reviews passed with no unresolved findings.
Local acceptance only; no deployment or shared-service restart.

## Supplied file and generated/native acceptance

Operator supplied `/tmp/boulderck_mica_1_7777.sol` on forest. Its exact 243-byte
CRLF content is retained as `tests/data/single_input_soils/boulderck_mica_1_7777.sol`.
SHA-256: `9ff8feb48350d47330b882d5ebe90076d07ee13d09335d4d12ac62fe6eda2350`.
A separate synthetic 7777 fixture provides distinct layer conductivity and profile
anisotropy sentinels for modification/boundary tests.

Focused parser, source publication and generated/native artifacts: **205 passed**.
Tests read actual prepared files and compare each OFE's fields/version/ksflag,
exercise native 1/2/12/32 OFEs for both supplied and synthetic 7777, and cover existing
formats. Explicit supplied-file assertions independently compare all ten numeric
fields of both horizons and restrictive `1 10 0.46`. The authored2400 mm depth is
preserved on disk; native internal1800 mm depth limits remain unchanged. Modifier
cases exercise saturation, kslast, minimum depth and exact-layer clipping through
single and3 OFE preparation. Source bytes remain unchanged; native loss outputs
are nonempty without NaN/Inf markers. Hostile labels, numeric syntax/range,
widths/counts, hydraulic bounds, float32 depth collapse and 10/11 layer boundaries
are tested before publication.

Existing validator/WSU/Pure-template/multipart regressions: **305 passed**.
An initial command used the wrong WSU test path and collected no tests; the
corrected command uses `tests/wepp/soils/utils/test_wepp_soil_util.py`.

## Live development workflow

`validate_live_7777.py` submits the exact supplied file through authenticated
rq-engine multipart transport, real Redis/NoDb/RQ, and the normal `_prep_soils`
and `_prep_multi_ofe` controller/service paths. Build job
`9b88943d-f2ca-4bca-9028-8e1345d64a7f` finished. Actual 2/12 OFE native inputs preserve
all source fields except selected saturation; fresh output is finite. Source
download returns the original bytes. See `20260928_live_acceptance.json` for
identity/umask, input/source hashes, output sizes and retained file paths.

Run `/wc1/runs/si/single-input-acceptance-20260925` is an existing disposable
development run with synthetic topology. The old long-lived worker rejected the
new version; a fresh RQ Worker retried only this failed acceptance job successfully.
Update web and workers together and restart workers during deployment as the
existing operator guide requires. This is not proof that shared workers are updated.

`validate_archive_7777.py` invokes actual archive/restore routines on that disposable
run. Restored metadata and original source bytes/hash match; see
`20260928_archive_acceptance.json`. Source and prepared inputs remain available
through the established browse/download paths.

## Quality gates

Full `wctl run-pytest tests --maxfail=1 -q`: **9,892 passed, 99 skipped,
12 subtests passed**, exit 0, 2429.35 seconds. The known test-generated
`man42_5.man.json` parser-flag changes were inspected and restored.
Frontend lint passed; **112 suites / 919 JavaScript tests passed**.
Shared stub completeness and broad-exception changed-file gate passed.
Targeted documentation lint passed after fixing an existing broken controller
link in the touched WSU README. Code-quality telemetry is observe-only; existing
WSU parser hotspot remains unchanged, with one preserving-writer field-order branch.
