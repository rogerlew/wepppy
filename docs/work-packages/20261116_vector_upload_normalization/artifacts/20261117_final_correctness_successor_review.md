# Final vector-upload correctness successor review

## Review identity and verdict

- Exact candidate revision:
  `04012d9b85b14db74a4f193101a4e2cf83e5041c`
- Exact local shape-converter image:
  `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`
- Scope: independent M3-M5 correctness closure review of the frozen committed
  successor, its contract, tests, active ExecPlan, tracker, and retained local
  qualification evidence
- Disposition: **HOLD**
- Remaining findings: **1 High and 3 Medium**

This artifact supersedes the correctness review of `061253c55`. The review is
based on committed objects from `04012d9b85b14db74a4f193101a4e2cf83e5041c`,
not concurrent working-tree changes. No runtime code was modified by this
review. Publication, remote-host parity, deployment, and production rollout
remain outside the execution authorization.

The successor closes the prior Batch transaction, active-project recovery,
partial-root rebuild, destructive-lifecycle intent, worker configuration,
derived-side-effect ordering, private-archive authority, and false final-image
provenance findings. It also correctly applies the ratified recovery rule at
`docs/schemas/vector-upload-normalization-contract.md:248-253`: a workflow
without a read-only authoritative adapter remains conservatively `incomplete`,
and canonical hash alone is never used as acceptance evidence. No adapter
redesign is required for this gate.

## Findings

### High 1: Redis loss can discard the admission authority of a durable rebuild obligation

The contract requires new reservations to fail closed while either side of a
destructive rebuild obligation remains pending
(`docs/schemas/vector-upload-normalization-contract.md:295-304`). The successor
persists a mode-private filesystem marker and mirrors its identity in Redis
(`wepppy/microservices/vector_upload_normalization.py:875-921`). Admission,
however, checks only the Redis set: `_RESERVE_LUA` tests `SCARD KEYS[5]` at
lines 128-131, and `RedisRetentionLedger.reserve()` supplies only the Redis
pending key at lines 314-327.

After Redis loss, the filesystem marker can remain while the Redis pending set
is empty. The documented recovery operation then makes the bypass durable:
`reconcile_retention(..., rebuild_ledger=True, apply=True)` does not inspect or
rehydrate `.vector-upload-rebuild-pending`, and it writes
`initialized=1` plus rebuilt totals at lines 613-684. The next reservation sees
an initialized ledger and an empty Redis set and is admitted even though the
filesystem obligation still exists. The activation readiness tool checks both
authorities, but an already-running web/rq-engine process does not execute that
tool on each request.

The retained obligation test proves blocking only while both markers exist and
then clears both normally
(`tests/microservices/test_vector_upload_normalization.py:390-441`). It does not
delete the Redis ledger while retaining the file marker, rebuild, and attempt a
new reservation.

Impact: the supported Redis-loss recovery path can re-enable uploads while an
interrupted project deletion, private-archive deletion, or destructive restore
still requires accounting repair. This violates the fail-closed ledger
invariant and can admit work against unverified global/principal totals.

Required closure: make the filesystem marker an admission/rebuild authority,
not readiness-only evidence. Under the exact-root reconciliation lock, validate
the obligation directory without following symlinks and rehydrate or otherwise
bind every valid file marker into the Redis pending set before initializing the
ledger. Refuse reservation/rebuild on malformed or unaccounted markers. Add a
real-Redis test that retains a file marker, removes the Redis namespace, runs
the documented rebuild, and proves admission remains blocked until exact
recovery readback and ordered file/Redis clearing complete.

### Medium 1: interrupted private-archive bundle deletion has no retryable route

The private delete route validates the archive, receipt, and sidecar before it
creates or resumes the deterministic deletion obligation
(`wepppy/microservices/rq_engine/fork_archive_routes.py:625-681,1773-1803`). It
then removes the whole bundle with `shutil.rmtree()` before rebuilding the
ledger at lines 1825-1849.

If `rmtree()` removes `normalization.json` or the sidecar and then fails while
the ZIP remains, the obligation correctly stays pending. A retry cannot reach
that obligation: `_resolve_run_archive_path()` sees the remaining private ZIP,
fails provenance validation because a companion file is absent, and the route
returns `400 validation_error` before taking the run scope or rebuilding. The
successful test covers only complete removal followed by an absent-target retry
(`tests/microservices/test_rq_engine_fork_archive_routes.py:1492-1559`); it does
not inject partial `rmtree()` failure.

Impact: one ordinary partial filesystem failure can leave the global
rebuild-pending gate closed indefinitely with no contract-compliant API retry.
The state fails closed, so this is an availability/recovery finding rather than
an evidence disclosure or accounting undercount.

Required closure: when the deterministic private-delete obligation already
exists, resolve the globally qualified bundle identity without requiring the
partially deleted bundle to pass accepted-archive provenance validation, while
retaining strict ancestry/symlink checks and owner/Root authority. Remove the
remaining whole bundle, rebuild, read back, and clear the same obligation. Test
failures after removal of each companion, a remaining ZIP, an already absent
bundle, and a symlink substitution.

### Medium 2: one reconciliation run recovers only one stale reservation per project

For every stale noncommitted reservation, `reconcile_retention()` obtains a
nonblocking project-scope lease and keeps it in `held_scope_leases` until the
entire command finishes
(`wepppy/microservices/vector_upload_normalization.py:405-436`). The next stale
reservation with the same stored project scope tries to acquire the same key,
observes the reconciler's own lease, and records `active_scope_skipped`.
Therefore abandoned reservations accumulated by sequential crashes in one run
or Batch project require one operator invocation per reservation. The audit
incorrectly labels the reconciler's own lock as active workflow ownership.

This is safe against concurrent mutation, but it prevents one bounded `--apply`
run from terminalizing the full inventory promised by the recovery command and
can leave the eight-slot global in-flight ceiling exhausted. The retained
active-scope test covers one reservation only
(`tests/microservices/test_vector_upload_normalization.py:525-595`).

Required closure: retain acquired leases in a map keyed by project scope and
reuse the owned lease for later reservations in that scope, renewing it before
each mutation. Add a real-Redis test with at least two stale bound reservations
for the same project plus an actually active project, proving complete recovery
of the former and zero mutation of the latter in one invocation.

### Medium 3: retained final5 evidence does not prove reload/downstream acceptance

Final5 has useful exact-image route-adapter coverage across GeoJSON, Shapefile
ZIP, `.parquet`, and `.geoparquet`, but the authoritative workflow objects are
still replaced in the acceptance selections:

- Roads uses `RoadsStub`
  (`tests/weppcloud/routes/test_roads_bp.py:25-254,474-495`);
- AgFields uses `DummyAgFields`
  (`tests/microservices/test_rq_engine_ag_fields_routes.py:23-181,359-383`);
- Omni uses `DummyOmni` and bypasses real prevalidation
  (`tests/microservices/test_rq_engine_omni_routes.py:1292-1356`); and
- Batch uses a fake ledger/lease, `DummyBatchRunner`, and `DummyCollection`
  (`tests/microservices/test_rq_engine_upload_batch_runner_routes.py:52-110,
  204-243`).

Those selections parse the canonical GeoJSON immediately after the request.
They do not recreate the real controller from durable state or parse the next
consumed/generated artifact required by the ExecPlan: Roads segments, AgFields
rotation/field data, Omni run/dry-run reports, or Batch
`dem/target_watershed.geojson`. Signed-session-to-terminal-receipt/principal
attribution likewise remains helper/monkeypatch evidence rather than one actual
authenticated boundary readback.

The retained M3-M5 summary names the final5 image and reports `480 passed, 5
skipped`, but names no exact application revision at
`20261117_m3_m5_validation.md:3-6`, supplies no exact command or skipped-test
identities, and contains no per-workflow downstream artifact receipt at lines
20-39. This does not meet the active ExecPlan's explicit requirements at
`implementation_execplan.md:317-332,348-368`; mocks, successful requests, and
file existence cannot establish artifact acceptance.

Required closure: on one named committed revision and final5, submit all four
accepted suffixes through each route, recreate real authorities from durable
state, and semantically parse the named next artifact. Retain exact commands,
fixture hashes, results/skips, receipt/original/canonical hashes, reload state,
and downstream semantic readback. This is an acceptance-evidence gap; the
static runtime mapping appears consistent.

## Prior-finding closure audit

| Finding from `061253c55` review | Result at `04012d9b` |
| --- | --- |
| High: Batch replacement not transactional through receipt | **Closed.** Batch uses `publish_transactional()`, retains canonical and serialized-state snapshots through receipt completion, and preserves accepted/pending accounting on Redis commit failure. |
| High: reconciliation can terminalize active project work | **Closed for active-work safety.** It acquires and renews a nonblocking stored project scope before mutation. Same-project reuse remains Medium 2. |
| High: descendant root can rebuild global totals | **Closed.** Reconciliation requires exact resolved root equality and has rejection coverage. |
| Medium: delete/restore/project-delete accounting is not retry-safe | **Substantially closed.** Deterministic dual markers, exact-root rebuild, readback, absent-target retry, and restore/project-delete integration are present. Redis-loss authority remains High 1; partial private deletion remains Medium 1. |
| Medium: production workers lack retention identity/root | **Closed.** The consuming production worker definitions receive both values. |
| Medium: exact-image reload/downstream proof absent | **Open as Medium 3.** Final5 crosses route adapters but still stops at stub-backed canonical readback. |
| Medium: AgFields catalog and Roads log can record rolled-back uploads | **Closed.** These effects occur after accepted receipt completion and failures no longer trigger false rollback. |
| Medium: unrelated Admin can operate private evidence | **Closed.** Owner or Root is required consistently. |
| Medium: final4 names nonexistent source | **Closed.** Final5 names resolvable source commit `e172f9f8a23c10774f87828181048c72188ba78a`, and the qualification records source-manifest comparison. |
| Prepared process-death recovery lacks an adapter | **Closed by recorded authorization.** The contract expressly requires conservative `incomplete` where an adapter does not exist and forbids hash-only promotion. |

## Exact-image and validation assessment

The final5 qualification is internally consistent with the supplied candidate:

- `git cat-file` resolves parser source revision
  `e172f9f8a23c10774f87828181048c72188ba78a`;
- retained SPDX SHA-256:
  `bd4b97c3ea517e214626f2371aaa0fca399e8a8f08354ed91625ea1258305fed`;
- retained Grype SHA-256:
  `5b21d0f4b905f00c10b306a2bfc8167e88e8700628c742009c6afa1501c89878`;
  and
- qualification image ID:
  `sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.

The retained 480-pass result is audited as evidence, not independently
promoted. A host-side focused rerun could not collect tests because that host
environment lacks `python_multipart` and sandbox policy denies its Redis socket;
this is a reviewer-environment limitation, not a candidate test failure. The
working tree also changed concurrently after the frozen commit was verified, so
no later working-tree run can be counted as validation of `04012d9b`.

## Disposition

Revision `04012d9b` must not complete M5 or be activated while High 1 and the
three Medium findings remain. Fix them on one committed successor, retain the
missing real reload/downstream evidence, and repeat the independent closure
reviews against that exact revision and final5. Image publication, registry
integration, remote-host parity, deployment, and production canaries remain
separate, genuinely unperformed gates.
