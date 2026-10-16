# M7 isolation repair security review

## Findings and verdict

**Pass for source integration.** No new high, medium, or low security finding
in the reviewed delta. Complete hosted isolation acceptance remains pending;
this verdict does not close that functional gate or replace correctness review.

| Surface | Finding | Required action |
| --- | --- | --- |
| Checker failure handling and import exceptions | No blocking defect found. Failed executions remain findings; import exceptions are bounded heuristics, not authentication. | Retain the documented limits and complete the hosted isolation gate. |
| CI diagnostics and execution | No new permission, secret, mount, network, or archive-traversal authority. | Preserve the existing isolated runtime and non-dereferencing archive. |
| Terrain conditioning integrity | Strict failure is forwarded to the existing WBT boundary; diagnostic validation is retained. | Complete normal correctness acceptance without weakening diagnostics. |

## Scope and triage

- Reviewer: independent `validation_security` agent, 2026-10-16 UTC.
- Context: working delta against `1951875ba`; no deployment performed by this
  review. Unrelated infrastructure documentation and generated docs index excluded.
- Security impact: **high** package classification retained because CI/tool
  execution and diagnostic publication cross process boundaries. Dedicated review
  required under the work-package security gate.
- Reviewed: `tools/check_test_isolation.py`, its regression tests, six Daymet/report
  test files removing collection-time stubs, `terrain_processor_helpers.py` and
  its tests, workflow source/generated output, the checker contract, diagnostics
  contract, and ADR-0095.
- Related evidence: [isolation follow-up](20261016_isolation_followup.md) and
  [correctness review](20261016_isolation_correctness_review.md), plus the
  [prior security review](20261015_validation_security_review.md). Earlier
  runtime confinement, storage, and archive-link probes are unchanged evidence;
  they were not repeated during this review.

## Boundary assessment

- **Valid state and failure integrity:** module inspection reads dictionaries
  without invoking lazy module `__getattr__`. Snapshots bracket collection and
  test execution after framework initialization and after fixture teardown.
  Missing requested snapshots fail explicitly. Nonzero pytest executions cannot
  disappear because repeats agree or a baseline suppresses a finding. CI does
  not use the existing explicit `--allow-failures` reporting option.
- **Expected imports versus leaked state:** newly loaded file-backed modules
  are permitted; replaced modules remain findings, including native helper
  names. Cython/SWIG/DuckDB exceptions use the listed names and shapes. Pint and
  Rasterio environment exceptions require a new file-backed dependency import
  and exact default values; existing-value changes/removals remain findings.
  Module attributes can be forged by test code. These checks diagnose accidental
  pollution and do not establish a security sandbox or authenticate provenance.
  Root conftest/plugin initialization is deliberately outside the measured
  interval, as documented in the checker contract.
- **Test dependency removal:** the six files remove persistent fake imports,
  including Flask, raster, and native-library replacements, while keeping test
  bodies and assertions. Missing canonical libraries now fail visibly. No
  production authentication, session, CSRF, or authorization code changes.
- **CI and logging:** the workflow delta adds only `--json`; structured failure
  details can contain environment differences and exception text. The reviewed
  Compose runtime supplies synthetic credentials and does not inherit deployment
  secrets, the host environment, or a Docker socket. Its internal network,
  explicit user, dropped capabilities, and checkout-only bind remain unchanged.
  The host archives `.pytest_cache` without following links and uploads only
  that regular tar file. No additional host-file traversal or credential source
  is introduced. The read-only workflow token and runner-01 exclusion remain.
- **Terrain integrity:** `derive_flow_stack` passes a boolean strict flag only
  for least-cost breach with filling disabled. Existing distance, cost, fill,
  path, executable, and diagnostic handling remain intact. Unresolved terrain
  fails at the native boundary instead of producing output rejected later;
  valid strict-mode output remains supported. This follows
  [ADR-0095](../../../adrs/ADR-0095-terrain-helper-strict-least-cost-breach.md)
  and the existing diagnostics contract. No fallback, new subprocess argument
  interpolation, queue edge, permission, or data-publication path was added.
- **Artifact observability:** per-worker logs and structured errors remain
  available through existing CI logs/archive. The terrain change retains the
  existing diagnostics writer and validator; no new hidden-only project record
  or archive exclusion is introduced. This review does not claim a new browser,
  archive/restore, or production terrain acceptance run.

## Validation evidence and limits

Independently read the executor's receipts:

- `/tmp/m7-checker-tests.log`: **15 passed**, two warnings, 16.60 seconds.
  Includes subprocess checks for collection-time stub/environment leaks and a
  clean pytest lifecycle, plus lazy inspection and failed-execution regressions.
- `/tmp/m7-isolation-repair-tests.log`: **142 passed**, eight warnings, 20.08
  seconds across checker, Daymet, reports, terrain helper, and the explicitly
  selected real-WBT integration module. The two real terrain paths were not
  skipped; existing diagnostics validation stayed active.
- Hosted run [38825109720](https://github.com/rogerlew/wepppy/actions/runs/38825109720):
  baseline **10,671 passed, 329 skipped**, followed by five passing suite repeats.
  No randomization plugin was installed; these were unchanged-order repeats.
  The subsequent per-file/state scan failed, so this is not complete isolation
  acceptance and predates this repair.
- Subsequent `/tmp/m7-isolation-runner-qualified.log` records the focused run
  and all 15 selected per-file runs passing, with final `issues: []` after the
  CFFI/Cryptography corrections below. The broader collection audit then found
  additional initialization differences; it is diagnostic evidence, not
  complete test-body acceptance.

Reviewer checks: workflow generation `--check` passed using the repository
virtualenv; `git diff --check` passed. No heavy runtime tests were repeated.

## Collection-audit follow-up

Reviewed the final checker and test delta after `/tmp/m7-collection-audit.log`
completed. Source integration approval remains unchanged; no new security finding.

- CFFI `Lib` objects, OpenSSL's native FFI/Lib pair, Cython ABI suffixes and
  `Cython.Shadow`'s `CythonDotParallel`, `CythonCImports`, and
  `CythonDotImportedFromElsewhere` use bounded shape/type recognition, as does
  `passlib.registry._PasslibRegistryProxy`.
  Cryptography and Passlib proxies expose their wrapped module dictionary
  through static fields, without invoking lazy attribute forwarding. Module
  identity tracking still detects replacements. Bare same-name stubs remain
  findings except the already documented minimal `cython_runtime` heuristic.
- `KMP_DUPLICATE_LIB_OK=True` is accepted only as an absent-to-default addition
  alongside a new file-backed Threadpoolctl/Scikit-learn import. Pyogrio and Fiona
  join Rasterio's exact Certifi-path initialization exception. Independently read
  `/tmp/m7-shape-probe.log`, which records Fiona's real import and the exact
  Certifi bundle additions during endpoint-test collection. The checker does not
  set these values, allow arbitrary certificate paths, or suppress existing
  values being changed/removed. The canonical checker inventory now names each
  exception; these remain diagnostic heuristics rather than provenance checks.
- The soil utility test removes its persistent `deprecated` stub. Two app-import
  tests scope `ASSET_VERSION` with `MonkeyPatch.context`, preserving an existing
  value and restoring absence after import, including exception exit. Production
  app initialization, account constraints, and route authorization are unchanged.
- Nonpositive iteration counts are now rejected. All detected module findings
  are reported rather than stopping at the first one. These changes do not widen
  baseline suppression or permit failed executions to pass silently.
- Independently read `/tmp/m7-checker-audit-tests.log`: **27 passed**, three
  warnings, 17.51 seconds, including real Cython/Passlib imports, bare-name
  negatives, and exact-default versus changed-value checks.
  `/tmp/m7-audit-followup-tests.log`: **98 passed**, eight warnings, 19.21
  seconds across checker, soil utility, RQ details, and PostgreSQL preferences.
  The 36-file collection recheck, four-file actual isolation, and complete
  hosted isolation were still pending at this review. No containment,
  production, or deployment change is included in this follow-up.

## Residual risk and sign-off

The previously documented persistent public-PR runner trust remains unchanged:
containers do not contain malicious workflow edits executed by the runner host.
JSON diagnostics are appropriate for this secret-free test runtime, not a claim
that arbitrary deployment environments are safe to publish. No new risk
acceptance is requested, and no inherited issue is represented as remediated.

Security reviewer: `validation_security`, source integration approved,
2026-10-16 UTC. Full hosted isolation and independent correctness acceptance
remain separate requirements.
