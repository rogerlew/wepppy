# Tracker - AgFields Sub-field WEPP Interchange Integration

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-16 18:53 UTC
**Current phase**: Discovery and contract design
**Last updated**: 2026-07-16 19:05 UTC
**Next milestone**: Freeze the opt-in native identity contract and its no-regression fixtures
**Security impact**: low
**Dedicated security review**: no
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Capture pre-change ordinary-writer golden outputs and schemas in
  `wepppyo3`; prove the fixture set covers PASS/HBP, EBE, ELEMENT, LOSS, SOIL,
  and WAT.
- [ ] Implement six dedicated native AgFields writers using shared parser
  internals without changing the ordinary public writer paths.
- [ ] Add PyO3 binding tests for exact propagation and every mapping rejection
  case; add an AgFields dataset-kind schema contract without rewriting ordinary
  snapshots.
- [ ] Rebuild only the canonical `wepp_interchange` release artifact, update
  provenance, and verify import origin and public signatures.
- [ ] Add the specialized staged WEPPpy AgFields interchange orchestrator and
  focused contract tests.
- [ ] Wire it into `run_ag_fields_wepp_rq` between WEPP completion and the
  preflight timestamp/completion event.
- [ ] Update AgFields and interchange documentation in both repositories.
- [ ] Run targeted and full gates, then perform staged generated acceptance on
  `sacral-self-discipline` and record resource, identity, and immutability
  evidence.
- [ ] Obtain independent code review and QA review; resolve all high/medium
  findings before closeout.

### In Progress

- [ ] Finalize the native identity/dataset-kind contract and regression fixture
  matrix from the initial reconnaissance.

### Blocked

- None.

### Done

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
| Shared parser refactoring changes ordinary schemas or values | High | Medium | Dedicated public APIs, golden ordinary outputs, exact schema snapshots, independent review | Open |
| Mapping rows attach the wrong field to a raw file | High | Medium | Key by parsed `H<n>`, require one-to-one coverage, reject missing/extra/duplicate ids, full-corpus anti-join | Open |
| Parent `topaz_id` is misrepresented as sub-field identity | High | Medium | Contract forbids propagation; focused negative tests and schema assertion | Open |
| Large conversion exhausts worker memory or disk | High | Medium | Native streaming writers, bounded staging, disk preflight, monitor peak RSS/disk, retain raw inputs | Open |
| RQ reports success after partial interchange failure | High | Low | Interchange precedes timestamp/result/completion; inject failures in each family | Open |
| Stale native `.so` makes Python and Rust signatures disagree | High | Medium | Canonical release rebuild, provenance update, host and restarted-container import/signature tests | Open |
| Existing bundle is destroyed by a failed rerun | High | Low | Unique stage, validate before publish, backup/restore around directory replacement | Open |
| Queue graph changes accidentally | Medium | Low | No child job; run `wctl check-rq-graph` and inspect static catalog diff | Open |
| Full acceptance mutates watershed or baseline artifacts | High | Low | Protected-file inventory before/after; scope writes to `wepp/ag_fields/output/interchange` | Open |
| Global dataset version changes create unrelated churn | Medium | Low | Use a versioned AgFields dataset-kind/schema marker; do not bump the ordinary dataset version without explicit plan revision and owner review | Open |

## Verification Checklist

### Code Quality

- [ ] `cargo fmt --check` passes in `/home/workdir/wepppyo3`.
- [ ] `cargo test -p wepp_interchange_rust` passes.
- [ ] Changed-file broad-exception and quality observability checks are recorded.
- [ ] No new external dependency is introduced.

### Security

- [x] Initial security impact triage recorded as low.
- [ ] Confirm final diff has no new route, queue edge, user-controlled path,
  subprocess behavior, or out-of-run write.
- [ ] Escalate to a dedicated security review if the scope crosses that boundary.

### Documentation

- [ ] `wepppy/nodb/mods/ag_fields/README.md` documents stage-4 interchange and
  identity semantics.
- [ ] `docs/dev-notes/wepp_interchange.spec.md` documents the AgFields dataset kind.
- [ ] WEPPpyo3 module/provenance docs describe the public signature and rebuilt
  artifact.
- [ ] Work package, tracker, compatibility plan, and ExecPlan match as-built
  behavior.
- [x] Parameterization ADR confirmed unnecessary.

### Testing

- [ ] Ordinary native writer golden parity and exact schema tests pass.
- [ ] AgFields native identity propagation/rejection tests pass.
- [ ] WEPPpy specialized orchestrator tests pass.
- [ ] RQ ordering, success, and injected-failure tests pass.
- [ ] Ordinary WEPPpy interchange snapshots and consumer tests pass unchanged.
- [ ] Full forest generated-output identity and protected-file checks pass.

### Deployment

- [ ] Canonical native release artifact and provenance are refreshed.
- [ ] Host and container import origins resolve to the canonical release.
- [ ] Forest stack is restarted only after pre-restart targeted gates pass.
- [ ] Actual RQ stage-4 acceptance reaches terminal success with all six resources.
- [ ] Rollback is rehearsed/documented: restore the prior native release and
  WEPPpy code, restart, and leave raw outputs intact.

## Progress Notes

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
