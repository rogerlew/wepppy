# Final operations successor re-review

Date: 2026-11-17
Reviewer: independent `ops_security_control_agent` (`final_ops_review`)
Source revision: `4654150c96183eb7913f8f086526c88ad6ee3ce9`
Source tree: `ad26419e1280f6cfacde91171a549188f2e709e3`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final3`
Exact image ID:
`sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`
Verdict: **REJECT receiver activation and M5 acceptance; three High and three
Medium findings remain. Continue local remediation only.**

## Review boundary

This is a successor review of the exact committed revision above. Concurrent
working-tree remediation appeared while the review was running, so all source
claims below were checked against committed blobs with `git show HEAD:<path>`;
uncommitted changes receive no credit. No runtime code, Redis data, container,
shared checkout, registry or production host was changed by this review.

The retained M2 qualification of final3 remains valid for the isolated converter
boundary. Its retained SPDX and Grype evidence hashes remain:

- SPDX JSON:
  `00fad0f0e8c143c47f78b67f6a0706f3d64e0103e4fd8217b10130445799dffa`;
- Grype JSON:
  `a359b57d30d90cdbc9e98d06eb80f47a1aeeda281583f56f0de95eb26c163345`.

This review does not reopen that local image decision. It reviews receiver-side
configuration, shared accounting, archive confidentiality and lifecycle, crash
recovery, provenance, rollback and operating evidence. Production publication,
remote integration and deployment remain explicitly excluded actions, not failed
local tests and not authorization granted by this review.

## Prior-finding disposition

| Prior finding | Successor disposition | Evidence and remaining control gap |
| --- | --- | --- |
| `VUN-FINAL-OPS-01`, ordinary archives expose sensitive attempts | **Partially resolved** | Attempt-bearing archives are now directed to mode-`0700` bundles below `archives/private`, with a mode-`0600` ZIP, SHA-256 sidecar and retention receipt (`project_rq_archive.py:341-380, 427-466`). Direct worker-level restore evidence exists. The 600-second scope lease is not renewable or checkpointed, however, so a long ordinary archive can lose exclusion before publication and admit a newly created sensitive attempt. The established archive API also cannot discover or resolve nested private archives. See successor findings 01 and 04. |
| `VUN-FINAL-OPS-02`, reservation expiry permanently consumes capacity | **Core defect resolved; successor lock defect remains** | Reservation records no longer expire while charged, retain owner/amount/principal/project/state, and bind the attempt path (`vector_upload_normalization.py:128-160, 199-231`). A real-Redis test fills all eight slots, releases proven pre-write reservations and restores admission (`test_vector_upload_normalization.py:261-346`). The filesystem-wide reconciliation lock itself still has an unrenewed 300-second TTL. See successor finding 03. |
| `VUN-FINAL-OPS-03`, post-mutation failure becomes false rejection | **Partially resolved** | Online accepted publication is monotonic across Redis commit failure, and uncertain mutation/readback paths become `incomplete` instead of an ordinary rejection (`vector_upload_normalization.py:1049-1149`). Offline reconciliation does not implement the contract's authoritative workflow-state check and cannot recover a `prepared` receipt as accepted. See successor finding 02. |
| `VUN-FINAL-OPS-04`, no deletion/archive/rebuild lifecycle | **Partially resolved** | A bounded audit/apply command and receipt-driven Redis rebuild now exist. Private archives carry terminal receipts. There is still no audited whole-attempt/private-archive export-delete operation, project-deletion integration or atomic post-removal decrement; rebuild also does not fail on every symlink as specified. See successor findings 04 and 05. |
| `VUN-FINAL-OPS-05`, browser sessions lose human provenance | **Resolved** | The signed session `feature_access_principal` is reduced to a positive human account ID, and AgFields, Omni and Batch accept the resulting session attribution (`auth.py:147-157`; `ag_fields_routes.py:174-188`; `omni_routes.py:209-223`; `upload_batch_runner_routes.py:131-146`). Route tests cover the session paths. Receipts do not persist the session ID. |
| `VUN-FINAL-OPS-06`, no activation/disable/rollback controls | **Partially resolved** | Production Compose defaults binary admission off in web and rq-engine (`docker-compose.prod.yml:141-144, 584-587`), UI and server use the same flag, and direct GeoJSON stays available. Readiness and reconciliation tools now exist. The preflight does not authenticate the expected exact image/parser provenance, and the rollout material omits a defined observation duration and numeric danger thresholds. See successor finding 06. |

## Open High and Medium findings

| ID | Severity | Finding | Exact closure required |
| --- | --- | --- | --- |
| VUN-FINAL-OPS-RR-01 | High | **A long archive can outlive the run-scope lease and publish newly created sensitive evidence as an ordinary archive.** `_RedisScopeLease` is acquired with a fixed 600-second expiry and supports only ownership assertion/release, not renewal (`vector_upload_normalization.py:568-634`). `archive_rq()` checks sensitivity once before ZIP traversal, never checkpoints the lease, and replaces the public-path temporary ZIP without rechecking sensitivity or ownership (`project_rq_archive.py:341-354, 394-427`). If an ordinary archive runs past 600 seconds, a new upload can acquire the expired run scope while the ZIP walk is active. Its attempt can then be included after the one-time sensitivity decision and published under `archives/<name>.zip`. This reopens the original hostile-evidence disclosure boundary under a realistic large-run/concurrent-upload condition. | Use an owner-checked renewable scope lease or equivalent checkpointed fence for the full scan/write/publish interval. Check ownership while walking and immediately before `os.replace`; abort and remove the temporary archive after any ownership loss. Re-scan sensitivity before publication or otherwise prove no sensitive root appeared, and reclassify to private only under a still-owned fence. Add a test that intentionally exceeds the lease lifetime, races a vector upload, and proves no sensitive byte or name can reach an ordinary archive or public route. |
| VUN-FINAL-OPS-RR-02 | High | **Crash reconciliation cannot prove authoritative workflow publication.** The reconciler checks only `status=accepted`, size and canonical-file SHA-256; every `receiving`, `source_stored` or `prepared` receipt is changed to `incomplete`, and no Roads/AgFields/Omni/Batch authoritative state or reload is inspected (`vector_upload_normalization.py:435-467`). Thus a crash after successful workflow mutation but before accepted-receipt persistence cannot become `accepted_recovered`, while an accepted file alone can be called recovered without proving controller/NoDb state. Private archive recovery is also deterministically misaddressed in this commit: its receipt stores `canonical_path=private/...` relative to the run root although the file is at `archives/private/...` (`project_rq_archive.py:445-460`). | Implement workflow-specific, read-only authoritative recovery adapters under the same project scope. For stale `source_stored`/`prepared` and accepted-pending receipts, compare candidate/source provenance, exact canonical hashes, persisted NoDb/controller state and reload/downstream artifacts. Mark `accepted_recovered` only when all authorities agree; otherwise preserve `incomplete`. Correct private-archive canonical addressing. Inject process interruption at receipt fsync/replace, mutation, canonical readback, Redis commit and lease release for all four workflows, then prove semantic reload and downstream artifact readback. |
| VUN-FINAL-OPS-RR-03 | High | **The filesystem-wide reconciliation fence can expire while a bounded rebuild is still mutating shared accounting.** `reconcile_retention()` takes a single 300-second Redis lock and scans as many as 10,000 reservation keys and 10,000 receipt trees, potentially over shared `/wc1`; it never renews or asserts ownership before terminalizing receipts or resetting the ledger (`vector_upload_normalization.py:356-385, 388-467, 469-547`). After expiry, another reconciler or new reservation can enter. The final Redis transaction is not conditioned on the original lock token. Concurrent reconciliation can therefore delete a committed reservation after the first scan passed its receipt and allow the first rebuild to replace totals with a stale undercount. The rebuild also silently prunes symlink directories rather than refusing the unverifiable tree (`:473-477`). | Replace the fixed fence with a renewable owner-checked lease. Checkpoint before each receipt mutation and immediately before the rebuild transaction; make the final ledger replacement conditional on continued token ownership and abort without mutation if ownership is lost. Refuse any symlink encountered in the evidence inventory. Add real-Redis/NFS-representative tests that force work beyond the lease lifetime, admit a concurrent reservation/reconciler and prove neither undercount nor double terminalization is possible. Retain before/after receipt and ledger readback. |
| VUN-FINAL-OPS-RR-04 | Medium | **Private archives are confidential at rest but are not a complete user/operator lifecycle and can bypass per-project evidence quotas.** `has_archive()` scans only direct ZIP children, while `_resolve_run_archive_path()` rejects any name containing a directory and requires the resolved parent to equal `archives/` (`fork_archive_routes.py:530-538, 609-632`). The worker therefore returns a `private/<bundle>/<zip>` name that established restore/delete API paths cannot resolve. The retained test calls the worker restore function directly, so it does not prove the user-facing route. Archive creation reserves global bytes and checks free space but does not apply the contract's attempt/archive/total per-project limits before adding another private archive (`project_rq_archive.py:352-380`). | Extend owner/root-authorized list, download, restore and delete flows to resolve only canonical private bundle paths without traversal or public aliases; make `has_archive` report them. Exercise those API routes as owner, non-owner and anonymous user. Before creation, include live attempts plus all private bundles in archive/total project quota checks, under the run-scope fence, and prove repeated archives stop at the documented limit without changing older evidence. |
| VUN-FINAL-OPS-RR-05 | Medium | **Project deletion and evidence removal still have no audited ledger lifecycle.** `tools/reconcile_vector_upload_retention.py` can audit/apply stale reservations and globally rebuild committed totals, but no project-deletion path invokes it and no command inventories, exports and durably removes an entire terminal attempt/private bundle before atomically decrementing its filesystem and principal counters. The current guidance relies on a later global rebuild after project deletion. That is conservative until counters exhaust, but it is not the contract's same-lock, explicitly audited deletion boundary. Empty attempt directories created between `mkdir` and reservation binding can also remain outside receipt-ledger reconciliation. | Add read-only inventory plus root-authorized export/delete operations. Under the same project scope, verify terminal receipt, regular files, sidecar and hashes; remove only the whole attempt/private bundle; fsync durable removal; then atomically decrement the correct filesystem/principal committed bytes. Integrate or explicitly invoke this flow from project deletion. Test failure before/after durable removal, empty pre-bind directories, idempotent retry, whole-project deletion, Redis loss/restore and concurrent cross-project activity. Never prescribe partial deletion or manual counter edits. |
| VUN-FINAL-OPS-RR-06 | Medium | **The local rollout package cannot yet prove the activated binary or define a bounded observation decision.** `check_vector_upload_readiness.py` validates the mount, private file mode, Redis ping and only two readiness strings, `status=ready` and `geoparquet_parser=ready` (`check_vector_upload_readiness.py:18-62`). It does not compare an operator-supplied final3 image digest, parser binary SHA-256, source revision or exact `Cargo.lock` SHA-256, despite the validation document claiming exact provenance. It also does not compare the filesystem ID/root and Redis authority across both participating services or exercise the Caddy/internal-network path. The M3-M5 rollout section names useful signals but gives no observation duration or measurable danger thresholds (`20261117_m3_m5_validation.md:48-70`), contrary to the ExecPlan (`implementation_execplan.md:316-320`). | Make preflight compare expected immutable image/parser/source/lock identities and resolved service configuration, and fail closed on any mismatch. Retain a local resolved-Compose/Caddy-path rehearsal under both production identities. Document workflow canaries with semantic artifact readback, a concrete observation duration and measurable ledger, stale-reservation, 5xx/507, disk and converter thresholds. Retain the existing immediate `VECTOR_UPLOAD_BINARY_ENABLED=false` rollback and verify direct GeoJSON after disable. Production-host proof remains a later, separately authorized gate. |

## Low findings and later gates

- `VUN-FINAL-OPS-07` remains Low. The structured quarantine event is bounded and
  avoids filenames, tokens, sessions and IP data, but it still lacks the
  contract's stable correlation ID and a documented operator query/retention
  procedure. Add the existing sanitized correlation/error ID; do not create a
  permanent ban store in this package.
- `VUN-FINAL-OPS-08` remains a later publication/deployment gate. Final3 is a
  local image ID, not a registry digest, and no production-host parity or rollback
  receipt exists. This is expected because publication and deployment were not
  authorized. A fresh publication-time scan, pinned registry digest and real-host
  canary/recovery receipt remain mandatory after local acceptance.

## Controls that are accepted locally

- Final3 remains accepted as the exact isolated M2 converter candidate with its
  retained SBOM, vulnerability scan, non-root identity, read-only root,
  capability drop, PID/CPU/memory limits and internal network evidence.
- Durable Redis reservation records and the real-Redis eight-slot recovery test
  close the prior reservation-record expiry defect.
- Successful accepted publication is monotonic when Redis accounting fails; it
  is no longer rewritten as an ordinary rejection.
- Signed browser sessions retain verified human account provenance for AgFields,
  Omni and Batch without persisting cookies, session IDs, roles or raw claims in
  evidence receipts.
- Private archive storage modes, digest sidecar and sensitive-path denial are
  useful containment controls when the archive is classified private.
- Production binary admission defaults off in both participating services. The
  shared UI/server flag provides an immediate binary-only disable while direct
  GeoJSON remains available.

## Control decision and production boundary

Revision `4654150c9` is not accepted for M5 completion or receiver activation.
The correct decision is **reject**, scope-reduced to local remediation and
validation. Keep the production filesystem ID unset and binary admission false;
do not use successful jobs, receipt existence or canonical-file existence as
substitutes for authoritative reload and downstream artifact readback.

This rejection does not revoke the isolated M2 image qualification and does not
claim a production failure. Remote integration, image publication and production
deployment were not performed and remain outside this execution authorization.
After the High/Medium findings close on one new committed revision, repeat this
operations review against that exact revision and final image. Only then may a
separately authorized production rollout collect real identities, mounts, Redis,
Caddy/network, canary, observation and rollback evidence.
