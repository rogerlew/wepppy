# Vertical slice validation ledger

**Status**: Ready for controlled canary handoff; local gates complete with one confirmed unrelated baseline assertion. Cluster acceptance pending (2026-11-10).

## Fixture registration (M1)

Public `ned1/2024`, 30 m, `disturbed9002`, extent
`[-116.10,46.70,-116.09,46.71]`; output `dem/dem.tif`. Consumer is the
existing elevation-query HTTP endpoint (zero-write), with `_sample_dem` used for
local direct readback. Exact runtime and mounted-identity evidence remains a
cluster gate. Protected state is root NoDb plus the complete DEM tree and immutable
provenance; operational/catalog/manifest writes follow the canonical v1 contract.

## Acceptance evidence

| ID | Case | Required direct evidence | Status |
| --- | --- | --- | --- |
| V01 | Valid fresh definition | Actual request, normal project creation and NoDb readback | Local real initialization/RQ passed; cluster pending |
| V02 | Real acquisition | Source response/selection, retrieval time, raster hash and semantic parse | Real ordinary provider acquired; declarative source fixture passed |
| V03 | Identity/admission | Approved schema/digest, observed runtime binding; mismatch and missing-evidence refusal | Strict refusal and Pod mutation tests passed; live identity pending |
| V04 | Git publication | Exact tracked paths, attempt record/commit association; no secrets/bulk data | Real Git exact-path/checkpoint tests passed |
| V05 | Successful finalization | Writer completion, catalog/manifest validity, durable readonly and completion ordering | Real finalizer/manifest success and failure passed; cluster pending |
| V06 | Subsequent viewing | Real task consumes acquired raster; fresh visible output; protected paths unchanged | Real raster consumer + unchanged fingerprints passed; HTTP/browser pending |
| V07 | Mutation boundaries | UI/API/queued protected writes denied; valid derived writes allowed | Direct NoDb/Bootstrap/Flask/RQ refusal passed; cluster endpoints pending |
| V08 | Ordinary projects | Absent legacy metadata, valid optional empty state, ordinary DEM and Bootstrap behavior preserved | Ordinary acquisition, read-only and Bootstrap regressions passed |
| V09 | Duplicate/uncertain attempts | Duplicate submission/delivery and lost worker produce no unintended replay | Duplicate submission/claim/completion passed; live worker loss pending |
| V10 | Failure/cancellation | Source failure, commit failure, cancellation and finalization failure retain truthful outcomes | Real RQ source/commit/init/finalizer failures and queued cancellation passed |
| V11 | Recovery | Old writers stopped; explicit full rerun allocates new project | Unique UUID projects tested; live interrupted-writer cleanup pending |
| V12 | Access and redaction | Public-only admission; ordinary private behavior preserved, hostile paths/images rejected, logs/records omit secrets | Public-only contract; path/image/Git/redaction tests passed |
| V13 | Artifact observability | Live browser/download; archive/restore membership and record byte equality | Canonical archive/restore byte/fence tests passed; live browse/download pending |
| V14 | Runtime compatibility error | Visible later report failure leaves build history/protection intact | No compatibility layer; live optional report error pending |
| V15 | Cost | Acquisition baseline versus added hashing/commit time and storage | Small real fixture measured below; large ordinary DEM cost pending |
| V16 | Bootstrap exclusion | Declarative enable/push/checkout/no-prep rejected through actual entry points | Direct Bootstrap mutation and API regression gates passed |

## Evidence recording rules

Append exact sanitized commands, candidate revisions, project/job/attempt IDs,
paths and outcomes under each ID as performed. Record failures as well as passes.
Mocks cannot replace the changed writer, authorization or publication boundary.
Do not infer semantic raster validity from file existence or matching timestamps.
This ledger does not certify determinism or automatic cross-build comparison.

## Real local acquisition and job tree

Run `metastatic-interconnection`, canonical `/wc1/runs/me/metastatic-interconnection`,
ordinary initial job `88af4419-a979-4718-99d0-cf4e5f441443` took 3.960 s.
The isolated updated worker ran job `a7b1626b-9783-4b2a-9675-181de81067b0` on
`dem-local-103e5f977d244807a7d05c8cfcf0a650` in 3.683522 s; source boundary
acquisition 3.133311 s, hash/semantic readback 0.053871 s. These are two observations,
not a speedup claim or global budget. Registry identity is honestly `unknown`.
`get_wepppy_rq_job_info` readback: finished, no exception, empty children.

Both acquisitions produced SHA-256
`10b6b95c574f8a90e6fe5ebed0a56ae68f90f38129cd434c8d7cb04302698134`,
EPSG:32611, 37 rows x 26 columns, 962 valid cells, nodata -999999, elevation
989.341003–1066.154297 m. Bounds are
`[568792.1912008075,5172221.57294407,569572.1912008075,5173331.57294407]`;
resolution is 30 m. Center elevation query returned 1032.540283 m.
Observation attempt `f81665c3-1db0-4dc0-ad99-234fa07f4c3c` records source, effective
extent/center/zoom, worker/job and raster semantics under visible provenance.

## Local test runs

- New protocol + real adapter/RQ lifecycle matrix: 32 passed before final CLI
  empty-response regression; final rerun recorded below when complete.
- Fault matrix includes source error, initialized-empty-Git publication failure,
  initialization failure, malformed grid, queued cancellation, prefinalizer drift,
  protected-manifest failure and finalization failure. Fixture identities are not
  registry attestations. Failed science remains failed/read-only/unverified.
- QA additional real `browse.create_manifest` failure inside shared
  `set_run_readonly_rq`: 1 passed, 9 deselected. READONLY remains; durable error
  and no repeat enqueue/state overwrite asserted.
- Ordinary targeted regressions: 150 passed across two runs after correcting the
  worker test double to supply RQ's actual `perform` interface.
- UI/Bootstrap regression suite: 372 passed. Canonical archive additions: 6 passed.
- `wctl run-npm lint`: passed. `wctl run-npm test`: 124 suites, 1069 tests passed.
- `wctl check-test-stubs`: passed. Full Python gate and final graph/docs checks
  are still running/preparing; do not treat this entry as their result.

## Retained defects found and repaired

Real integration first rejected a valid raster because Ron stores SRID as string;
normalizing the evidence SRID fixed comparison. A later completion saw stale
process-local Ron state from before the RQ child; detached persisted verification
fixed that. Reviewer findings and their regressions remain in the independent
review artifacts; do not erase these failed observations from handoff.

## Final scoped gates and storage readback

`wctl run-pytest tests/rq/test_declarative_dem.py
 tests/rq/test_declarative_dem_integration.py tests/rq/test_project_rq_archive.py
 tests/rq/test_rq_worker_runid.py -q --maxfail=1`: **102 passed**, 59.58 s.
`wctl check-rq-graph`: passed after canonical regeneration (153 static edges).
`python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master`:
passed, 24 changed Python files, zero unsuppressed increase. Existing line-based
allowlist drift was resolved with explicit boundary rationale comments, not new
exception swallowing. Code-quality telemetry is observe-only; initial collection
lacked changed-file analysis before the implementation commit and radon is absent.

Real ordinary checkpoint `f68177f4d6be3076f2e0156418d6292603b091d8` tracks exactly
`attempts/f81665c3-1db0-4dc0-ad99-234fa07f4c3c.json` (1697 bytes). Local Git consumes
28115 bytes including repository metadata. Hash/readback time is measured above;
Git publication duration was not isolated, so no invented per-commit timing.

Source package (10 files) and v1 contract doc lint passed. Receiving package and
runbook lint passed using markdown-doc from its own repo; the wctl wrapper with
an out-of-root path panicked, so its failure is tooling scope, not a doc pass.
Spelling preview covered 14 documents; one harmless oversize normalization applied.
Receiving secret policy passed; synthetic render plus engine validate passed.
No generated overlay was added to active Flux resources.

Implementation candidate: `185429547`; inactive receiving handoff: open-wepp-org
`5c98b96`. Neither has been pushed or published by this task. Contract ancestry
is `d6e101ab8` before implementation. Final changed-file quality telemetry covers
29 files: new production modules remain green by LOC/function length; the real
lifecycle fault test is a 130-line yellow fixture to keep actual RQ setup/cleanup
and failure expectations together. Existing large shared files gained only entry
fences and archive ordering, not opportunistic restructuring. Python complexity
metrics are unavailable without radon; this is observe-only, not a claimed pass.

## Broad-run interruption and continuation

The original `wctl run-pytest tests --maxfail=1` visibly completed the test groups
through query-engine and entered roads. Its handle/final output was lost when the
execution environment reset; the process was no longer running. Its failure cache
is not a substitute for a retained test result. Do not report that run as a full
suite pass. The final scoped tests had already rerun all changed adapter boundaries.

A frozen-code continuation from `tests/roads` through all remaining test roots
collected 6642 cases and retained log/JUnit evidence. It stopped with **1393 passed,
35 skipped, 1 failed** in 535.22 s. The failure was the cache-ordering `DummyRon`
without `wd`, a required real controller attribute now read by provenance. Additive
`wd` and `runid` fields repair the double without changing production code or
bypassing evidence logic. Its module then passed **65 tests** in 9.91 s.
The remainder restarts at that entire module; results follow when complete.

Exact commands are `dem-broad-continuation-command.txt` and
`dem-broad-remainder-command.txt`. Local retained logs are
`/tmp/dem-broad-continuation.log` and `/tmp/dem-broad-remainder.log`; JUnit reports
are `out/declarative-dem-broad-continuation.xml` and
`out/declarative-dem-broad-remainder.xml`. Raw test logs are not published as project
provenance or committed as potentially sensitive operational output.

## Final local disposition

The retained remainder completed 4940 passes/207 skips before the unrelated
`test_runs_template_uses_the_ttl_deletion_usersum_doc_id` assertion. Both its test
and `templates/user/runs2.html` are byte-identical to contract ancestor `d6e101ab8`;
see `baseline_template_inputs.json`. Executing those two baseline files from
`out/declarative-dem-baseline-template/` reproduced the same missing
`runsTtlDeletionHelpUrl` assertion (1 failed, 0.97 s). No DEM change touches that
Runs-list template. This is a confirmed preexisting assertion, not an unexplained
regression or a claim that all repository tests pass.

With only that exact assertion deselected, the final template tail passed **16**
tests (10.33 s); the remaining `tests/weppcloud/utils` group passed **60** (11.86 s).
Its command was `wctl run-pytest tests/weppcloud/utils --maxfail=1
--junitxml=/workdir/wepppy/out/declarative-dem-broad-utils.xml`.
The four retained JUnit reports deduplicate to **6401 passed, 241 skipped, one
confirmed baseline failure** from roads onward. See `broad_validation_summary.json`.
The earlier full invocation visibly passed the preceding groups, but its lost
terminal result is not counted as a single full-suite pass. Final stub hygiene
passed again after the test-double correction; independent QA accepted that fix.

Local handoff is ready: focused lifecycle/artifact/guard gates pass, independent
reviews have no open high/medium findings, configuration is inactive and reviewed,
and no new production defect remains. The unrelated assertion stays outside this
package. Live image/platform identity, mounted runtime parity, actual HTTP/browser
and archive/download workflow, running cancellation and worker-loss evidence remain
M5 receiving gates. The package is **open**, not closed or deployed.
