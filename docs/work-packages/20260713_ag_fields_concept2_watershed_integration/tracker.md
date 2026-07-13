# Tracker - AgFields Concept 2 Watershed Integration

> Living record for weighted PASS accounting, isolated watershed execution, and
> the scientific-evaluation handoff.

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-13 19:37 UTC

**Current phase**: Implementation planning and semantic-contract finalization

**Last updated**: 2026-07-13 19:37 UTC

**Next milestone**: Accept ADR-0018 and implement the conservation-tested weighted
PASS kernel

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-07-13_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Finalize the PASS field-semantics table and serialization-derived closure
  tolerances; update ADR-0018 from Proposed to Accepted.
- [ ] Implement, export, document, build, and test the weighted `wepppyo3` PASS API.
- [ ] Implement the AgFields watershed-integration collaborator, additive facade
  state, isolated workspace, manifests, and interchange generation.
- [ ] Add RQ/API/UI stage, staleness/readiness/clear behavior, and dependency graph
  updates.
- [ ] Complete synthetic, focused, security, and generated-output validation.
- [ ] Produce and hand off the `sacral-self-discipline` evaluation bundle to Mariana.

### In Progress

- [ ] Ground the semantic table against the WEPP PASS writer/reader, especially
  `gwbfv`, `gwdsv`, particle-class fields, header area, and hydrograph terms.

### Blocked

None. Mariana's evaluation follows engineering delivery and does not block starting
or implementing Concept 2.

### Done

- [x] Selected Concept 2, opened its implementation scope, assigned scientific
  evaluation to Mariana, and deferred Concept 1 (2026-07-13 19:37 UTC).
- [x] Inspected the current AgFields, Roads, RQ/API/UI, PASS parser/combiner, and
  dev-project contracts (2026-07-13 19:37 UTC).
- [x] Created the package, active ExecPlan, compatibility plan, proposed ADR, initial
  security review, and root tracker entry (2026-07-13 19:37 UTC).

## Timeline

- **2026-07-13 19:37 UTC** - Package opened. Concept 2 became the sole implementation
  track; Concept 1 was explicitly deferred.
- **2026-07-13 19:37 UTC** - `/wc1/runs/sa/sacral-self-discipline` designated as the
  generated-output dev and scientific-evaluation project.

## Decisions Log

### 2026-07-13 19:37 UTC: Open Concept 2 and defer Concept 1

**Context**: Both concepts were feasible enough to plan, but Concept 2 retains the
independent sub-field simulations and their source accounting without quantizing
the field mosaic into parent-profile OFEs.

**Decision**: Implement Concept 2. Do not implement Concept 1 or require it as a
comparison fixture. Mariana Dobre performs the scientific evaluation after the
engineering result and evidence bundle exist.

**Impact**: Engineering acceptance uses area, water, sediment, parser, integration,
and generated-output gates. Concept 1 can be reopened only by a separate decision.

### 2026-07-13 19:37 UTC: Preserve all existing run artifacts

**Context**: The dev project has independent sub-field PASS files but its parent
PASS files were deleted after interchange because the parent setting is
`delete_after_interchange=true`.

**Decision**: Materialize current parent legacy PASS files by rerunning prepared
parent hillslope inputs inside `wepp/ag_fields/watershed/`. Never toggle the parent
setting or rewrite baseline and independent AgFields trees.

**Impact**: The feature works on the designated project and historical projects
with cleaned baseline PASS files. The manifest records that parent sources were
materialized, not silently recovered.

### 2026-07-13 19:37 UTC: Separate engineering and scientific acceptance

**Context**: Conservation and executable routing are engineering claims; buffer
effects and suitable scientific use require domain evaluation.

**Decision**: Close engineering milestones only on conservation, integration,
compatibility, security, and generated-output evidence. Label scientific
qualification pending until Mariana records her disposition.

**Impact**: No unreviewed delivery-ratio or buffer correction enters the build.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| A PASS field is scaled with the wrong dimensional semantics | High | Medium | Required field-semantics table, WEPP source evidence, identities, reparse closure | Open |
| Parent/sub-field calendars or climate files differ | High | Low | Resolve and compare climate sources, headers, row counts, and day keys; fail explicitly | Open |
| Baseline cleanup leaves no parent PASS | High | Confirmed | Regenerate legacy PASS from current prepared inputs in the isolated workspace | Mitigated in design |
| Large dev run causes excessive time/disk use | Medium | Medium | Hard-link/copy inputs, bounded worker count, retain only needed parent PASS, progress logs | Open |
| Partial runs are mistaken for current results | High | Low | Versioned source signature, terminal state, required-artifact checks, explicit clear/retry | Open |
| Outlet injection is interpreted as buffer routing | High | Medium | UI/docs/manifest warning and Mariana-owned scientific-use disposition | Open |
| Queue or clear operations overlap | High | Low | Existing AgFields single-flight guard extended to the new job and route tests | Open |

## Verification Checklist

### Native Kernel

- [ ] `cargo fmt --check` and `cargo test -p wepp_interchange_rust` pass.
- [ ] Existing Roads `combine_hillslope_pass_files` behavior and tests remain unchanged.
- [ ] Canonical py312 release import and focused Python API tests pass.

### WEPPpy

- [ ] Focused NoDb/AgFields collaborator tests pass through `wctl run-pytest`.
- [ ] RQ and rq-engine AgFields route tests pass.
- [ ] Frontend lint/Jest tests and regenerated controller bundle pass.
- [ ] `wctl check-rq-graph`, stub checks, broad-exception gate, and docs lint pass.
- [ ] Repository-wide `wctl run-pytest tests --maxfail=1` passes or any unrelated
  baseline stop is reproduced and documented.

### Generated Output

- [ ] Dev project input inventory and existing-artifact hashes are captured before
  execution.
- [ ] Exactly one integrated PASS is staged per parent hillslope.
- [ ] Area/source/event/run closure is within the accepted tolerance.
- [ ] Watershed run and interchange resources complete under the isolated tree.
- [ ] Existing baseline and independent AgFields artifacts remain byte-identical.
- [ ] Evaluation bundle and limitations README are handed to Mariana.

### Security and Documentation

- [ ] ADR-0018 Accepted before merge.
- [ ] Compatibility plan reflected in code/tests/docs.
- [ ] Dedicated security review passes with no unresolved medium/high findings.
- [ ] AgFields README, UI contract, usersum design, output docs, package, tracker,
  and ExecPlan describe as-built behavior.

## Progress Notes

### 2026-07-13 19:37 UTC: Package opening and fixture discovery

**Agent/Contributor**: Codex

**Work completed**:

- Converted the concept comparison into a selected implementation decision.
- Recorded Mariana as scientific evaluator and removed Concept 1 from active
  implementation and validation dependencies.
- Inspected the real project, current controller/RQ/UI surface, Roads precedent,
  and native PASS combiner.
- Authored the required planning/governance artifacts.

**Dev-project evidence**:

- 6,626 sub-field records and independent legacy PASS files.
- 1,869 affected parent hillslopes out of 3,543 total parent hillslopes.
- 113,774,400 m2 retained field area within 176,981,400 m2 affected parent area.
- No overcovered parent; 482 affected parents have full field coverage.
- `length * width` differs from raster area by at most `5.9e-11` m2.
- Parent `wepp/output` has no `H*.pass.dat`; interchange cleanup removed them.

**Next steps**:

- Confirm PASS writer semantics and accept ADR-0018.
- Implement the weighted native API before WEPPpy orchestration.

**Test results**: Documentation validation is recorded after package scaffolding.

## Watch List

- PASS header line 3 appears to be modeled area and must be parsed/validated rather
  than inferred only from Peridot `length * width`.
- `gwbfv` and `gwdsv` lack unit metadata in the current interchange schema.
- The parent project uses legacy ASCII PASS but deletes it after interchange; the
  isolated path must not depend on baseline retention settings.

## Communication Log

### 2026-07-13 19:37 UTC: Delivery ownership

**Participants**: Roger Lew, Codex

**Outcome**: Concept 2 implementation opened; Concept 1 deferred; Mariana Dobre
will perform the science evaluation; `sacral-self-discipline` is the dev project.
