# Security Review - Batch Daymet Multiple NoDb Contention

## Metadata

- **Reviewer**: Independent `security_reviewer` agent.
- **Date**: 2026-09-30.
- **Package**: `docs/work-packages/20260930_batch_daymet_multiple_nodb_contention/`.
- **Revision context**: evolving working-tree changes over
  `bbace6023575d29ca00a26f1ad2a7776e957fc8a`, branch `master`.
- **Reviewed production diff SHA-256**:
  `287e54adf19f2840fdf25724638f99d5c305e1eb89ad457bf2c0fd8a5960c730`.
  Computed from `git diff --` for `wepppy/nodb/_derived_build.py`,
  `wepppy/nodb/batch_runner.py` and `wepppy/nodb/core/` files `climate.py`,
  `climate_build_helpers.py`, `climate_build_router.py`,
  `climate_mode_build_services.py`, `climate_observed_build.py`.
  Subsequent source changes require review of their delta.
- **Scope reviewed**: Climate facade, observed collector, mode/router wiring,
  PRISM helper, shared `_derived_build` finalizer/publication; batch startup,
  base resynchronization and NoDb lock-clear behavior.
- **Related artifacts**: `2026-09-30_writer_attribution.md` and
  `2026-09-30_correctness_review.md` in this directory. Correctness/QA and broad
  validation are separate required gates; this sign-off covers source security
  and the independent forest checks below.

## Security Triage Decision

- **Security impact level**: `high`.
- **Dedicated security review required**: `yes`.
- **Rationale**: shared-worker ownership, run-tree publication and failed project
  records are affected. This introduces no new public route or privilege.
- **Threat assumptions**: authorized jobs can be duplicated; several workers
  share run files; run files can change during collection; trusted numerical
  collectors can fail after writing useful work products. Existing project
  authorization remains the access boundary.
- **Valid states to preserve**: absent/empty ordinary climate directory,
  populated directory, supported string-year legacy controllers and managed
  NoDir projections; malformed/relevant-edit, unrelated-edit, duplicate-job,
  collection-failure and publication-failure states require distinct outcomes.

The exact Kubernetes incident writer has **not** been attributed. The source
defects below do not assert that attribution or establish cluster lock identity.

## Findings

| ID | Severity | Surface | Description / exploit path | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Medium | Failed project artifacts | Initially hidden auto-cleaned staging destroyed failed work products, including candidates consumed by publication then removed during rollback. Daymet/observed PRISM now retain visible originals, publish redundant copies and write failed status; recovery backups use visible `derived-backup-*`. | `climate_observed_build.py::_publish_retained_attempt`, `::run_observed_daymet_build`, `::run_prism_revision_build`; `_derived_build.py::publish_files`. Independent failure, working/failed archive/browser and unknown-commit recovery tests pass. Canonical inventory: `docs/schemas/climate-parquet-lineage-contract.md`, Daymet acquisition source preservation. | Completed locally: candidate/recovery bytes, status, ordinary paths and canonical inventory verified. Live authorization/service-identity evidence remains a separate prerelease requirement below. | Resolved in reviewed candidate. |
| SEC-02 | High | Worker ownership and durable integrity | Initially duplicate startup cleared active controller tokens and resync truncated the whole leaf controller without ownership. Shared batch-root ownership, fresh atomic climate resync and exclusion of climate tokens from automatic clearing address those source paths. | `batch_runner.py::_clear_batch_leaf_nodb_state`, `::_run_with_climate_leaf_lock`, `::run_batch_hillslopes`, `::_resync_base_project_attributes_owned`; five independent direct ownership/reset/nonreplay/token/resync test instances pass. | Completed locally. Retain exact cluster writer/lock identity as a separate acceptance gate, without treating local injected writers as incident attribution. | Resolved in reviewed candidate. |

Risk acceptance requires reviewer recommendation plus explicit package-owner
acknowledgment. No acceptance is recorded here.

## Verdict

- **Gate status**: `pass` for local source security and automated forest review.
- **Unresolved source findings**: High: 0; Medium: 0; Low: 0.
- **Recommendation**: accept source remediation; withhold release/deployment and
  package closeout until live authorization/service-identity, final
  correctness/QA/broad checks and bounded cluster evidence pass. This is not a
  cluster execution approval or incident-resolution claim.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [x] Ordinary and managed climate-directory containment has targeted coverage.
- [x] Unrelated same-size durable edits survive both newly routed stages.
- [ ] Final correctness/QA state matrix and generated-artifact parity reviewed.
- [x] Real Daymet and observed PRISM failure tests retain visible candidates.
- [x] Working/failed attempt bytes and status survive canonical archive/restore;
  established browse listing/download routes expose those records in TestClient.
- [x] Canonical inventory and visible recovery-backup archive/browse coverage.
- [ ] Live service identity/auth and final correctness/QA/environment gates.

The full `Climate.build` router historically clears previous output; a staged
successful replacement may preserve that result. Direct Daymet calls historically
retain unrelated sidecars. The current `replace_existing` option separates those
behaviors; its final tests/docs must match. No additional security control may
reject supported empty/legacy/projected states merely for convenience.

### 1) Auth, Session, and Authorization

No route, JWT/session, CSRF, or authorization change is present. Existing
run-scoped authorization must also govern retained attempts.

### 2) Secrets and Credential Handling

No secret, token, new secret mount, or credential logging was introduced in the
reviewed diff. Retained records must not contain credentials or controller dumps.

### 3) Input Validation and Output Safety

Existing observed-input snapshots and final relevant-input comparisons are
reused. Explicit malformed/superseded failures remain. No new shell interpolation
or deserialization boundary was introduced.

### 4) File System and Run-Tree Boundaries

`require_output_directory` enforces resolved run containment. The observed
collector rejects unmanaged climate symlinks; the router preserves their target
contents while removing the link. `publish_files` rejects nonregular/symlink
artifacts, uses flat names, checks owning lock tokens and protects rollback from
overwriting a successor. Existing permissions are retained for replaced files.
Attempt-directory browse/read permissions under actual service identities remain
an integration evidence requirement, not a proved defect.

### 5) Queue, Worker, and Subprocess Surfaces

No enqueue site, dependency edge, retry classification or subprocess composition
changed. No RQ graph gate is triggered by the reviewed diff. The new shared
lexical/effective climate guard covers batch startup and full leaf execution;
acquisition retry cannot replay a failed callback. Startup enumerates active
lock state and clears only exact non-climate controller scopes, preserving
climate tokens, including those belonging to standalone/controller-only writers.
Direct production-method tests verify that behavior and same-leaf exclusion
before/after effective-root replacement. Cross-node identity is still unproved.

### 6) Agentic Tooling and MCP Surfaces

No tool/MCP privilege or external publication change. This review performed no
live-run mutation, deployment or batch replay.

### 7) Network and External Integrations

Existing Daymet/PRISM numerical collectors and endpoints are reused. No new
service, outbound destination, dependency or retry loop was added.

### 8) CI/CD and Supply Chain

No CI permissions, image-publication pipeline or dependency change. The bounded
cluster procedure still needs exact fixture/write-set/rollback/stop declarations
before its own execution gate.

### 9) Data Integrity, Locking, and Concurrency

`finalize` locks, hydrates current disk state, checks controller identity, applies
explicit derived fields and dumps once. Relevant-input rejection and stale-write
protection remain; artifacts roll back on identifiable precommit failure.
Postcommit/unknown commit outcomes retain recovery evidence and report failure.
Climate resynchronization now rehydrates under the controller lock and applies
named values through normal atomic persistence. Its pre-lock comparison is
advisory; the fresh mutation base is reestablished under ownership. Automatic
startup now preserves climate tokens held by another controller owner; its
targeted test proves that owner can dump the unrelated edit afterwards.

### 10) Logging, Monitoring, and Incident Readiness

No new broad exception swallowing appeared. Daymet/observed PRISM failures log
the retained run-scoped path and write bounded working/failed status with kind,
observed years and UTC update time, not controller payloads. Failure to update
status is logged while the original build exception remains explicit. No
automatic replay or repair is added. Cluster ownership evidence is pending.

## Validation Evidence

Independent command:

```text
wctl run-pytest tests/nodb/test_batch_climate_rap_contention.py \
  -k 'old_publication or containment or daymet_multiple' -vv --tb=short
```

Result: **5 passed**, 35 deselected, 12.77 seconds. Tests exercise the actual
serializer/filesystem publication boundary, with injected collection/writer
seams. They prove successor-safe rollback, managed/unmanaged containment and
Daymet/PRISM preservation of unrelated durable edits. They do not prove native
scientific output parity, duplicate startup exclusion, archive retention,
production identities or cluster writer attribution.

An independent `wctl run-python -c` probe called the actual Daymet collector with
an injected collection failure after three real files were written. Current
behavior retains visible `daymet-build-*/wepp.cli`, `ws.prn` and `diagnostic.txt`
and preserves `previous.cli`: retained flags were `[True, True, True]`. This
establishes Daymet's collection-failure retention only; archive/browser/status
and newly routed PRISM coverage remain pending. The probe used an isolated
temporary run and ordinary production staging/cleanup, with numerical acquisition
and station lookup injected.

Second independent command:

```text
wctl run-pytest tests/nodb/test_batch_climate_rap_contention.py \
  -k 'daymet_build_failure or observed_prism_retains' -vv --tb=short
```

Result: **6 passed**, 42 deselected, 13.08 seconds. Daymet collection,
relevant-edit, malformed-input and real precommit serializer failure; observed
PRISM worker and precommit serializer failure retain visible candidate bytes and
failed status while preserving accepted outputs/controller state. Both original
attempts and the real publisher/rollback remain unmocked.

Third independent command:

```text
wctl run-pytest tests/nodb/test_batch_climate_rap_contention.py \
  -k 'batch_leaf_guard or batch_startup_preserves or batch_climate_resync or observed_attempt_browser_archive_restore' \
  -vv --tb=short
```

Result: **9 passed**, 49 deselected, 15.80 seconds. Five test instances verify
root-reset duplicate exclusion, callback nonreplay, standalone token preservation
and fresh resync preservation of an injected unrelated edit. Four verify actual
working/failed Daymet/PRISM writer records through canonical ZIP/archive restore
and established browse listing, raw status and download routes. The browse
fixture injects a public `AuthContext`; these are real route/filesystem tests,
not live authorization or worker/browser UID/group/mount parity evidence.

Total independent targeted checks: **20 passed** across the three runs, without
claiming exhaustive scientific, process/crash, production-identity or cluster
coverage. Those tests were subsequently moved to
`tests/nodb/test_batch_daymet_multiple_contention.py`; the commands above record
the actual locations used at execution time.

Final independent command:

```text
wctl run-pytest tests/nodb/test_batch_daymet_multiple_contention.py \
  tests/nodb/test_batch_climate_rap_contention.py \
  -k 'unknown_commit or old_publication' -vv --tb=short
```

Result: **3 passed**, 68 deselected, 16.12 seconds. An actual unknown commit
readback failure retains a visible prior-output backup; established browse
listing/download and canonical archive/restore preserve its exact bytes. Shared
RAP unknown-outcome retention and successor-safe rollback also pass after the
backup-prefix change. Thus **23 targeted test instances passed** across four
independent runs; the total includes one repeated rollback check.

The canonical inventory identifies retained Daymet/PRISM source/work products,
status, recovery backups and redundant coordination copies, normal authorized
visibility and directory-mode archive requirements, plus concise rationale.
Developer/operator guidance documents owned startup/resync, standalone-token
preservation, unchanged lease and separate incident attribution.

Independent doc lint for the canonical inventory and developer/operator note:
**2 files validated, 0 errors, 0 warnings**. The security artifact is linted again
after this final review update.

### Final Compatibility Delta Review

Climate resynchronization now invokes the normal reader's existing
`_ensure_legacy_module_imports` on the base document before decoding configured
attributes. The helper admits only redirects discovered from the owned NoDb
package; its import target comes from that existing registry, not an arbitrary
module name in persisted input. It does not widen the reader's admitted modules,
add a new external dependency, or change run authorization. Current and admitted
legacy Climate enum values now follow the same existing decoding path.

Acquisition cleanup now uses `with ExitStack()` instead of a separate broad
`BaseException` cleanup handler. Earlier acquired guards are still released on
any exceptional exit, and only acquisition `NODIR_LOCKED` is retried. Callback
failures remain outside that retry boundary and propagate without replay.

Independent delta command:

```text
wctl run-pytest tests/nodb/test_batch_daymet_multiple_contention.py \
  -k 'resync or batch_leaf_guard' -vv --tb=short
```

Result: **5 passed**, 29 deselected, 14.83 seconds: current/legacy resync preserve
the unrelated durable edit, duplicate exclusion holds before/after root reset,
and callback failure is not replayed. No new security findings. The updated
production-diff fingerprint above includes both bounded deltas; **28 targeted
test instances passed** across five independent runs, including repeated checks.
This delta approval does not change any release, identity or cluster claim.

## Required Pre-Release Evidence

- Final correctness/QA dispositions and required broad regression checks.
- Actual browse/download/read of working/failed attempts and recovery records
  under normal project authorization and intended browser/worker UID, groups,
  mounts, umask and configuration. Injected public `AuthContext` tests prove
  route/file behavior only; they cannot satisfy live authorization or identity
  parity. Do not deploy across these boundaries without that evidence.
- Separately declared cluster fixture/write set, exact candidate image/revision,
  rollback and stop conditions; shared Redis/resolved-path lock identity,
  bounded runtime, complete RQ tree and generated/consumed outputs.
- Attribute the actual incident writer, or explicitly retain the uncertainty
  when reporting acceptance; local injected rewrites are not that attribution.

Missing operational evidence is distinguished from an unresolved source defect.
No operator risk acceptance has waived any of these required gates.

## Residual Risk

- **Accepted risks**: none recorded.
- Multi-file publication is not crash-atomic; existing explicit failure/recovery
  behavior remains necessary.
- The widened leaf guard retains the existing six-hour maintenance lease with
  no renewal. Bounded execution must complete within that ownership window;
  source inspection alone does not prove production runtime or expired-owner
  safety. This review does not authorize longer leases or a new lock mechanism.
- Exact cluster writer, shared Redis/path lock identities and duplicate RQ
  behavior remain unverified acceptance gates, separately from SEC-02's source
  finding.
- Directory-backed native datasets retain existing root-metadata identity;
  comprehensive member-dependency closure is outside this change's authority.
- Broader legacy GridMET artifact-retention behavior and historical hidden
  recovery-directory migration are outside the new Daymet extraction. Newly
  produced observed PRISM and shared recovery records are visible; old hidden
  backups remain records and must not be deleted during rebuilding or recovery.

## Sign-off

- **Security reviewer**: independent `security_reviewer`, 2026-09-30; local
  source findings resolved and targeted forest checks passed. Release/closeout
  approval is withheld until the required prerelease evidence passes.
- **Package owner**: no risk acceptance or closeout acknowledgment recorded.

## Artifact Observability Gate (Required)

Authority: [artifact observability](../../../standards/artifact-observability-standard.md).

- [x] Comparable Climate module and canonical inventory name attempts/status.
- [x] Direct writer/failure tests prove retained work products; canonical archive
  and restore prove member coverage/byte equality; established route tests prove
  listing/download/status for working/failed attempts and recovery records.
- [ ] Live browser/download evidence exists under normal project authorization
  and intended identities; this remains a required prerelease gate.
- [x] No new hidden-only project-record exclusion or unapproved exception:
  `.climate-publish-*` contains redundant publication copies, while original
  candidate records and interrupted recovery backups remain visible.

The local source and executable retention/archive/route gates pass. The complete
artifact-observability gate remains open for live authorization/service-identity
evidence; source approval does not substitute for that release requirement.
