# Final QA successor closure review

Date: 2026-11-17
Reviewer: independent `qa_reviewer` (`final_qa_review`)
Reviewed revision: `04012d9b85b14db74a4f193101a4e2cf83e5041c`
Comparison revision: `061253c55a2a0e1cc8952143ebdf47cc40357a18`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final5`
Exact image ID:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`
Verdict: **HOLD M5 acceptance. One High and four Medium QA findings remain.**

## Review boundary

This artifact supersedes the QA closure review of `061253c55`. It reviews only
the frozen committed successor and exact final5 image named above against the
active ExecPlan, canonical normalization contract, prior QA findings, tests and
retained validation evidence. The task worktree was clean when the successor
review began. Later uncommitted normalizer, archive-route and test edits from
parallel remediation receive no credit here.

The contract at `vector-upload-normalization-contract.md:248-253` explicitly
ratifies conservative `incomplete` recovery when a workflow has no read-only
authority adapter and forbids canonical hash/file existence from becoming false
acceptance evidence. This review applies that decision: conservative
`incomplete`, after fencing the active project scope and retaining evidence, is
not treated as a defect merely because it does not infer acceptance or roll back
an ambiguous crash.

No runtime code, Redis state, image, registry or deployment was changed by this
review. Publication, remote-host integration and production deployment remain
separate, unauthorized gates.

## Prior-finding disposition

| Prior QA finding | Successor disposition |
| --- | --- |
| Batch late-failure replacement | **Closed.** Batch now uses `publish_transactional()`, retains prior canonical bytes and Batch state through receipt completion, and restores both on injected receipt failure. Accounting failure remains the intentional accepted/pending state. |
| Crash ambiguity and active-scope reconciliation | **Closed to the ratified contract.** Reconciliation non-blockingly acquires every noncommitted reservation's project scope, skips an active owner without mutation, and takes the conservative `incomplete` branch after release. Exact-root enforcement, symlink rejection and real-Redis scope/lock tests are present. No hash-only acceptance is credited. |
| Descendant-root global rebuild | **Closed.** Reconciliation requires exact configured-root equality before lock or inventory and has a no-mutation descendant test. |
| Roads/AgFields side effects | **Closed.** Receipt publication now precedes completion logging/catalog refresh. Post-commit side-effect failure is non-fatal or leaves the already accepted resource monotonic; tests cover both pre-commit rollback and post-commit interruption. |
| Destructive delete/restore accounting | **Narrowed substantially.** A deterministic filesystem plus Redis obligation is recorded before mutation; exact-root rebuild preserves unrelated active reservations; retry repairs an absent target; readiness and Redis admission block the normal pending-obligation path. Redis-loss mirroring and missing-configuration paths remain open below. |
| Private archive Admin authority | **Closed.** API and dashboard now require current owner or Root; an unrelated Admin is explicitly denied. |
| Production worker retention identity | **Closed structurally.** Production worker, fork/archive and wepp3 Compose paths now receive the filesystem ID/root variables. Blank values remain fail-closed for admission, subject to the destructive-path finding below. |
| Final4 source provenance | **Closed by replacement.** Final5 names Git-resolved `e172f9f8a23c10774f87828181048c72188ba78a`; the retained SBOM and Grype JSON parse and match their recorded SHA-256 values. Final4 remains disqualified. |
| Exact-image workflow/downstream proof | **Open, Medium.** Final5 supplies ten useful exact-image selections, but the five HTTP cases still stop at route adapters and canonical GeoJSON with workflow doubles. |
| Session actor provenance | **Open, Medium.** The successor does not add authenticated session-to-receipt/accounting/event evidence. |
| Retained evidence consistency | **Open, Medium.** Latest totals and image evidence exist, but exact commands, skip identity, current revision binding and downstream results are not consistently retained. |

## Open High finding

### VUN-QA-SUCC-01 — Filesystem rebuild obligations do not block runtime admission after Redis loss or stale restore

The contract requires both durable markers to survive destructive deletion or
restore and says new reservations fail closed while *any* obligation remains
(`vector-upload-normalization-contract.md:295-302`). The implementation checks
only the Redis set in reservation Lua (`vector_upload_normalization.py:128-148,
291-357`). The filesystem marker is checked only by the manually invoked
readiness script (`check_vector_upload_readiness.py:24-35`). Neither
`RedisRetentionLedger.reserve()` nor `reconcile_retention()` rehydrates the
Redis pending set from surviving files below
`.vector-upload-rebuild-pending`.

This breaks the dual-marker recovery invariant. If Redis is lost or restored
from a snapshot that predates the pending set, the filesystem marker survives
but the set is empty. Missing totals initially fail closed, but a normal
exact-root ledger rebuild can write `initialized=1` without restoring the
pending identity. A still-running web/rq process does not automatically execute
the readiness CLI. Its next direct GeoJSON or binary upload can therefore pass
reservation admission while the destructive operation's accounting obligation
is unresolved. A private restore can add retained bytes, so this is not limited
to conservative overcharging; admission can proceed from an undercounted ledger.

The new real-Redis obligation test covers only the normal state where the file
and Redis set coexist. It clears both through the helper and never deletes or
restores Redis while leaving the filesystem marker intact.

**Required closure:** make reservation admission fail closed on a bounded,
no-symlink readback of the filesystem obligation directory as well as the Redis
set, and rehydrate or preserve pending identities during Redis-loss rebuild.
Initialization must not become usable while an unretired file marker exists.
Add a real-Redis test that creates an obligation, loses the totals and pending
set while retaining the file, rebuilds, and proves both readiness and direct
reservation remain blocked. Retry the exact destructive operation, clear both
markers in the required order, then prove admission resumes with exact global
and principal totals.

## Open Medium findings

### VUN-QA-SUCC-02 — Final5 equivalence still does not prove real reload and downstream artifacts

The ten final5 selections are valuable: five exercise the shared normalizer and
five cross the Roads, AgFields, Omni run, Omni dry-run and Batch HTTP routes for
all four supported suffixes. The route cases still replace the authorities whose
state and downstream behavior are the acceptance target:

- Roads uses `RoadsStub`, copies canonical JSON and never builds/parses real
  road segments (`test_roads_bp.py:128-167,474-497`).
- AgFields uses `DummyAgFields`; no real rotation-schedule Parquet or detached
  controller is parsed (`test_rq_engine_ag_fields_routes.py:55-70,359-383`).
- Omni stubs queue/preparation, uses `DummyOmni`, and makes the run/dry-run build
  methods no-ops or a fixed dictionary; no `build_report.ndjson` is read
  (`test_rq_engine_omni_routes.py:1292-1356`).
- Batch substitutes `DummyBatchRunner` and `DummyCollection`; no real detached
  registration or generated per-watershed input is read
  (`test_rq_engine_upload_batch_runner_routes.py:204-243`).

All four formats run sequentially against one project with equivalent content.
The tests compare the first canonical feature but do not verify each iteration's
source receipt/hash, so an unchanged canonical resource can satisfy the equality
assertions. The Roads case uses dictionary equality rather than the retained
claim that all five use Shapely equality. Separate controller and rollback unit
tests improve confidence but do not establish the ExecPlan's required format ->
real receiver -> fresh reload -> next consumed/generated artifact chain.

**Required closure:** drive each suffix through the exact image and real workflow
authority using isolated projects or unique per-format markers. Read source and
canonical receipt hashes, detach/reload the real controller, and semantically
parse Roads segments, AgFields rotation/field artifacts, Omni run and dry-run
reports, and Batch `dem/target_watershed.geojson` or the actual generated run
input. Retain complete feature/property and Shapely geometry comparisons.

### VUN-QA-SUCC-03 — Destructive lifecycle silently bypasses obligations when retention identity is missing

Production Compose now passes the filesystem variables to workers, but their
defaults remain blank until an operator configures the feature. Whole-project
deletion enters the obligation/rebuild path only when
`VECTOR_UPLOAD_RUN_FILESYSTEM_ID` is nonempty
(`project_rq_delete.py:117-134`); otherwise it recursively deletes the run and
continues without a marker or ledger repair. Archive restore similarly creates
an obligation only when that ID is present
(`project_rq_archive.py:661-670`), even when restoring a verified private archive
or deleting a live run tree that already contains retained attempts.

This matters during rollback, partial configuration and existing-project
lifecycle. Retained evidence can outlive binary activation. A missing worker
variable must not silently authorize destructive mutation and leave old
filesystem/principal charges behind. The private archive delete route fails
closed, but project deletion and worker restore do not. Current tests cover
configured success and retry, not missing-identity negatives with retained
evidence.

**Required closure:** before destructive project deletion or restore, classify
whether the live tree/archive contains vector evidence or a pending obligation.
If it does, require the exact filesystem identity/root and fail before mutation
when either is absent or mismatched. Preserve legacy non-vector deletion/restore
without inventing a new global requirement. Add configured/unconfigured tests
with retained attempts and private archives and prove zero filesystem, receipt,
database and ledger mutation on failure.

### VUN-QA-SUCC-04 — Browser-session provenance remains helper-only evidence

The runtime reduction to a positive human user ID is plausible and existing
session-auth tests cover signed-session claim construction. The vector workflow
tests still call `_retention_actor()` helpers with synthetic dictionaries for
AgFields, Omni and Batch (`test_rq_engine_ag_fields_routes.py:1464-1473`,
`test_rq_engine_omni_routes.py:2181-2187`,
`test_rq_engine_upload_batch_runner_routes.py:762-768`). They do not submit a
signed owner session through the upload routes and read back the resulting
attempt receipt, Redis principal bucket and bounded
`vector_upload_security_event_v1`. Roads likewise lacks a request-to-receipt
actor assertion.

This leaves the user's requested provenance guarantee unproved at the actual
authentication/retention boundary and does not demonstrate that session ID,
roles, email/raw claims and client IP stay absent from durable evidence and the
security event.

**Required closure:** add authenticated owner-session route tests for Roads,
AgFields, Omni run/dry-run and Batch, plus relevant non-owner/anonymous
negatives. Read back receipt actor and source SHA-256, the exact principal
accounting bucket and the bounded security event. Assert only the verified
positive account ID is retained and every session/token/raw-claim/network field
is absent.

### VUN-QA-SUCC-05 — Final retained validation is not revision-bound or reproducible

The tracker records the successor aggregate as `303 passed, one skipped`, while
`20261117_m3_m5_validation.md` still identifies only ancestor `9ac7cb8f6` plus
an unnamed successor and records the older `480 passed, 5 skipped` bundle. No
artifact records the exact affected-suite command, the identity/reason for the
single current skip, or per-selection output. The M3-M5 file also repeats the
five-boundary Shapely claim that the Roads assertion does not implement. Its
activation rollback asks for downstream readback that the retained local
validation does not supply.

The final5 qualification correctly records the image ID, Git-resolved revision,
GeoParquet fixture hashes, tar hash, SBOM/scan hashes and aggregate 315/10 test
counts. It does not retain the referenced seven-file source sidecar/manifest or
the exact commands/output, and it omits byte hashes for the GeoJSON and
Shapefile fixtures used in the equivalence run. The tracker also retains the
current statement that Batch implementation/regression evidence is pending
while marking M3-M4 complete.

These gaps conflict with the ExecPlan requirement to record commands, revisions,
image digests, fixture hashes, results, skips and parsed artifacts
(`implementation_execplan.md:365-368`). Aggregate totals and prose assertions
cannot be independently replayed as the final acceptance record.

**Required closure:** update one canonical validation artifact with exact clean
revision `04012d9b85b14db74a4f193101a4e2cf83e5041c`, final5 image ID, every
command/environment, all source fixture hashes, individual selection results and
the one skip identity/reason. Retain the parser source sidecar/manifest or its
complete seven-file hash table. Correct the boundary descriptions and tracker
pending statement, and add the real reload/downstream results required by
`VUN-QA-SUCC-02` before claiming M5 acceptance.

## Accepted local controls and residual Low debt

- Final5's Git revision resolves, and its retained SPDX/Grype files parse with
  SHA-256 values matching the qualification. A fresh publication-time scan and
  immutable registry digest remain later gates.
- Batch live late-failure rollback, Roads/AgFields commit ordering, exact-root
  reconstruction, active-scope exclusion, unrelated-reservation preservation,
  owner/root archive authority and normal-path obligation retry are materially
  stronger and have focused tests.
- Conservative `incomplete` recovery is an explicit contract state. Operator
  guidance should make clear that it is uncertainty requiring retained review,
  not a rejected replacement or acceptance proof.
- `reconcile_retention()` grew into a large multi-responsibility function, and
  begin/rebuild/complete sequencing is repeated across destructive callers. Once
  correctness closes, a behavior-preserving recovery transaction helper and
  smaller inventory/mutation/readback functions would reduce further drift.
- The four exact-route tests duplicate format loops and ad hoc semantic
  dictionaries. Shared parameterized assertions would improve failure
  localization after real workflow coverage is added.
- Readiness still exposes malformed converter JSON as a raw `ValueError`; this
  is fail-closed but is Low operator-usability debt.

## Validation performed

- Verified the task worktree was clean at exact revision
  `04012d9b85b14db74a4f193101a4e2cf83e5041c` before successor review and used a
  clean `git archive` for supplemental commands after parallel edits appeared.
- Retained candidate totals supplied with the frozen successor: affected
  application suite **303 passed, 1 skipped**; exact final5 shape-converter suite
  **315 passed**; exact-image shared plus five route selections **10 passed**.
  These totals are credited at their stated boundaries, not as downstream
  artifact proof.
- Supplemental exact-archive readiness tests: **8 passed**.
- RQ dependency graph from the exact archive: **passed** (`RQ dependency graph
  artifacts are up to date`).
- Verified source revision
  `e172f9f8a23c10774f87828181048c72188ba78a` resolves to a commit. Parsed the
  retained final5 SPDX and Grype JSON and reproduced their recorded SHA-256
  values:
  `bd4b97c3ea517e214626f2371aaa0fca399e8a8f08354ed91625ea1258305fed`
  and
  `5b21d0f4b905f00c10b306a2bfc8167e88e8700628c742009c6afa1501c89878`.
- Static readback covered the exact successor diff, new failure/recovery tests,
  normalizer and destructive lifecycle, Compose propagation, active ExecPlan,
  tracker, contract, prior reviews and final5/M3-M5 evidence. No production or
  remote-host proof was attempted.

## QA disposition

Do not mark M5 complete or activate receiver-side vector admission on
`04012d9b85b14db74a4f193101a4e2cf83e5041c`. Final5 is the corrected local M2
candidate, but Redis-loss obligation authority, exact real-workflow downstream
proof, destructive missing-configuration behavior, session provenance and the
revision-bound evidence package remain open. Re-review one clean committed
successor after every High and Medium above closes. Publication, remote
integration and production deployment remain separate operator-authorized work.
