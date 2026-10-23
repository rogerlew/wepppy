# Validation evidence

Implementation freeze: `a501c15cc`; contract ancestors `c4774cf2a`, `5ebc3b0ff`
and `fa5c40a76`. No branch change. The final scientific report is
[analysis_results_current.md](../../../../tests/roads/analysis_results_current.md).

## Scientific matrix and project checks

- Final matrix: `wctl run-pytest tests/roads/test_roads_matrix.py
  --basetemp=/tmp/roads-matrix-verified-oct23 -x -q`: **516 passed**, 361.05 s.
- Native audit: 3,015,504 PASS days; 6,942,672 WAT OFE-days; all six annual
  metrics agree exactly with independent native-source aggregation. See
  [independent audit](20261023_independent_native_review.json).
- Production grade cap, exact management plant/scenario semantics across all
  200 scheduled years, staged shared inputs and generated file hashes are checked.
- Three full-upload additive project checks and one explicitly limited positive
  unrutted check pass. Each preserves 2,383 recorded source files and 911 copied
  baseline files. Full-upload unrutted remains a verified negative control with
  two rejected upstream OFEs and no current receipt.
- Positive project roots: `/wc1/runs/ro/roads-validation-oct23-v2-bd`, `-v2-rd`,
  `-v2-rutted`, and `/wc1/runs/ro/roads-validation-oct23-unrutted-positive`.
  Each retains `validation.json`, before inventories, generated inputs and outputs.
- Negative root: `/wc1/runs/ro/roads-validation-oct23-v2-unrutted`, retaining
  `validation-negative.json` and the failed attempt in history.
- The positive unrutted case retains 54/55 upload features and exercises one road
  replacement plus one remainder on one target. It is not whole-upload success.
- Initial exploratory clones appended to the original Roads log through stale
  serialized paths; scientific artifacts and saved source state were unchanged.
  Final clones rebase paths before controller deserialization and pass full hash
  checks including the original log. Initial failure diagnostics are retained.

## Publication and focused checks

- Publication plus Usersum tests: **68 passed**.
- Fixture/failure contracts and Roads controller tests: **56 passed** before four
  additional tampering checks; latest fast contracts: **11 passed, 5 opt-in site
  tests skipped**. Full site CLI checks were executed separately as above.
- Stub completeness and changed broad-exception enforcement: pass; no new broad
  exception handler. Code-quality observability is non-blocking; production Roads
  logic shrinks by 28 lines. Reports retained at `/tmp/roads-quality.*`.
- Source report, guide and package Markdown lint pass. Scientific fixture trailing
  whitespace is preserved byte-for-byte intentionally; `git diff --check` reports
  only those source fixture bytes (channel/climate/groundwater inputs).
- Scoped vendor sync touches only `wepppy-roads`; vendor/source bytes match.
  Usersum contract validation: 79 docs, 79 navigation leaves, 3 vendors.
  Generated index drift is intentionally excluded from commits.
- [Live HTTPS evidence](20261023_usersum_http_validation.json): report, navigation,
  guide, vendor and followed report links all return 200 through forest's normal
  reverse proxy. No auth override. Internal Gunicorn/proxy-address probes were
  unsuitable for browser-prefixed HTTPS links; the actual public forest URL passed.
- A reviewed interpretation-only refresh explains the near-zero-denominator
  no-traffic contrast. Its script verifies that no other source or numeric evidence
  changed and retains previous report/context identities in provenance.

## Broad regression

**11,647 passed, 131 skipped, 8,820 warnings in 3,270.42 seconds (54:30)**;
exit status 0 against frozen implementation `a501c15cc`. This includes another
complete 516-case Roads execution and report freshness validation. Command:

```bash
wctl exec weppcloud env \
  PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers \
  PYTHONPATH=/workdir/wepppy MYPY_CACHE_DIR=/tmp/mypy_cache \
  /opt/venv/bin/pytest tests --maxfail=1
```

This is the canonical wrapper's test image/interpreter with an explicit child
browser-cache override. The host-only environment override is not forwarded by
`wctl run-pytest`; an initial run was stopped early and is not counted toward the
final broad result. Log: `/tmp/roads-full-regression-canonical.log`.
Log SHA-256: `19576f741f7a8b053233925e49b7f5aeb529c248ce5ef3cd30c68460aa6aa248`.

## Reviews and limits

[Correctness](20261023_correctness_review.md) and
[publication/isolation](20261023_publication_isolation_review.md) approve the final
implementation with no unresolved high/medium findings. The report explicitly
qualifies extreme detachment, zero legacy-profile lateral flow, signed deposition,
file precision, mixed-profile scope and limited unrutted coverage. No field
accuracy or production deployment claim is made.
