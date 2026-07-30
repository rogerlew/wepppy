# Final Validation - Topaz Conditioning WEPPpy Integration

## Verdict

PASS. The WBT release, WEPPpy integration, compatibility controls, local stack
restart, and operator-authorized project-scoped E2E all passed.

## Release Identity

- Contract-first ancestor:
  `5754a1e06798a2f116a04b5eff4601402e143962`
- WBT release commits:
  `0f226804e568c12bb698795f352c47ecbc324769` and
  `47ca8e44730c0691cfcf8ac2bfa106e792254b36`
- Installed WBT binary SHA-256:
  `e5b33364b788f0046db15760320c7b03c6412fda99987f2bbe3ac76ba53b4cd0`

After the local stack restart, `weppcloud`, `rq-worker`, and
`rq-worker-batch` all imported
`/workdir/weppcloud-wbt/WBT/whitebox_tools.py`, exposed
`WhiteboxTools.topaz_condition_dem`, and resolved the same installed binary
hash.

## Automated Gates

- WEPPpy full Python suite: 5,598 passed, 58 skipped in 663.70 seconds.
- Focused Python integration/contract set: 323 passed.
- Daymet-before-Topaz isolation regression: 3 passed after correcting the
  legacy test's module-level stub behavior; the module now imports the real
  installed `whitebox_tools` first and stubs only when unavailable.
- Frontend lint: passed.
- Frontend suite: 104 suites and 745 tests passed.
- Focused channel controller suite: 2 suites and 30 tests passed.
- Changed-module stubtests and `wctl check-test-stubs`: passed.
- `wctl check-rq-graph`: passed.
- Package, ADR, and Usersum documentation lint: passed.
- Changed-file broad-exception enforcement and `git diff --check`: passed.
- WBT `cargo test --locked -p whitebox-tools-app`: 132 passed.
- Seven production-representative WBT parity cases: passed.
- Both WBT wrapper-surface containment tests, including early output EOF with
  a surviving descendant: passed.

`wctl check-test-isolation` has a known low-severity reporting defect: it can
print success despite pytest exit code 3. It is not used as release evidence.
Explicit bidirectional ordering tests and the full green suite provide the
isolation evidence for this package.

## Local End-to-End Evidence

The operator authorized mutation of local run `austere-inaction` with config
`disturbed9002_wbt` after the automated gates and independent reviews.

- Stack restart: all 26 development services returned to running state.
- RQ discovery: live operation schema advertised the exact four-value enum,
  including `topaz`, and resolved the existing map extent, CSA 10.0, and MCL
  100.0.
- Pre-run persisted selection: `breach_least_cost`.
- Submitted operation:
  `rq_engine_fetch_dem_and_build_channels`, changing only the conditioning
  selection while retaining the discovered extent and channel parameters.
- Parent job: `30df3081-bed5-4cf1-b75d-63e792d03448`, finished.
- Fetch child: `df6bc618-98b3-4d72-8826-42184ce694fe`, finished.
- Channel-build child: `9713c6f4-f151-411d-b662-e864c43a4e06`, finished.
- Pipeline completion timestamp: `2026-07-30T03:15:24Z`.
- Post-run persisted selection: `topaz`.
- Post-run `relief.tif` SHA-256:
  `b96715730cc157261e894a36140a9bf1bf017733a35eff82616a4d0b733db074`.
- Post-run `flovec.tif` SHA-256:
  `d93cc5df6370b76b7180d30a75baa245b91042afbd935bb188e7bfcbf7c670c5`.

The run log records
`WhiteBoxToolsTopazEmulator._create_relief(fill_or_breach=topaz)` followed by
the unchanged flow-vector, flow-accumulation, and channel-extraction steps.
The expected watershed downstream steps were invalidated, including the
outlet; the readiness contract correctly reports `set-outlet` as the next
action.

The browser URL returned the normal CAP verification gate to the service
credential. No gate bypass was attempted. Actual option rendering, selected
state hydration, and both browser payloads remain covered by the passing
render and frontend contract suites.
