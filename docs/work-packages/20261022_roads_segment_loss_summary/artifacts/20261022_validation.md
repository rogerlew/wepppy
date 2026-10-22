# Segment summary validation

## Generated-artifact evidence

Final controller run on the isolated, previously archive-restored UM1 copy:
34 source-profile rows; 4,810.818379721261 kg/year sediment;
1,008.0648908316255 m³/year runoff; 4,127.15 m² modeled area.
Independent comparisons cover all six extensive annual metrics on every row
against original UM1 native PASS and all modeled areas against original WAT.
216 protected scratch artifacts and 46 original Parquets remain unchanged.
See [UM1 receipt](20261022_um1_validation.json) and [reproducible probe](validate_um1.py).

The canonical archive filesystem helpers restored the corrected copy at
`/wc1/runs/ro/roads-segment-summary-validation`. Summary, manifest, H.pass and
H.wat bytes and modes were preserved; summary mode is 0644. Job/status/lock/cache
callbacks were isolated, so this is filesystem archive evidence, not an RQ job
or production deployment claim. See [archive receipt](20261022_archive_validation.json)
and [probe](validate_archive.py).

Actual Chromium navigation to the live browse service listed the restored
summary. Live authenticated Parquet and CSV downloads returned 200; Parquet
bytes match, CSV has all existing columns plus additive provenance, and every
row's sediment and unavailable buffer alias match. The existing active dev-agent
account supplied a 300-second run-scoped token through the standard issuer;
live authorization and feature identity checks ran without mocks. No credentials
are retained. See [browser receipt](20261022_browser_validation.json) and
[probe](validate_browser.py). Producer/archive/browser probes ran as uid 1000,
gid 993 using normal container mounts. Python Playwright is not installed;
the successful probe uses the already installed Node Playwright and Chromium.

## Gates

- Focused canonical `wctl run-pytest` over source-summary and Roads controller
  modules: 76 passed, two existing dependency deprecation warnings, 13.83 s.
- `wctl check-test-stubs`: pass.
- Broad-exception enforcement against checkpoint `bac3042b1`, including the
  staged new helper: pass, zero added broad catches.
- Independent [correctness review](20261022_correctness_review.md): pass;
  empty-facade climate dependency found and corrected with real regressions.
- Independent [security review](20261022_security_review.md): local checks pass;
  final receipt disposition pending.
- Broad regression and final documentation gates: running.

The broad suite uses `wctl exec weppcloud env` to invoke the same container pytest
with `PYTHONPATH=/workdir/wepppy` and installed Chromium path
`PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers`.
This invocation supplies a per-process environment correction for the known
unrelated default browser path; it changes no runtime configuration.
No native API/stub or binary changes occur in this package.

## Limits and retained interpretation

This repairs source attribution and reporting, not physical model parameterization.
Full-profile exports are not incremental road impact or routed watershed yield.
Short-segment geometry and dominant-road behavior remain scientific questions.
Original `clogging-starch` is unchanged; its historic summary remains historic
until explicitly regenerated. No model rerun or production rollout is claimed.
