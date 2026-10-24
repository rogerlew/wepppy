# Implementation correctness review

Reviewer: independent correctness agent, 2026-10-23. Baseline: `dc2b2ddbe`.
Scope: publication, receipt acknowledgment, reader barriers, admission/reconciliation,
lifecycle exclusion, and migrated producer boundaries. Production deployment was
not performed by this reviewer.

## Disposition

No remaining blocking correctness finding in the reviewed implementation after
the fixes below. This is an implementation review, not production rollout
acceptance. Final repository gates and the actual environment/workflow evidence
remain the execution lead's responsibility.

The authoritative source-selection decision is recorded in the refresh
[contract's Reader freshness and caches section](../../../schemas/query-engine-catalog-refresh-contract.md#reader-freshness-and-caches).
Without a producer receipt, an allowed explicit `fs_path` remains authoritative;
the barrier verifies that selected source. A captured producer invalidation may
advance inherited selection to the newly published canonical artifact. Recurring
full reconciliation handles receipt-free publication. This preserves existing
report selection semantics instead of treating every child copy as authoritative.

The isolated Mill Creek workflow reached a terminal scientific acceptance
failure. M4 and M6 full-workflow acceptance remain incomplete and blocked; neither
successful catalog maintenance nor the passing Roads evidence resolves that gate.
The terminal disposition and independent raw-artifact checks are recorded below.

## Findings and closure

| Finding | Severity | Disposition and evidence |
| --- | --- | --- |
| Inventory stopped at a project and only traversed `_pups`, omitting supported RHESSys scenarios. | P2 | Closed. `_inventory_step` now includes `rhessys/scenarios`, `_base`, and `runs`; bounded nested-scope coverage is in `tests/rq/test_query_catalog_rq.py`. This was also independently identified by the execution lead. |
| READONLY transition could freeze pending receipts, after which ordinary context resolution attempted a forbidden refresh and failed indefinitely. | P1 | Closed. `set_run_readonly_rq` drains parent/nested receipts under owner exclusion before freezing the project. Tests cover successful drain before manifest creation and failure retaining writable state and pending intent. |
| A captured child artifact invalidation could continue selecting inherited parent `fs_path`. | P1 | Closed with the authority distinction above. Explicit receipt refresh selects the published child artifact; no-receipt barriers preserve explicit parent selection. Child receipt regression and existing relocated-parent report regression cover both directions. |
| Equal size and restored modification time caused strict refresh to reuse an obsolete Parquet schema and acknowledge its receipt. | P1 | Closed. Required Parquet metadata is rebuilt and validated against actual schema, including field metadata. The retained same-stat regression verifies the new schema and acknowledgment. |
| Schema could change after candidate collection while preserving size/time; final validation read the new schema but discarded it. | P2 | Closed. Final validation compares normalized actual schema and raises `CatalogRefreshConflict` on drift, retaining the receipt. Independent injected-after-collection reproduction passed. |
| Initial schema comparison rejected stable Date32 files because native `Date32` and PyArrow `date32[day]` representations differed. | P1 | Closed. Full strict candidates normalize schema with the existing Python schema reader before validation. A Date32 full-scan regression and independent real-Parquet probe pass. |
| Recording incarnation A then re-resolving before enqueue could admit work for replacement incarnation B while returning receipt A. | P1 | Closed. Admission receives immutable receipt identity and original namespace. An independent restore-between-record-and-enqueue probe is rejected before queue admission. |
| Receipt readers could raise `FileNotFoundError` when a worker acknowledged and removed a discovered receipt, producing a false missing-run response. | P1 | Closed. Discovery tolerates acknowledged disappearance; barriers load the catalog after receipt discovery. A two-thread probe paused the reader across publication/acknowledgment and verified the new schema without a missing-run error. |
| Default historical roots included an absent legacy namespace, preventing cycle completion and repeatedly rescanning valid roots. | P2 | Closed. Enabled mode requires explicit `QUERY_CATALOG_ROOTS_JSON`; configured missing namespaces remain visible failures. Default disabled synchronous operation remains available. |

The initial Roads lock-order concern was corrected during review: existing Roads
locks use nonblocking acquisition, so an indefinite deadlock was not demonstrated.
It was not retained as a proven P1 defect. Exclusive Roads operations join catalog
ownership before taking the Roads guard; ordinary shared reads retain concurrent
admission under the narrow exception reviewed below. Fork acquisition orders and
deduplicates owner identities.

## Recheck evidence

Independent filesystem probes used real Parquet files and the local virtualenv:

- Parent-backed child metadata, followed by an explicit child invalidation,
  selects the child schema and physical source.
- A Parquet replacement with different field names, identical byte size, and
  restored nanosecond modification time publishes its actual new schema.
- The same replacement injected after candidate collection fails strict
  validation and retains its durable receipt.
- A stable Date32 Parquet completes full refresh successfully.
- A receipt reader paused immediately before reading its file survives concurrent
  refresh/acknowledgment and returns the newly published schema.
- Lifecycle rotation inserted between receipt persistence and admission cannot
  enqueue the replacement incarnation.

The publication implementer reports 25 focused core cases passing, including the
latest owner-READONLY case. The execution lead reports reader/MCP coverage (112),
report-cache coverage (51), fork coverage (113), Roads/archive coverage (68),
lifecycle regressions (16), queue coverage (24), and scheduler coverage (27).
These counts are implementation-team validation, not reruns by this reviewer;
the central execution evidence records the final commands and results.

Reviewed invariants include immutable finite receipt snapshots, acknowledgment
only after digest-bound publication, later receipts surviving acknowledgment,
catalog revision/incarnation comparison under the stable owner guard, no Redis
requirement for standalone synchronous calls, blocked admission retaining durable
intent, and publication refusing a replaced/deleted/readonly scope. Internal
reader barriers reload held metadata rather than relying on catalog membership.

### M4 malformed-catalog recovery recheck

The actual environment matrix exposed a further P1 recovery defect after the
initial review: submission remained responsive, but malformed catalog JSON failed
before worker repair and left its receipt pending. This finding is closed.

The repaired loader handles malformed JSON, encoding, and catalog structure as
unusable derived metadata. It logs the original digest and retains exact original
bytes in `_query_engine/refresh/attempts/malformed-*.json`. Permission and storage
errors remain explicit. Rebuilding forces full required-source validation even
when the original receipt named one asset; publication remains fenced by the
starting catalog digest and incarnation.

Independent direct probes confirmed successful rebuild/acknowledgment, explicit
catalog read denial, and failure on an unreadable untargeted Parquet while retaining
the original catalog, pending receipt, and failed status. The publication owner
reports eight focused malformed worker/barrier cases passing, including exact
retained-byte assertions; the expanded core suite passed 33 cases before the final
test parameter refinement.

The [environment rerun](2026-10-23_environment_probes.md#malformed-catalog-disposition-and-independent-rerun)
repaired the same previously failed scope using real Redis/RQ and NFS: 59 entries,
zero pending receipts, and digest-bound current status. The original authenticated
service-token request returned HTTP 200 in 0.904447 seconds; the rerun exercised
maintenance recovery, not a new browser session. Structured results are retained
in [environment_probe_results.json](environment_probe_results.json), with the raw
rerun at `/wc1/query-catalog-validation/20261023/malformed-retest.json`. Runtime
identity remains forest uid1000/gid993, not production uid1002/gid130.

### Roads concurrent-reader recheck

The execution lead's final audit found a P2 availability regression: the first
implementation held exclusive catalog ownership throughout a Roads shared read.
An independent pre-fix probe confirmed that a second shared reader returned
unavailable. The fix limits outer catalog ownership to exclusive Roads operations;
ordinary readers retain their established shared Roads lock and acquire catalog
ownership only for actual freshness barriers.

Independent post-fix probes used real current-result receipts and Parquet files:
concurrent readers succeeded in two threads and in a fresh Python process; an
exclusive writer remained busy while readers held their locks, succeeded after
release, and still excluded readers while active. A reader also completed actual
receipt-draining `ensure_catalog_fresh` while an archive took compatible shared
Roads admission and while an exclusive writer was rejected and released catalog
ownership. The lifecycle owner reports all 21 Roads lifecycle cases passing.

The narrow exception is documented in the [catalog publication contract](../../../schemas/query-engine-catalog-refresh-contract.md#publication-and-synchronous-coexistence)
and [Roads admission contract](../../../schemas/roads-preparation-lifecycle-contract.md#implementation-admission-and-retention-contract).
It relies on nonblocking Roads exclusive acquisition, no shared-to-exclusive
upgrade, and release of catalog ownership on conflict. Compatible archive shared
admission cannot wait on the reader. Catalog publication remains exclusively
guarded. This restores existing reader concurrency without introducing a general
reader/writer lock or expanding whole-project deletion snapshot guarantees.
These local probes do not certify cross-host Roads `flock` interoperability;
the catalog owner's separate POSIX-lock environment evidence is not a substitute.

### Roads scientific evidence publication recheck

The full-suite source-provenance gate correctly rejected the previous Roads
publication after runtime/native changes. The execution team reran all 516 matrix
cases and four fresh project designs before requesting publication. Independent
review approves publication of those regenerated results; it does not approve
production rollout.

[Retained independent results](roads_independent_numeric_review.json) record:

- Exactly 504 factorial cases and 12 one-factor controls, with the required case
  identities, arrangements, textures, finite metrics, and positive modeled areas.
  Every case's scientific metadata and numeric summary exactly matches the prior
  publication. Actual raw input, output, and template hashes were revalidated;
  none differs from the prior execution.
- Complete 2000–2015 calendars: 516 PASS profiles and 1,188 WAT OFE profiles each
  contain 5,844 distinct daily indices, with correct year alignment. Their tables
  contain 3,015,504 and 6,942,672 rows respectively.
- All 80 generated Parquet tables across four fresh projects have exactly equal
  Arrow values and schemas against the retained prior projects. File hashes
  changed; the only Arrow metadata differences are updated source hashes in the
  four segment summary tables. Prepared-input inventory differences are confined
  to root paths in `.err` logs; model inputs are unchanged.
- The three additive designs each execute 34 profiles. Positive unrutted executes
  one replacement profile with two summary rows and the previously reviewed
  54-feature selection. Independent daily water/area reconciliation passes for
  all four projects. Current receipts and generated artifacts are present.
- All 2,383 protected source files and each project's 911 baseline files retain
  their recorded hashes. The retained full-upload unrutted negative control still
  records the exact Topaz 271/272 nonpositive-upstream-OFE failures and has no
  current receipt. Its baseline also remains unchanged; the negative control was
  revalidated, not rerun as a new model experiment.

The review records the three changed runtime source identities and native
`wepp_interchange_rust.so` SHA-256
`7908a4fa667b149f4eee5a827dfb65c39c0c080369459b659c68cec26f411811`.
No scientific interpretation change is needed. Existing caveats remain: this is
one site's modeled experiment, and the positive unrutted feature exclusion
prevents treating all four designs as identical whole-watershed inputs.

Final publication readback passed at 2026-10-23 21:59:50 UTC. Published case
records and artifact identities match the approved analysis; all four project
validation-file digests remain unchanged. Current source/native identities,
result/report digests, report rendering, project summary/total hashes, and the
negative control agree with the approval. The scoped Usersum report is byte
identical, with its role, navigation, and link preserved. Final publication hashes
are retained in the JSON artifact's `publication_readback` entry. The publication
owner also reports all three publication tests passing.

### Terminal Mill Creek acceptance disposition

The isolated 184-year incident run failed at simulation year 100 with
`PASS components error: SOURCES3 date mismatch` and `STOP 1`. Independent readback
confirmed the error log SHA-256
`2a8e29641c1db74e1378624c997ff0f8607445686671c67ed1eae29753d814dc`.
All 1,908 hillslopes completed, but watershed success, downstream finalization,
and final channel/outlet/report consumption were not established. Seven downstream
stages remain deferred. Zero pending catalog receipts does not establish
successful scientific completion.

Independent inspection of the actual `pw0.run` confirmed exactly 1,908 sequential
raw `H1.pass.dat` through `H1908.pass.dat` references, with no HBP or Parquet input.
The unchanged runner launches the WEPP executable directly using that prompt;
`wepp_runner`, `WeppRunService`, and `wepp_rq.py` have no changes from the accepted
contract checkpoint. Independent readback also confirmed two distinct raw
`H1.wat.dat` observations for OFE 1 / day 365 / simulation year 104. The strict
water-balance report correctly rejects that duplicate. These observations locate
the failures before catalog lookup and show that catalog publication did not
create the raw duplicate dates.

The [terminal environment record](2026-10-23_environment_probes.md#terminal-outcome--full-scientific-acceptance-failed)
and [structured evidence](environment_probe_results.json) retain the failed job
tree, process exits, error hashes, and source identities. The supervisor stopped
before finalizers; worker process exit 0 does not override the recorded RQ job
failure. Original production raw output is unavailable for comparison. The paired
native build includes the disclosed preexisting calendar/HBP edits, although this
watershed run uses the raw ASCII path. Neither a preexisting-defect attribution
nor one shared cause for the watershed and water-balance failures is established.

Disposition: keep M4/M6 full-workflow acceptance blocked and make no production
readiness or incident-resolution claim. Existing partial submission, hillslope
query, authenticated summary, and exact-download evidence remains valid within
its stated scope. The narrow input-path and raw-output inspection is sufficient
for this catalog review; a scientific diagnosis and any changed inputs, date
handling, binary, or validation policy require separate scoped work. No rerun,
scientific fix, deduplication, shortened simulation, or dependency bypass was
performed or authorized by this review.

### Transactional enqueue metadata recheck

The final broad run exposed a P2 consistency defect outside the core admission
function: `wepppy/rq/auth_actor.py` saved actor/correlation metadata directly after
RQ staged a job in the caller's WATCH transaction. A real conflict discarded the
queued job but left a metadata-only `rq:job:*` hash. This finding is closed.

The final hook writes serialized metadata through the supplied pipeline, keeping
it in the same EXEC as job creation and admission. Ordinary enqueue calls retain
`job.save_meta()`. Independent inspection of installed RQ 1.16.2 confirmed that
`save_meta()` accepts no pipeline parameter; the final implementation exactly
matches its `serializer.dumps(meta)` and HSET operation using the caller's
pipeline. The intermediate API-compatibility issue was corrected before closure.
Reviewed `auth_actor.py` SHA-256 is
`364f1e8ed6d4293a8b09bc4f94808f351bc10c6d9df3e374322d09bdc54e48ca`.

The [retained combined validation](transaction_metadata_validation.txt) reports
70 passing cases. The real Redis regression installs the production hook with
active actor and correlation context, forces an actual competing WATCH write,
asserts no additional job hashes and preserved durable intent, then retries and
verifies actor, correlation, and maintenance metadata on the admitted job. The
same run covers ordinary hook/trace behavior, submission recovery, and
observability. This reviewer inspected the actual installed API, final source,
regression, and successful log; the 70-case execution belongs to the queue owner.
No remaining blocker was found in this fix. Terminal Mill Creek M4/M6 acceptance
remains blocked as recorded above; no additional model run or scientific change
was performed.

## Residual risks and coverage limits

- Production enablement still requires the actual identity, mounts, shared-lock
  behavior, consumer compatibility, scientific workflow, and capacity evidence
  required by the contract. Local probes do not substitute for those gates.
- Full strict scans perform extra Parquet schema readback. Measure that background
  cost on the incident workload and prove the configured complete-cycle target;
  source reconciliation is not an unconditional freshness deadline during outage.
- Catalog metadata publication is not an atomic scientific-data snapshot.
  Freshness-sensitive report publication retains its stronger source checks.
- Explicit `fs_path` selection without a receipt is intentionally preserved.
  Discovery of a newly published canonical override after the producer dies
  before receipt persistence depends on recurring full reconciliation.
- This review did not independently rerun the full repository suite or every
  migrated domain's production workflow. Those acceptance results belong in
  [execution evidence](execution_evidence.md), together with the independent
  security review and environment probes.
