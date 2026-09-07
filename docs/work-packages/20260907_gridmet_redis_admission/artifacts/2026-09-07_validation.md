# GridMET admission validation

Execution baseline: `583e6870c639999515035423f133e5925dae2da5`.
Accepted contract ancestor: `1b4835ca73bc67c9c84ecbb26f596aab4078e234`.
Automated runtime validation, independent reviews, and live Forest acceptance
pass for runtime candidate `ae5d107d44a77c6ff3d0288e97b86cac174a77a4`.

## Completed checks

- Final frozen implementation: `wctl run-pytest tests --maxfail=1`:
  **7,651 passed, 72 skipped, 3,106 warnings**, 770.34 seconds. No runtime files
  changed during this run. The nine real-Redis cases are skipped without their
  isolated endpoint and passed separately as recorded below.

- Initial full suite: `wctl run-pytest tests --maxfail=1`: **7,633 passed,
  70 skipped, 3,106 warnings**, 800.54 seconds. Review fixes landed while this
  run was active, so a second full run uses the frozen final implementation;
  its result is recorded above.

- Admission configuration/lifecycle: `wctl run-pytest
  tests/climates/gridmet/test_admission.py --maxfail=1 -q`: **45 passed**,
  9.38 seconds, after final review fixes.
- Real Redis: `wctl docker compose exec -T
  -e GRIDMET_ADMISSION_TEST_REDIS_HOST=gridmet-admission-test-20260907
  weppcloud bash -lc 'cd /workdir/wepppy && PYTHONPATH=/workdir/wepppy
  /opt/venv/bin/pytest tests/climates/gridmet/test_admission_redis.py
  --maxfail=1 -q'`: **9 passed**, 153.11 seconds. Scenarios: ownership/policy,
  FIFO, six-process occupancy, timeout, outage, clock disagreement, killed
  clients, corruption without writes, and automatic liveness renewal.
- Probe: `wctl run-pytest tests/tools/test_gridmet_admission_probe.py
  --maxfail=1`: **29 passed**. Six-process implementation smoke separately
  observed peak two, queuing, FIFO 1–6, no violation, and empty state.

- Baseline `wctl run-pytest tests/climates/gridmet/test_download_clients.py
  tests/nodb/test_climate_build_helpers.py --maxfail=1`: **54 passed**.
- Updated client lifecycle and legacy tests: `wctl run-pytest
  tests/climates/gridmet/test_admission_clients.py
  tests/climates/gridmet/test_download_clients.py --maxfail=1`: **53 passed**.
- Propagation focused suite: **56 passed**, with exact invocation and coverage
  in [call inventory](2026-09-07_call_inventory.md). Strengthened service tests
  subsequently reran: **12 passed**.
- `wctl run-stubtest wepppy.climates.daymet.daymet_singlelocation_client`:
  success, one module. `wctl check-test-stubs`: passed.
- `wctl docker compose config --quiet`: passed. Parsed JSON renders with
  enable false and true show all seven admission values consistent in default,
  batch, and fork/archive definitions; only the default and batch pools execute
  GridMET climate work and are activation targets.
- Configuration reference, Forest runbook, contract/ADR, and package scoped
  documentation lint: passed. Spelling previews and `git diff --check`: clean.
- Observe-only code-quality command completed; broad-exception enforcement
  passed. Existing Daymet allowlist line
  references moved with imports/signatures; handler behavior did not change.

## Isolated Redis fixture

Created disposable container `gridmet-admission-test-20260907` from the existing
`redis:latest` image on `wepppy-net`, without published ports, persistence, or
operational credentials. The server is separate from Forest's operational
Redis. Tests use an explicit test hostname and fresh subprocess interpreters
to bypass the repository's autouse recording Redis fixture. No database flush
is used. The executor removed this disposable container after validation with
`docker stop gridmet-admission-test-20260907`; `--rm` removed the container.

An optional `wctl check-test-isolation` invocation was stopped deliberately:
the wrapper accepts no target arguments and starts five full-suite iterations.
No randomization plugin was available. It is not reported as a passing gate;
the required single full suite continued independently. A scoped passthrough
option would avoid this unnecessary verification cost in future work.

## Remaining gates

None within this package. [Forest acceptance](2026-09-07_forest_integration.md)
passed across two containers, including both crash repetitions, a valid public
request, empty cleanup, and actual disable/restore rollback.
Independent correctness, QA, and security all passed with zero unresolved
findings; their artifacts record the regression evidence and dispositions.
The separate registry build, Kubernetes/openwepp.org deployment, and batch
validation remain operator-owned.

## Final code-quality observation

After committing, reran the observability tool against the fixed starting SHA
`583e6870c639999515035423f133e5925dae2da5` (remote master had advanced on push),
with outputs in `/tmp/gridmet-final-code-quality.{json,md}`. It analyzed 17
changed Python files. Four received a red highest metric band and four yellow;
there are no threshold-based failures. `radon` is unavailable, so Python
cyclomatic-complexity measurements are not claimed.

The long existing Daymet/grid retrieval functions grew only for explicit
configuration/lifecycle handling; preserving their established behavior kept
the change bounded. Acquisition's largest function shrank from 109 to 80
measured lines. The real-Redis scenario runner deliberately shares setup and
cleanup across nine subprocess scenarios, accounting for its function-length
band. Independent QA reviewed cohesion and meaningful coverage. These are
observe-only tradeoffs, not unreviewed runtime behavior changes.
