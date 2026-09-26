# SUDI-02 validation evidence

Contract ancestor: `313951562`, following independent correctness/security reviews.
Runtime code is not deployed. No production services were restarted.

## Generated and native behavior

The focused parser/WSU/source/artifact suite passed **248 tests**. The final format-focused suite passed **115 tests**, including complete
10-layer acceptance and 11-layer rejection for each new format. The additional
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
- Initial `wctl run-pytest tests --maxfail=1 -q`: **4,492 passed, 51 skipped**,
  then an incomplete conductivity-map test double failed because it lacked the
  real controller's `mode`. The fixture now covers unchecked ordinary, checked
  ordinary and checked uploaded soils and asserts both preparation flags.
  Its full module passed **32 tests**, and the correctness reviewer approved it.
- Broad continuation: 398 remaining files, retaining the `tests` directory entry
  point and ignoring the 269 completed files from actual contiguous collection
  order. **5,366 passed, 49 skipped, 12 subtests passed** in 526.42 seconds,
  exit 0. `20260926_regression_coverage.json` retains that split: all 667
  collected files are covered. Phase counts overlap in the rerun failing module
  and include collection-time skips; do not sum them as unique test counts.
  Final format-focused tests separately cover the precision fixes completed
  while the first broad process was already running.
- Final independent correctness/QA and dedicated security reviews: passed;
  no unresolved findings. Owner accepts all closures; no risk acceptance used.

The continuation's initial per-file ignore list was interrupted during slow
pathlib discovery after 187.78 seconds with no tests run. Compressing completed
subtrees reduced 269 ignores to 45 with an exact coverage check; the successful
continuation retained ordinary directory-based optional-test selection. The
known test-generated `man42_5.man.json` change (three parser flags) was restored
after inspecting the diff. No unrelated production code was changed.
