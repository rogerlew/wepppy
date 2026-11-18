# Final QA successor re-review

Date: 2026-11-17  
Reviewer: independent `qa_reviewer` (`final_qa_review`)  
Reviewed revision: `4654150c96183eb7913f8f086526c88ad6ee3ce9`  
Exact local image named by the package:
`wepppy/shape-converter:vector-upload-m2-final3`  
Exact image ID:
`sha256:ed4d93692add1f7cd1527ed6948353e584a213865ebcc3006b1adf84f5c62386`  
Verdict: **HOLD M5 acceptance. One High and six Medium QA findings remain.**

## Review boundary

This review independently re-examined the successor commit against the active
ExecPlan, the canonical normalization contract, the prior final QA findings and
the retained M3-M5 validation claims. It focused on four-format/five-profile
evidence, failed replacement and reload behavior, downstream artifact readback,
Redis recovery, private archive/restore behavior, session provenance, activation
preflight, and documentation consistency.

The shared task worktree became dirty during the review as other agents edited
the same runtime files. To avoid crediting later uncommitted changes, static
review and supplemental tests used a clean `git archive` of the exact revision
above. This artifact does not review those later edits and does not modify
runtime code. Publication, deployment and production-host integration remain
outside this review.

## Prior finding disposition

| Prior finding | Successor disposition |
| --- | --- |
| VUN-QA-01 sensitive path escape/Culvert NameError | **Immediate defect closed.** The misplaced Batch check is removed and resolved-path sensitive checks cover the direct download/Files API path. Private-archive integrity/recovery has a separate Medium finding below. |
| VUN-QA-02 Redis crash wedge | **Narrowed, not fully closed.** Reservation metadata is durable and a reconciliation/rebuild command exists, but the reconciliation owner lock can expire during its own bounded scan and the real-Redis test does not exercise restart, duplicate recovery, wrong-owner behavior or receipt-state crashes. |
| VUN-QA-03 failed replacement/reload | **Open, High.** Late failure after durable mutation still leaves Roads or AgFields replacements selected, and fresh-reload/downstream fault evidence is absent. |
| VUN-QA-04 all-format workflow/downstream proof | **Open, Medium.** The exact-image test labels five profiles but calls only the shared normalizer and a generic copy callback. |
| VUN-QA-05 converter error translation | **Runtime mapping closed; test closure incomplete.** The receiver now bounds the response, maps the admitted converter codes and turns malformed successful responses into 503. The requested receiver-envelope matrix is still absent and is retained as Low test debt. |
| VUN-QA-06 session provenance | **Runtime path plausibly closed; acceptance evidence incomplete.** Session human IDs are preserved, but tests stop at helper functions rather than real session-token uploads and receipt/ledger/event readback. |
| VUN-QA-07 M5 activation/docs | **Open, Medium.** The new preflight rejects the exact service's successful readiness body, and the retained validation/tracker overstate or ambiguously identify evidence. |
| VUN-QA-08 test seams | **Still present.** The new exact-image and workflow tests continue to substitute the ledger, lease or workflow controller at the boundaries whose behavior is being claimed. |

## Findings

### VUN-QA-RR-01 — High — Late workflow failures can still replace accepted Roads and AgFields resources

The successor adds useful byte/state backups, but their scope ends before all
fallible work completes:

- Roads replaces `roads.uploaded.geojson`, commits controller state and deletes
  the backup at `wepppy/nodb/mods/roads/roads.py:1178-1199`. It then writes the
  completion log at lines 1201-1215. An `OSError` from that log is returned by
  the route as a failed upload after the replacement and durable state are
  already selected; the old backup is gone.
- AgFields replaces GeoJSON and rotation-schedule Parquet and commits controller
  state at `wepppy/nodb/mods/ag_fields/ag_fields.py:301-323`, deletes both
  backups at lines 324-327, and only then requests catalog refresh at lines
  329-330. A refresh failure likewise escapes after the new bytes/state are
  authoritative.

`PreparedVectorUpload.publish()` records these post-mutation cases as uncertain;
it cannot restore workflow-specific state. The added Batch test injects failure
before `register_geojson()` mutates state
(`tests/microservices/test_rq_engine_upload_batch_runner_routes.py:320-364`),
and the Omni test uses a dummy controller and verifies only staged-file removal
(`tests/microservices/test_rq_engine_omni_routes.py:1291-1339`). No test injects
the Roads log or AgFields catalog failure, reloads a fresh real controller, and
parses the prior downstream artifact.

**Required closure:** keep backups/lifecycle snapshots until every operation
that can make the request fail is complete, or explicitly make post-commit
operations non-fatal with truthful observability. Inject failures at file
replacement, state persistence, log/catalog refresh, receipt publication and
Redis finalization for all workflows. After each failed request, load a fresh
controller/process and prove prior authoritative hashes, state and downstream
artifacts remain selected. Do not treat an `incomplete` receipt alone as failed-
replacement safety.

### VUN-QA-RR-02 — Medium — The claimed four-format/five-profile exact-image proof is not a workflow-boundary test

`tests/microservices/test_vector_upload_exact_converter.py:48-120` parameterizes
five workflow *strings*, but every case directly calls
`prepare_vector_upload()` with the generic geometry validator (lines 85-100)
and publishes by `shutil.copy2()` to `accepted.geojson` (lines 101-106). It does
not invoke the Roads browser route, AgFields API, Omni run/dry-run API, or Batch
API. It uses fake ledger and lease implementations (lines 22-45), never reloads
authoritative NoDb state, and never creates or parses any required downstream
artifact. `.geoparquet` also reuses the same `.parquet` fixture bytes (lines
74-80), which is useful suffix coverage but not an additional workflow proof.

Consequently the statements in
`artifacts/20261117_m3_m5_validation.md:24-28` and
`tracker.md:228-230` establish shared normalizer/converter equivalence only.
They do not meet the contract's actual-boundary, reload and parsed-artifact gate.

**Required closure:** drive all four formats through each actual receiver using
the exact image, then instantiate fresh authoritative controllers and
semantically parse/compare Roads segments, AgFields rotation/field artifacts,
Omni `build_report.ndjson` for run and dry-run, and Batch
`dem/target_watershed.geojson`. Retain exact command, revision, image ID, fixture
hashes and parsed results. Rename the present test/evidence if it remains as the
shared-normalizer integration layer.

### VUN-QA-RR-03 — Medium — Reconciliation loses exclusive ownership after 300 seconds

`reconcile_retention()` obtains the filesystem-wide lock with fixed `EX 300` at
`wepppy/microservices/vector_upload_normalization.py:381` and never renews or
rechecks it. The protected work can scan and hash up to 10,000 reservations and
then walk/hash up to 10,000 receipt trees (lines 383-515). Rebuild finally
deletes and recreates global/principal totals at lines 525-546. If that work
exceeds five minutes, normal reservations can resume while the rebuild is still
running; a later rebuild transaction can erase or undercount those admissions.

The single real-Redis test proves eight pre-write releases and one simple
rebuild (`tests/microservices/test_vector_upload_normalization.py:261-346`), but
not lock renewal/loss, Redis restart, wrong-owner rejection, idempotent duplicate
recovery, or crashes at bound receipt states.

**Required closure:** use a renewable owner-checked lock or a bounded operation
whose lease cannot expire, assert ownership immediately before every mutation,
and abort safely on loss. Add disposable-Redis tests for lock expiry during
scan/rebuild, concurrent admission, restart/persistence, duplicate reconciliation,
wrong owner and receiving/source-stored/prepared/accepted recovery. Prove totals
and evidence bytes after every case.

### VUN-QA-RR-04 — Medium — Private archive recovery records the wrong canonical path and restore ignores the binding sidecar

Private archive creation writes the archive beneath `archives/private/...`, but
its synthetic receipt records `canonical_path: archive_name` at
`wepppy/rq/project_rq_archive.py:445-460`. Reconciliation resolves canonical
paths relative to the project root
(`wepppy/microservices/vector_upload_normalization.py:437-448`), so a crash
between archive receipt publication and reservation commit searches for
`<run>/private/...` rather than `<run>/archives/private/...` and classifies a
valid archive as `incomplete`.

The mode-0600 sidecar binds the archive SHA-256 at archive creation (lines
436-444), but `restore_archive_rq()` opens the archive directly at lines 527-547
without reading or validating that sidecar. The archive test verifies the
sidecar before restoring the unchanged archive; it has no mismatch/tamper or
reconciliation case.

**Required closure:** record a project-root-relative canonical path that includes
`archives/`; verify the private-archive sidecar schema, archive identity, size
and SHA-256 before restore cleanup; and add crash/reconcile and tampered/missing
sidecar tests. Prove anonymous/non-owner denial as well as owner restore and
terminal ledger readback.

### VUN-QA-RR-05 — Medium — The activation preflight rejects the exact image and does not verify exact provenance

`tools/check_vector_upload_readiness.py:52` requires readiness
`status == "ready"`. The exact shape-converter returns `status: "ok"` on a
successful readiness response at
`wepppy/microservices/shape_converter/app.py:397-410`. Binary-enabled preflight
therefore always exits with failure against the qualified image. In addition,
the check accepts only the generic string `provenance: binary_binding_verified`;
it does not compare the expected image ID, parser binary SHA-256, Cargo.lock
SHA-256 or source revision. No test covers this tool.

This contradicts the claim in
`artifacts/20261117_m3_m5_validation.md:50-53` that the tool verifies exact
converter readiness/provenance.

**Required closure:** consume the actual readiness contract (`status=ok`,
`check=ready`, both parser fields and provenance marker), bind the preflight to
the expected immutable image/parser identities available to the operator, and
add success plus wrong-image/parser/missing-parser tests using the exact response
shape. Correct the rollout text to distinguish service-owned binary validation
from externally pinned image identity.

### VUN-QA-RR-06 — Medium — Session-human provenance is not proved through real request receipts or accounting

The runtime now retains a verified session human ID, which is the right design.
The new tests only call actor helpers with synthetic dictionaries:

- AgFields: `test_rq_engine_ag_fields_routes.py:1427-1436`;
- Omni: `test_rq_engine_omni_routes.py:2113-2119`; and
- Batch: `test_rq_engine_upload_batch_runner_routes.py:652-658`.

They do not send a signed session token through authentication and authorization,
perform an upload, or read the resulting receipt, Redis principal bucket and
bounded security event. They therefore do not prove the prior provenance bug is
closed at the user-visible boundary or that session IDs/roles remain absent.

**Required closure:** add actual owner-session route tests for AgFields, Omni run
and dry-run, and Batch, plus anonymous/public-session negatives. Read back the
receipt actor, principal ledger bucket and security event, asserting that only
the positive canonical user ID is retained and no session ID, token, role or raw
claim leaks.

### VUN-QA-RR-07 — Medium — Retained M5 evidence and tracker state are internally inconsistent

The M3-M5 validation artifact identifies the application only as
`9ac7cb8f6 plus the successor commit named by the final review artifacts`
(`artifacts/20261117_m3_m5_validation.md:5-6`), not the exact tested revision.
It claims all four workflows restore prior durable state (lines 32-34) despite
the late-failure paths above, and claims exact five-profile acceptance despite
the generic shared-normalizer test. The tracker is dated 2026-11-16 while its
closure section is dated 2026-11-17 (`tracker.md:6,221`), and simultaneously
marks M3-M4 complete while saying Batch implementation/regression evidence is
pending (`tracker.md:29-30,52-53`).

**Required closure:** bind every retained command/result to one exact clean
application revision and exact image ID, describe the exact boundary each test
exercised, remove claims unsupported by parsed artifact readback, and reconcile
the tracker/ExecPlan living sections only after successor review findings close.

## Low test-quality debt

### VUN-QA-RR-08 — Low — Converter translation and readiness/recovery tools lack focused contract tests

The expanded converter code map and malformed-response translation appear
correct by inspection, closing the prior runtime defect. Receiver tests do not
exercise the admitted 400/408/413/503 code matrix or malformed/oversize 200
responses through each response envelope. Neither new operator tool has focused
CLI tests. This leaves small but important mappings and exit behavior coupled to
large route suites and manual evidence.

**Follow-up:** add a compact table-driven `_converter_payload()` contract suite
and isolated CLI tests for readiness and reconciliation. Keep workflow route
tests for envelope preservation rather than duplicating every transport case.

## Validation performed

- Verified the reviewed tree identity as
  `4654150c96183eb7913f8f086526c88ad6ee3ce9` and used an isolated archive after
  concurrent work dirtied the task worktree.
- Supplemental host-venv normalizer run from that archive, excluding the
  environment-dependent real-Redis test: **10 passed, 1 deselected**.
- A selected route bundle started and passed one test, then reproduced the
  known local `TestClient`/lifespan stall for more than 40 seconds and was
  interrupted. It is not counted green.
- The exact-image integration module was inspected rather than rerun because its
  converter network/fixture environment was not available in the isolated
  archive. Its retained `5 passed` result is accepted only as shared-normalizer
  format equivalence, not as five real workflow boundaries.
- Static readback covered all changed runtime/tests, the canonical contract,
  active ExecPlan, tracker, prior QA artifact, M3-M5 validation artifact, Compose
  wiring and the exact shape-converter readiness response.

## QA disposition

Do not mark M5 complete and do not treat the local rollout package as ready for
activation on revision `4654150c9`. The exact parser image remains the qualified
local M2 candidate, and publication/deployment remain separately blocked and
unauthorized. Re-review one clean committed successor after every High and
Medium item above is closed with actual-boundary, fresh-reload and parsed-
artifact evidence.
