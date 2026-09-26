# SUDI-02 validation evidence

Contract ancestor: `313951562`, following independent correctness/security reviews.
Runtime code is not deployed. No production services were restarted.

## Generated and native behavior

The focused parser/WSU/source/artifact suite passed **248 tests**. The additional
existing preparation/template suite passed **229 tests** (overlaps artifact tests).
All four soil versions executed with vendored `wepp_260803` at 1, 2, 12 and 32 OFEs.
Separate modifier/native cases exercise the single-OFE worker and 3-OFE preparation
for each new version, including 9002 adjustment flag zero (flag one is in baseline),
saturation, kslast on a developed label, minimum depth and exact-boundary clipping.
Generated inputs retain source version, avke, ksflag, restrictive values and all
seven 9002 hydraulic values except explicit selected modifier targets. Source
bytes stay unchanged; nonempty native loss outputs contain no NaN/Inf markers.

Fixtures deliberately separate base and appended water fractions and use
nondefault conductivity values so accidental Rosetta replacement is detectable.
Strict admission tests include native control tokens/quoting, comments at native
no-skip boundaries, widths/counts/trailing records, numeric nonfinite/range/underflow,
float32 strict-order collapse and preservation of valid original texture sums.

## Live development acceptance

[Reproduction script](validate_live_soil_formats.py) and
[retained JSON](20260926_live_acceptance.json) record authenticated multipart upload,
real NoDb/Redis/RQ, normal controller `_prep_multi_ofe` and service `_prep_soils`
entry points, native 2/12-OFE execution and authenticated download for each new
format. Run: `/wc1/runs/si/single-input-acceptance-20260925`; topology is synthetic,
not DEM delineation evidence. Generated per-version inputs remain under its
`soil-format-acceptance/` directory for normal inspection. JSON records source
and consumer hashes, identity, umask and native output sizes.

Long-lived development workers retained the pre-amendment validator. Each of
these disposable failed build jobs was successfully retried through RQ Worker
using a fresh process, without restarting any shared service. Deployment must
update web and workers together and restart workers. This is local acceptance,
not production rollout approval. Two initial acceptance-harness API assumptions
(RQ status enum versus string and read_source return shape) were corrected;
they were harness errors, not production defects.

## Quality gates

- JavaScript: **112 suites / 919 tests passed**; npm lint passed.
- WSU stubtest: passed. Shared test-stub check: passed.
- Broad-exception changed-file enforcement: passed; only existing allowlist line
  references shifted after adding one worker argument, with no new broad catch.
- Targeted docs lint, git diff whitespace and root AGENTS size gates: passed.
- Live archive/restore passed for the accepted 9002 source, preserving metadata
  and source hashes; see `20260926_archive_acceptance.json`.
- Broad pytest: in progress.
- Final independent correctness/QA and security reviews: pending.
