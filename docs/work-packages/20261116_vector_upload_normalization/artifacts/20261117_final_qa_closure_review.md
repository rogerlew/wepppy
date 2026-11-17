# Final QA closure review

Date: 2026-11-17
Reviewer: independent `qa_reviewer` (`final_qa_review`)
Reviewed revision: `061253c55a2a0e1cc8952143ebdf47cc40357a18`
Exact local image: `wepppy/shape-converter:vector-upload-m2-final4`
Exact image ID:
`sha256:ec801ab0c90e595dcc1a4f58b9be52398b8073a75a72591c34149b543a73ce03`
Verdict: **REJECT M5 acceptance. Two High and four Medium QA findings remain.**

## Review boundary

This review supersedes the QA re-review of `4654150c9`. It independently
examines the exact clean revision above against the active ExecPlan, canonical
normalization contract, prior QA findings, retained final4 qualification and
M3-M5 validation claims. It focuses on exact-image format/workflow equivalence,
real receiving validators and workflow authorities, failed replacement, crash
recovery, fresh reload, downstream artifacts, readiness, shared Redis recovery,
project/private-archive deletion, archive authorization and provenance evidence.

The worktree was clean at the reviewed revision before this artifact was added.
No runtime code, Redis state, image, registry or deployment was changed by this
review. Image publication, remote-host integration and production deployment
remain separate, unauthorized gates rather than local test failures.
Concurrent uncommitted edits to the normalizer and its Redis tests appeared
after the review was pinned. They receive no credit here; every runtime claim is
against the committed blob at `061253c55`.

## Prior-finding disposition

| Prior QA finding | Closure disposition at `061253c55` |
| --- | --- |
| `VUN-QA-RR-01`, late Roads/AgFields failure | **Narrowed.** Both real controllers now retain byte/state backups through a live publication callback, and focused tests prove rollback plus detached reload when that callback raises. Batch still discards its backup before receipt/readback completion, and abrupt termination remains unresolved for every workflow. See `VUN-QA-CLOSE-01` and `02`. |
| `VUN-QA-RR-02`, generic exact-image proof | **Partially narrowed, still Medium.** Five new tests cross the actual Flask/FastAPI routes with final4, but replace the authoritative Roads, AgFields, Omni and Batch controller/build objects and stop at canonical GeoJSON. See `VUN-QA-CLOSE-03`. |
| `VUN-QA-RR-03`, expiring reconciliation fence | **Closed for the prior lock-expiry defect.** Reconciliation renews and checks its global owner token before mutations/final replacement, uses an owner-checked Redis transaction, blocks symlink evidence and has a real-Redis lock-loss test. It does not fence an active workflow's project scope; see `VUN-QA-CLOSE-02`. Deletion/rebuild composition has a separate Medium finding. |
| `VUN-QA-RR-04`, private archive path/integrity | **Closed for the prior defect.** The receipt uses project-root-relative `archives/private/...`; route resolution verifies sidecar schema, size and SHA-256; owner/root restore, authenticated non-owner denial, private delete and real-Redis worker restore are covered. |
| `VUN-QA-RR-05`, readiness mismatch/provenance | **Closed locally.** The preflight accepts the actual `status=ok`, `check=ready` response and compares expected parser binary, Cargo lock and source revision. Focused success/mismatch/malformed tests pass. Registry digest and production parity remain later rollout gates. |
| `VUN-QA-RR-06`, session provenance | **Open, Medium.** No successor change drives an authenticated session upload through the routes and reads back receipt, principal accounting and the bounded security event. See `VUN-QA-CLOSE-05`. |
| `VUN-QA-RR-07`, retained evidence consistency | **Partially narrowed, still Medium.** Tracker date/image state and numeric rollout thresholds improved, but the exact revision, commands, fixture hashes, skip identities and downstream proof are still absent or overstated. See `VUN-QA-CLOSE-06`. |

## Open High findings

### VUN-QA-CLOSE-01 — High — Batch can report failure after irreversibly selecting the replacement

The Batch callback creates a backup, replaces the canonical resource, registers
the new collection and then unconditionally deletes the backup when the callback
returns (`upload_batch_runner_routes.py:264-295`). Only afterward does ordinary
`PreparedVectorUpload.publish()` hash the canonical file, persist the accepted
receipt and finalize Redis accounting (`vector_upload_normalization.py:1189-1229`).
An error in canonical readback or receipt persistence therefore reaches the
route's error response after the prior resource backup is gone and the new
Batch state is registered. A Redis commit error is similarly surfaced after the
attempt has become accepted/pending. This violates the failed-replacement gate:
the client receives failure while the replacement remains authoritative.

The existing Batch failure test injects `register_geojson()` failure before the
callback declares success, so it exercises only the early rollback branch. It
uses `DummyBatchRunner` and `DummyCollection`, does not inject post-callback
receipt/readback failure, and does not detach/reload real Batch state or parse a
generated per-watershed input.

**Required closure:** use a transactional publication callback for Batch and
retain both canonical bytes and authoritative Batch metadata/state until receipt
publication has committed (with accounting-pending treated consistently). Inject
failures in canonical readback, receipt fsync/replace and Redis finalization.
After every failed response, load a fresh real `BatchRunner`, prove the prior
resource remains selected, and semantically parse the prior generated
`dem/target_watershed.geojson` or equivalent run input.

### VUN-QA-CLOSE-02 — High — Process interruption still leaves prepared receipts and authoritative replacement state unresolved

The new Roads and AgFields callback design handles Python exceptions while the
process remains alive, but not termination between durable workflow mutation and
receipt publication. Roads replaces the canonical file and persists NoDb state
before calling `publication_commit()` (`roads.py:1198-1227`); AgFields replaces
GeoJSON/Parquet and persists state before its callback
(`ag_fields.py:316-332`). Omni builds real/dry-run state first and only then calls
ordinary `prepared.publish()` with a no-op mutation
(`omni_routes.py:822-834`). Batch has the same post-mutation receipt interval.

After a process dies in those intervals, the backup cleanup/exception handler
does not run. Reconciliation changes every nonterminal receipt to `incomplete`
without consulting Roads, AgFields, Omni or Batch authoritative state
(`vector_upload_normalization.py:457-492` in the committed blob). It neither
restores the prior state nor proves and adopts the replacement. It also decides
staleness from reservation age under only the global reconciliation lock; it
does not acquire or test the workflow's project-scope lease before mutating the
receipt/accounting. A long but live operation can therefore be terminalized by
recovery. A quarantined receipt is not evidence that the old resource remains
selected. The retained real-Redis tests exercise unbound recovery, accepted
receipt accounting and global-lock theft; they do not fence a live project
scope, interrupt a real workflow after durable mutation or prove fresh
reload/downstream selection.

**Required closure:** add workflow-specific, read-only recovery authority or an
equivalent transaction protocol that resolves this crash window under the same
scope fence. Inject process interruption immediately before/during receipt
publication for Roads, AgFields, Omni run, Omni dry-run and Batch. Reconcile,
load fresh real controllers, and parse the selected downstream artifacts. Mark
`accepted_recovered` only when canonical hash, persisted state, reload and
downstream authority agree; otherwise restore or explicitly block use of the
replacement rather than merely relabeling the receipt.

## Open Medium findings

### VUN-QA-CLOSE-03 — Medium — Final4 tests cross route adapters but not real workflow/reload/downstream boundaries

The five final4 route selections are useful transport and receiving-validator
coverage, but not the acceptance evidence claimed:

- Roads uses `RoadsStub`; its setter copies JSON and does not run the real
  controller or segment builder (`test_roads_bp.py:128-167,474-497`).
- AgFields uses `DummyAgFields`; it writes canonical JSON but never writes or
  parses the real rotation-schedule Parquet
  (`test_rq_engine_ag_fields_routes.py:55-70,359-383`).
- Omni run and dry-run use `DummyOmni`, stub the queue/preparation boundary and
  make both build methods no-ops/dict returns; no `build_report.ndjson` is read
  (`test_rq_engine_omni_routes.py:1292-1356`).
- Batch substitutes `DummyBatchRunner` and `DummyCollection`; it does not cover
  real registration, reload or per-watershed generation
  (`test_rq_engine_upload_batch_runner_routes.py:183-222`).

Each test loops four semantically identical fixtures through one shared project
and compares only the first canonical feature. It does not read the attempt's
source hash to prove each iteration replaced state, so stale canonical output
could satisfy the equality check. None loads a detached controller. The M3-M5
artifact's statement that all five boundaries parsed canonical properties and
Shapely geometry is also imprecise: Roads uses direct dictionary equality.

**Required closure:** run all four suffixes through the exact image and actual
workflow authorities with a fresh project or unique per-format marker, verify
source/receipt hashes, detach/reload, and semantically parse Roads segments,
AgFields rotation/field artifacts, Omni run and dry-run build reports, and Batch
per-watershed inputs. Retain feature counts, complete property equality and
Shapely geometry equality, not only the first feature of a shared canonical
file.

### VUN-QA-CLOSE-04 — Medium — Destructive evidence deletion is coupled to a global rebuild that fails under unrelated active uploads

Whole-project and private-archive deletion remove their filesystem target before
calling `reconcile_retention(..., rebuild_ledger=True, committed_only=True)`
(`project_rq_delete.py:127-181`; `fork_archive_routes.py:1797-1813`). The rebuild
refuses final accounting replacement while *any* reservation remains
(`vector_upload_normalization.py:553-562` in the committed blob).
`committed_only=True` skips unrelated
noncommitted reservations rather than resolving them, so one valid upload in any
other project makes the post-removal rebuild fail. Private archive deletion also
releases its run scope before the rebuild, leaving an additional same-run
admission gap.

The target is already gone when this happens. A project-deletion retry sees a
missing run directory, skips reconciliation and can delete the database record
while the removed project's bytes remain charged. A private-archive retry sees
404. Both paths can therefore leave conservative but persistent filesystem and
principal quota leakage. Current tests replace reconciliation with a mock and
assert only call ordering; they do not use real Redis, an unrelated in-flight
reservation, failure after removal or idempotent retry.

**Required closure:** make whole-attempt/private-bundle/project removal update
the exact charged bytes atomically after durable deletion, or hold a transaction
that cannot be invalidated by unrelated valid uploads. Add real-Redis tests with
concurrent cross-project reservations and same-run admission, failures before
and after durable removal, and idempotent retry. Prove the requested object is
gone, unrelated uploads remain valid, and global/principal totals equal receipt
readback after every outcome.

### VUN-QA-CLOSE-05 — Medium — Browser-session actor provenance remains helper-only evidence

The retained session tests call `_retention_actor()` with synthetic claim
dictionaries. They do not submit a signed authenticated session through the
AgFields, Omni run/dry-run or Batch routes, then read the attempt receipt, Redis
principal bucket and `vector_upload_security_event_v1`. Thus they do not prove
the user's human account ID survives the real authentication boundary or that
session identifiers, roles and raw claims stay absent. No code in the successor
commit closes this prior QA finding.

**Required closure:** add owner-session route tests for AgFields, Omni run and
dry-run and Batch, plus authenticated public/non-owner negatives where relevant.
Read back receipt actor, principal accounting and the bounded security event;
assert the positive user ID and source SHA-256 are present while session ID,
token, roles, email/raw claims and client IP are absent.

### VUN-QA-CLOSE-06 — Medium — Retained evidence is not reproducible and overstates the completed boundary

`20261117_m3_m5_validation.md` identifies only ancestor `9ac7cb8f6` plus an
unnamed successor, not exact revision `061253c55`. It records aggregate
`480 passed, 5 skipped`, but no exact commands, skip identities, per-selection
stdout or fixture hashes. The supplied shape-converter result of `315 passed`
is not recorded in the final4 qualification or M3-M5 artifact. The artifact also
claims detached failed-replacement and five-boundary geometry/property proof
beyond the actual Batch/Omni/dummy-controller evidence above. The tracker still
says Batch implementation/regression evidence is pending in its current
"Resolved Contract Decisions" while marking M3-M4 complete.

This conflicts with the ExecPlan requirement to retain commands, exact revision,
image digest, fixture hashes, results, skips and parsed downstream readback.
Aggregate green totals cannot close the absent artifact acceptance evidence.

**Required closure:** bind all retained results to the exact clean successor and
image ID; record commands, environment, fixture byte hashes, every skip and the
parsed per-workflow results. Correct the M3-M5 and tracker claims to distinguish
route-adapter/canonical coverage from real controller reload/downstream proof.
Record the `315 passed` shape suite with its exact command and revision, then
update living Progress/Outcomes only after all High/Medium successor reviews
close.

## Accepted local controls and residual Low debt

- Final4 retains an exact local image ID, parser binary/Cargo/source provenance,
  SPDX and Grype artifacts. This review does not reopen the M2 image decision.
- Roads and AgFields now have materially stronger live-exception rollback tests
  using the real controllers and detached reload.
- Reconciliation lock renewal/owner-token loss, initialized-ledger fail-closed
  behavior and eight-slot Redis recovery are useful local controls. Project-scope
  exclusion is not present in the reviewed commit.
- Private archive creation/restore now has mode, hash, canonical-path and
  owner/root route coverage. Anonymous denial remains indirectly dependent on
  the established JWT requirement; an explicit route negative would be useful
  Low test debt.
- Exact-format tests reuse the same `.parquet` bytes for `.parquet` and
  `.geoparquet`, which is appropriate suffix-alias coverage, but their long
  in-test loops and ad hoc semantic dictionaries are fragile. A small shared
  assertion helper plus per-format test IDs would improve failure localization
  after the real-workflow evidence exists.
- Readiness malformed JSON currently escapes as `ValueError` rather than a
  concise operator-facing exit. It fails closed, so this is Low usability debt.

## Validation performed

- Verified clean source identity
  `061253c55a2a0e1cc8952143ebdf47cc40357a18` before adding this review artifact.
- Reviewed the exact commit diff, all new final4 route selections, real
  controller rollback tests, normalizer/reconciliation code, project/private
  deletion integration, readiness tool/tests, Compose wiring, canonical
  contract, active ExecPlan, tracker and retained qualification/validation
  artifacts.
- Supplemental host run of the readiness tests: **6 passed**.
- The two selected real-controller rollback tests could not run in the host
  sandbox because NoDb attempted a forbidden localhost Redis socket; they are
  not counted as failures. The retained candidate-container application result
  is **480 passed, 5 skipped**.
- The supplied exact shape-converter suite result is **315 passed**; it was not
  independently rerun because the exact image/network harness was not available
  to this read-only review.
- RQ dependency graph check: **passed** (`RQ dependency graph artifacts are up
  to date`).
- `git diff --check` across the full work package reports pre-existing Markdown
  trailing whitespace in historical artifacts. This review adds none and does
  not treat that historical formatting debt as a runtime finding.

## QA disposition

Do not mark M5 complete and do not activate receiver-side binary admission on
revision `061253c55`. The final4 image remains the qualified local M2 candidate,
but exact-image workflow acceptance, crash/failed-replacement safety, deletion
accounting and retained evidence are not closed. Re-review one clean committed
successor after every High and Medium above is resolved with real controller,
fresh reload and parsed downstream artifact evidence. Publication, remote-host
integration and production deployment remain separate operator-authorized work.
