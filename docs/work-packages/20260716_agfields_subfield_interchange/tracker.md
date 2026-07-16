# Tracker - AgFields Sub-field WEPP Interchange Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-16 18:53 UTC
**Current phase**: Complete
**Last updated**: 2026-07-17 04:15 UTC
**Next milestone**: None; monitor ordinary and AgFields interchange consumers
**Security impact**: low
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- None.

### Done

- [x] Captured the complete six-family ordinary golden and pre-change native
  release provenance before Rust edits (2026-07-16 19:14 UTC).
- [x] Implemented and validated six dedicated native AgFields writers while
  retaining exact ordinary Arrow-table/schema/metadata parity
  (2026-07-16 19:29 UTC).
- [x] Atomically installed canonical native SHA
  `8c42edd0a8e1b03bdaf423355a12414180c709efaac3e379e5dd23e6cc77214e`
  with the prior SHA retained for rollback (2026-07-16 19:31 UTC).
- [x] Added the specialized serialized/failure-atomic WEPPpy orchestrator,
  RQ ordering, false-completion marker, and corrected Features Export identity
  contract; focused cross-layer suite passed 70 tests (2026-07-16 19:32 UTC).
- [x] Published the full 6,626-subfield bundle twice, validated every mapping
  anti-join/order/schema/manifest invariant, measured 7m48.63s and 751,956 KiB
  peak RSS, and preserved all direct-conversion protected hashes
  (2026-07-17 03:21 UTC).
- [x] Resolved the final independent code/QA findings by rejecting stale
  AgFields metric exports and impossible non-EBE zero-row completion metadata;
  the consolidated cross-layer suite passed 191 tests
  (2026-07-17 03:20 UTC).
- [x] Passed the full WEPPpy suite (4,984 passed, 58 skipped), restarted all six
  importers, and verified canonical native origin/SHA/signatures in each
  (2026-07-17 03:38-03:41 UTC).
- [x] Completed authenticated job
  `9ff0f757-3ec4-4d48-ae1c-f3f6de2c8e84` in 30m11s; state and independent deep
  validation reported current completion, protected hashes remained exact, and
  no stage/backup debris remained (2026-07-17 04:12 UTC).

- [x] Confirmed the current stage-4 RQ worker returns directly after
  `run_wepp_ag_fields` and does not invoke interchange (2026-07-16 18:53 UTC).
- [x] Confirmed the acceptance run has 6,626 files in each of the six target
  families, about 13.5 GiB apparent input (about 3.7 GiB allocated across all
  seven sparse raw families), and no interchange directory
  (2026-07-16 18:53 UTC).
- [x] Confirmed `fields.parquet` has 6,626 unique `sub_field_id` values and 2,169
  distinct `field_id` values (2026-07-16 18:53 UTC).
- [x] Scaffolded the package, active ExecPlan, compatibility plan, and project
  tracker entry (2026-07-16 18:53 UTC).

## Timeline

- **2026-07-16 18:53 UTC** - Package created and initial local/run-tree
  reconnaissance completed.
- **2026-07-16 19:11 UTC** - Began active execution against the package
  ExecPlan; confirmed both repositories were clean and froze the canonical
  pre-change native SHA as
  `7419203c8b91db1b595590b7c9a28040662d5fad9fdf8b182a17c85a76d518e4`.
- **2026-07-17 03:38 UTC** - All final repository gates passed; coordinated
  forest restart and per-importer ABI verification completed.
- **2026-07-17 04:12 UTC** - Authenticated stage-4 acceptance finished and all
  generated/protected-scope postchecks passed.

## Decisions Log

### 2026-07-16 18:53 UTC: Isolate identity behind dedicated AgFields APIs

**Context**: All six established writers are shared by baseline WEPP and roads
workflows, and exact schema snapshots were strengthened one day before this
package began.

**Options considered**:

1. Add `field_id` and `sub_field_id` to every ordinary hillslope dataset.
2. Post-process native Parquet in Python after conversion.
3. Add optional identity arguments to the six existing native writer APIs.
4. Add six dedicated AgFields writer APIs that reuse parser internals but own
   separate schemas and source descriptors.

**Decision**: Use option 4. The existing public functions are protected
compatibility surfaces and must not gain conditional schema/signature behavior.
WEPPpy constructs coupled `(path, field_id, sub_field_id)` descriptors, while
Rust repeats identity validation and owns final record/Parquet construction.

**Impact**: Parser/scientific logic remains shared, but public APIs and schemas
are isolated. Both variants require explicit tests.

### 2026-07-16 18:53 UTC: Use only real AgFields identity in the new schema

**Context**: WEPP names each AgFields raw report `H<sub_field_id>.*`, so today's
native parser emits that numeric token as `wepp_id`. The sub-field row also
contains a parent hillslope `topaz_id`, but the sub-field itself is not a TOPAZ
hillslope.

**Decision**: The dedicated AgFields schema begins with required `field_id` and
`sub_field_id`, followed by the unchanged measurement/date columns. It does not
emit a misleading `wepp_id` or `topaz_id`. Require the parsed filename token to
equal `sub_field_id` and fail explicitly on disagreement. Update the existing
Features Export catalog in the same change so it joins these new datasets on
`sub_field_id` rather than relying on the current ambiguous `wepp_id` entry.

**Impact**: Ordinary readers are untouched, and the previously nonexistent
AgFields bundle starts with semantically correct identity. The catalog update is
part of acceptance rather than deferred compatibility debt.

### 2026-07-16 18:53 UTC: Keep interchange in the existing RQ job

**Context**: A separate child job would add queue lifecycle, dependency, UI job
tree, cancellation, and graph-contract work unrelated to the missing call.

**Decision**: Call the specialized orchestrator synchronously inside
`run_ag_fields_wepp_rq` after successful WEPP execution and before the existing
timestamp/result/completion sequence.

**Impact**: No enqueue site or queue edge should change. The job timeout already
covers the full stage, and a native failure prevents false success.

### 2026-07-16 18:53 UTC: Stage the six-file bundle before publication

**Context**: Publishing family-by-family can leave a mixed or partial bundle
when a later parser fails, and the supplied run is large enough that failures
may occur late.

**Decision**: Write all targets under a unique run-scoped staging directory,
validate schemas, counts, ids, and metadata, then atomically replace/publish the
completed interchange directory. Preserve raw reports on every outcome.

**Impact**: Reruns are safe, failed conversions remain diagnosable, and consumers
do not see a partially refreshed bundle.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Shared parser refactoring changes ordinary schemas or values | High | Medium | Dedicated public APIs, golden ordinary outputs, exact schema snapshots, independent review | Mitigated; exact parity passed |
| Mapping rows attach the wrong field to a raw file | High | Medium | Key by parsed `H<n>`, require one-to-one coverage, reject missing/extra/duplicate ids, full-corpus anti-join | Mitigated; 6,626-id anti-join passed |
| Parent `topaz_id` is misrepresented as sub-field identity | High | Medium | Contract forbids propagation; focused negative tests and schema assertion | Mitigated; schemas contain only real identities |
| Large conversion exhausts worker memory or disk | High | Medium | Native streaming writers, bounded staging, disk preflight, monitor peak RSS/disk, retain raw inputs | Mitigated; 752 MiB peak, no swap |
| RQ reports success after partial interchange failure | High | Low | Interchange precedes timestamp/result/completion; inject failures in each family | Mitigated; every family failure gate passed |
| Stale native `.so` makes Python and Rust signatures disagree | High | Medium | Canonical release rebuild, provenance update, host and restarted-container import/signature tests | Mitigated in all six importers |
| Existing bundle is destroyed by a failed rerun | High | Low | Unique stage, validate before publish, backup/restore around directory replacement | Mitigated; failure injection and replacement passed |
| Queue graph changes accidentally | Medium | Low | No child job; run `wctl check-rq-graph` and inspect static catalog diff | Mitigated; graph gate passed |
| Full acceptance mutates watershed or baseline artifacts | High | Low | Protected-file inventory before/after; scope writes to `wepp/ag_fields/output/interchange` | Mitigated; all three post-RQ protected hashes exact |
| Global dataset version changes create unrelated churn | Medium | Low | Use a versioned AgFields dataset-kind/schema marker; do not bump the ordinary dataset version without explicit plan revision and owner review | Avoided; ordinary version unchanged |
| Raw WEPP signature makes state look complete after interchange failure | High | Medium | Separate persisted interchange signature, invalidate before run, set after publication, require manifest+signature in state snapshot | Mitigated; state/failure regressions passed |
| Stale retained bundle is exported after readiness invalidation | High | Medium | Detached read-only semantic readiness gate before Features Export dependency planning | Mitigated; marker/hash/major regressions passed |

## Verification Checklist

### Code Quality

- [x] `cargo fmt --check` passes in `/home/workdir/wepppyo3`.
- [x] `cargo test -p wepp_interchange_rust` passes.
- [x] Changed-file broad-exception and quality observability checks are recorded.
- [x] No new external dependency is introduced.

### Security

- [x] Initial security impact triage recorded as low.
- [x] Confirm final diff has no new route, queue edge, user-controlled path,
  subprocess behavior, or out-of-run write.
- [x] Confirmed the scope did not cross the dedicated-review boundary.

### Documentation

- [x] `wepppy/nodb/mods/ag_fields/README.md` documents stage-4 interchange and
  identity semantics.
- [x] `docs/dev-notes/wepp_interchange.spec.md` documents the AgFields dataset kind.
- [x] WEPPpyo3 module/provenance docs describe the public signature and rebuilt
  artifact.
- [x] Work package, tracker, compatibility plan, and ExecPlan match as-built
  behavior.
- [x] Parameterization ADR confirmed unnecessary.

### Testing

- [x] Ordinary native writer golden parity and exact schema tests pass.
- [x] AgFields native identity propagation/rejection tests pass.
- [x] WEPPpy specialized orchestrator tests pass.
- [x] RQ ordering, success, and injected-failure tests pass.
- [x] Ordinary WEPPpy interchange snapshots and consumer tests pass unchanged.
- [x] Full forest generated-output identity and protected-file checks pass.

### Deployment

- [x] Canonical native release artifact and provenance are refreshed.
- [x] Host and container import origins resolve to the canonical release.
- [x] Forest stack is restarted only after pre-restart targeted gates pass.
- [x] Actual RQ stage-4 acceptance reaches terminal success with all six resources.
- [x] Paired rollback is documented with exact revisions/hashes and leaves raw
  outputs intact. It was not executed because that would undo the accepted
  deployment; pre-change artifact recovery and both revert boundaries were
  independently verified.

## Progress Notes

### 2026-07-17 04:15 UTC: Generated and operational acceptance complete

**Agent/Contributor**: Codex with independent code and QA reviewers

**Outcome**: All repository gates passed, all high/medium review findings were
resolved, the forest importer set was restarted against one canonical native
SHA, and authenticated stage-4 job
`9ff0f757-3ec4-4d48-ae1c-f3f6de2c8e84` reached terminal success. Independent
deep validation, current-state checks, full descriptor/identity summaries, and
protected-scope hashes all passed. Exact evidence and rollback commands are in
the package artifacts.

### 2026-07-16 19:20 UTC: Independent review found a false-completion path

**Agent/Contributor**: Independent regression reviewer and Codex

**Finding**: `run_wepp_ag_fields()` persists the raw-WEPP source signature
before the new interchange call, while rq-engine's `wepp.complete` ignored both
the RedisPrep timestamp and interchange publication. An interchange exception
could therefore leave the API reporting stage 4 complete.

**Disposition**: High severity, accepted. Add a separate persisted interchange
completion signature, invalidate it before raw WEPP execution and clear paths,
set it only after bundle publication, and require it plus a valid manifest in
the state snapshot. Add failure coverage with a preexisting bundle.

### 2026-07-16 18:53 UTC: Initial scaffold and evidence capture

**Agent/Contributor**: Codex with three read-only reconnaissance agents

**Work completed**:

- Traced the current RQ endpoint through the AgFields controller and raw output
  directory.
- Examined the six native bulk writer signatures and ordinary schema snapshots.
- Inspected the local acceptance run without mutating it.
- Created the package documents and active executable plan.

**Blockers encountered**:

- None. The final internal Rust API shape must be confirmed during Milestone 1,
  but the external compatibility contract is fixed here.

**Next steps**:

- Capture pre-change goldens before touching native code.
- Implement the smallest shared identity primitive and one writer first.
- Promote to all six writers only after the ordinary and AgFields tests pass for
  the first writer.

**Test results**: `wctl doc-lint` passed for the package (`4 files, 0 errors,
0 warnings`) and `PROJECT_TRACKER.md` (`1 file, 0 errors, 0 warnings`);
`git diff --check` passed. Spelling preview found no package-file changes.

## Watch List

- **Schema/dataset-kind versioning**: keep ordinary dataset metadata stable;
  record the AgFields schema independently and validate required columns rather
  than trusting the current major-only refresh check.
- **Peak memory and stage size**: the acceptance input is about 13.5 GiB apparent
  (sparse on disk) and contains 39,756 target raw files.
- **Existing raw-data consumers**: do not enable delete-after-interchange.
- **Release import origin**: the source checkout and deployed `.so` must not drift.

## Communication Log

### 2026-07-16 18:53 UTC: User scope and authority

**Participants**: User, Codex
**Question/Topic**: Add AgFields native identity support, wire stage-4 RQ to
interchange, use the supplied forest project, and assess regression risk.
**Outcome**: Work-package scaffolding authorized; local stack restart and
subagent dispatch authorized for later implementation/acceptance.
