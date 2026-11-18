# Final code rereview: vector upload normalization

Date: 2026-11-17  
Reviewed revision: `4654150c96183eb7913f8f086526c88ad6ee3ce9`  
Comparison base: `9ac7cb8f69cf5189cc80f5493e01c08c393da204`  
Reviewer verdict: **HOLD — three High and three Medium findings remain.**

This rereview is pinned to the committed revision above. Concurrent uncommitted
work in the shared task worktree was not treated as part of the candidate. No
runtime code was modified by this review.

## Prior code-finding dispositions

| Prior finding | Disposition at `4654150c9` | Evidence |
| --- | --- | --- |
| `VUN-CODE-01` — Batch resolved-path authorization / misplaced Culvert check | **Closed in implementation.** | `wepppy/microservices/browse/_download.py:502-551` removes the Batch-only predicate from Culvert and applies it to the resolved Batch target. Files API resolved-alias checks were also added. Dedicated Batch download alias coverage remains desirable, but no remaining implementation bypass was found in the reviewed path. |
| `VUN-CODE-02` — recursive hostile GeoJSON escapes cleanup | **Closed.** | `wepppy/microservices/vector_upload_normalization.py:766-864` bounds JSON nesting, translates parser recursion, and uses iterative coordinate traversal with an explicit depth limit. `tests/microservices/test_vector_upload_normalization.py:210-258` covers coordinate and parser recursion with terminal quarantine/accounting assertions. |
| `VUN-CODE-03` — Roads/AgFields failed replacement rollback | **Partially closed; Medium remains.** | Both controllers now stage and restore canonical files inside their replacement blocks, but later fallible completion work remains outside rollback. See `VUN-REREVIEW-04`. |
| `VUN-CODE-04` — browser-session uploads lose human provenance | **Closed.** | `auth.py:147-157` retains only the positive verified human principal ID alongside the session actor; AgFields/Omni and Batch map it to `RetentionActor("human", id)`. The receipt projection still omits session ID, roles, and raw claims. |
| `VUN-CODE-05` — actual-boundary format equivalence and artifact readback absent | **Open, Medium.** | The new exact-image test invokes only the shared normalization helper and copies to a generic file. See `VUN-REREVIEW-05`. |

## Remaining findings

### VUN-REREVIEW-01 — High — private archives are not usable through the owner archive workflow and have an invalid recovery path

**Locations:**

- `wepppy/rq/project_rq_archive.py:367-380,427-466`
- `wepppy/weppcloud/routes/archive_dashboard/archive_dashboard.py:73-123`
- `wepppy/microservices/rq_engine/fork_archive_routes.py:609-632,1543-1613,1666-1713`
- `tests/rq/test_project_rq_archive.py:723-780`

When a run contains retained vector attempts, the worker writes the archive at
`archives/private/<bundle>/<archive>.zip`. The existing archive dashboard still
enumerates only `archives/*.zip`, so the successfully created archive disappears
from the normal user archive list. The restore/delete admission helper explicitly
accepts only a basename directly below `archives/` and rejects any nested path.
Thus the UI cannot download, restore, or delete the new private archive through
the established owner workflow. The worker-only test calls
`restore_archive_rq` directly with a nested path and therefore bypasses the
actual API incompatibility.

The private archive receipt is also internally inconsistent. The worker records
`canonical_path=archive_name`, where `archive_name` is relative to the
`archives/` directory (`private/...zip`). Reconciliation resolves canonical
paths relative to `project_root`, so it looks for `<run>/private/...zip` instead
of the real `<run>/archives/private/...zip` and cannot recover the accepted
archive. The committed test expects the correct project-relative value at line
772, so the implementation and test cannot both pass as committed.

This breaks an established data-recovery workflow precisely for projects that
contain the newly retained user uploads. It also prevents ordinary lifecycle
deletion from releasing archive storage/accounting.

**Required closure:** Extend the owner/root-authorized archive list, download,
restore, and delete contracts to understand a validated private-bundle identity
without introducing a public alias. Verify the sidecar binding before restore,
use a project-relative canonical path beginning `archives/private/`, and exercise
the HTTP list/restore/delete boundaries rather than only the worker function.
Prove public/non-owner denial and owner/root archive readback.

### VUN-REREVIEW-02 — High — restore can race an active upload and delete retained evidence

**Locations:**

- `wepppy/rq/project_rq_archive.py:512-607`
- `wepppy/microservices/vector_upload_normalization.py:605-634`
- `docs/schemas/vector-upload-normalization-contract.md`, “Idempotence and Recovery”

Archive creation now takes the run's vector-retention scope, but archive restore
does not. Restore acquires catalog, config, Roads, and NoDb-related guards, then
recursively removes project directories at lines 591-606. None of those guards
is the `run:<runid>` lease used by Roads, AgFields, and Omni uploads.

A vector upload can therefore hold its scope lease, create and bind an attempt,
and stream the original while restore deletes the attempt tree. This loses the
user/hostile original and leaves a durable reservation whose bound path is
missing. Reconciliation classifies that state `blocked_missing_attempt` and will
not release or commit it, so the race also creates persistent ledger drift. The
archive test verifies that creation takes the lease but has no equivalent
restore/upload concurrency test.

**Required closure:** Acquire the same project scope lease before restore
inventory and retain it through destructive replacement, receipt/state restore,
and cache invalidation. Define safe recovery for a restore interrupted after
destruction. Add a real concurrency test that pauses an upload after attempt
binding and proves restore cannot delete or partially restore until the upload
is terminal.

### VUN-REREVIEW-03 — High — reconciliation can lose its global exclusion and erase live reservation accounting

**Locations:**

- `wepppy/microservices/vector_upload_normalization.py:128-145`
- `wepppy/microservices/vector_upload_normalization.py:356-562`

`reconcile_retention` acquires the filesystem-wide exclusion key with a fixed
300-second expiry at line 381. It never renews the key or reasserts its owner
token. The allowed operation can scan 10,000 reservations, walk and measure up
to the configured filesystem evidence bound, and rebuild every principal key;
that can legitimately exceed five minutes.

After expiry, `_RESERVE_LUA` sees no reconciliation key and admits a new upload.
The still-running rebuild can then delete the totals and all principal keys and
replace them from its earlier filesystem snapshot at lines 533-546. That erases
the new live reservation from aggregate accounting while its reservation record
continues to exist, defeating the in-flight, global, and principal bounds. The
finally block's owner-checked delete does not prevent this because exclusivity
was already lost. The current real-Redis test completes below the expiry and
does not exercise lease loss during scan/rebuild.

**Required closure:** Use a renewable owner-bound reconciliation lease or
periodically extend and assert ownership, especially immediately before every
mutation and before the rebuild transaction. If ownership is lost, stop without
changing counters. Add a deterministic short-lease test that admits a concurrent
reservation after expiry and proves the rebuild cannot erase it.

### VUN-REREVIEW-04 — Medium — Roads and AgFields rollback still excludes fallible post-publication work

**Locations:**

- `wepppy/nodb/mods/roads/roads.py:1157-1217`
- `wepppy/nodb/mods/ag_fields/ag_fields.py:296-330`
- `wepppy/microservices/vector_upload_normalization.py:1075-1149`

Roads restores its canonical upload and retained output snapshot only for
exceptions through the `with self.locked()` block. The fallible
`_append_roads_log` call occurs after that rollback boundary. AgFields likewise
restores its GeoJSON/Parquet pair only inside the inner replacement block, while
`request_catalog_refresh` executes afterwards. Both operations perform filesystem,
Redis, queue, or catalog I/O and can raise.

If either post-publication call fails, `PreparedVectorUpload.publish` sees the
new canonical hash and records `incomplete`; it cannot restore the prior
workflow resource or state. The request returns an error even though the prior
accepted resource was replaced. Roads and AgFields route/controller tests do not
inject these post-lock failures and prove reload/downstream preservation.

**Required closure:** Either include completion logging/catalog publication in
the reversible transaction or make those operations non-authoritative and
non-failing after an already committed acceptance with an explicit observable
retry contract. Inject failure at completion log, catalog request, NoDb dump,
and subsequent route invalidation; read back prior canonical hashes, controller
state, reload state, and downstream consumers.

### VUN-REREVIEW-05 — Medium — the new exact-image “workflow” test bypasses every workflow boundary

**Locations:**

- `tests/microservices/test_vector_upload_exact_converter.py:48-120`
- `docs/work-packages/20261116_vector_upload_normalization/artifacts/20261117_m3_m5_validation.md:24-28`
- active ExecPlan, M3/M4 and “Validation and Acceptance”

The new test parameterizes a string named `workflow`, but every case directly
calls `prepare_vector_upload` with only the shared geometry validator, copies the
candidate to a generic `accepted.geojson`, and compares that file's first
feature. It never calls the Roads Flask route/controller, AgFields route/NoDb
controller, Omni run or dry-run parser/build service, or Batch route,
`WatershedCollection`, and generated per-watershed input path. It performs no
controller reload and parses no next consumed/generated artifact.

Accordingly the retained claim that all five receiving profiles accepted all
suffixes is only common-helper/converter evidence. It cannot detect workflow
field requirements, mutation and error envelopes, reload selection, or
downstream artifact divergence. The ExecPlan explicitly says converter mocks,
successful jobs, and file existence are insufficient and requires every format
through the actual receiving boundary.

**Required closure:** Drive the exact converter fixtures through each real HTTP
boundary for Roads, AgFields, Omni run/dry-run, and Batch; reload the real
controller/state and parse the next workflow artifact. Compare semantic output
for GeoJSON, Shapefile ZIP, `.parquet`, and `.geoparquet`, and retain prior
accepted resource readback for each failed replacement.

### VUN-REREVIEW-06 — Medium — the rollout preflight rejects the healthy converter readiness contract

**Locations:**

- `tools/check_vector_upload_readiness.py:43-53`
- `wepppy/microservices/shape_converter/app.py:397-410`
- `docs/work-packages/20261116_vector_upload_normalization/artifacts/20261117_m3_m5_validation.md:48-57`

With binary admission enabled, the preflight requires
`readiness["status"] == "ready"`. The qualified shape-converter readiness
response returns `status: "ok"`, `check: "ready"`, and
`geoparquet_parser: "ready"`. Therefore the documented operator command rejects
every healthy exact candidate before rollout. It also treats the generic
`provenance: binary_binding_verified` marker as sufficient and does not compare
the expected qualified parser/image identity despite the validation artifact's
claim that it verifies exact provenance.

**Required closure:** Validate the actual readiness schema (`status == "ok"`,
`check == "ready"`) and bind the canary to the expected immutable image/parser
provenance recorded for rollout. Add tool tests using the real healthy response,
wrong parser identity, unavailable parser, redirects, and malformed JSON.

## Low maintainability observation

Roads creates its canonical backup and staged copy before entering the cleanup
`try/finally` (`roads.py:1159-1178`). Attribute-catalog or mapping failures can
leave hidden backup/temp files in the accepted upload directory. Move staging
under the cleanup boundary and add one pre-lock failure-injection assertion.

## Validation performed

- Read the complete successor diff and exact committed source for all prior
  findings, archive/recovery additions, activation tooling, and exact-image test.
- Direct `py_compile` passed for both new operator tools and the principal
  changed Python modules.
- A host-side focused pytest attempt was **not counted**: collection could not
  establish the repository's container dependencies (`python_multipart`) and
  the sandbox denied local Redis sockets. The retained container results were
  considered supporting evidence only where their test source matched the
  asserted behavior.
- Direct markdown lint of this artifact is required after authoring.

## Residual gates

The local exact converter image remains a candidate, not a published or deployed
artifact. Production identity, mount, Redis, network, publication scan, canary,
observation, and rollback evidence remain separately authorized rollout gates.
Those external gates do not waive the High/Medium source and acceptance findings
above.
