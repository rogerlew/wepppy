# Tracker - MOFE scenario artifact integrity and Abdisa run repair

> Living execution record for the MOFE recurrence, Forest acceptance, and
> operator-gated production repair.

## Quick Status

**Timezone**: UTC
**Started**: 2026-09-17 22:39 UTC
**Current phase**: contract and regression planning
**Last updated**: 2026-09-17 22:57 UTC
**Next milestone**: ratify the canonical generated-artifact contract before code edits
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Ratify the canonical MOFE management artifact contract and commit the
      reviewed checkpoint as a standalone ancestor.
- [ ] Write regressions that fail against the real SBS classification contract,
      class-to-class writer path, and 0.30/0.50 canopy propagation.
- [ ] Implement the three bounded corrections without changing parameter values,
      RAP precedence, schemas, or queue topology.
- [ ] Complete focused, related, broad, documentation, correctness, and QA gates.
- [ ] Deploy the exact candidate revision to Forest through the canonical script.
- [ ] Restore or clone the actual Rithet Creek project on Forest and run all
      scenario roles through landuse, WEPP preparation, WEPP, and summary export.
- [ ] Present Forest evidence and stop for Roger's WEPPcloud deployment.
- [ ] After explicit deployment confirmation, manually process all eight Abdisa
      runs on wepp1 and complete the repair ledger.
- [ ] Compare the refreshed hillslope response summary and close the package.

### In Progress

- [ ] Prepare the contract decision, incident evidence, acceptance record, and
      production repair ledger for review.

### Blocked

- [ ] Forest execution is blocked until implementation and local gates pass.
- [ ] Production repair is blocked until Forest acceptance passes and Roger
      explicitly confirms deployment of the accepted revision to WEPPcloud.

### Done

- [x] Confirmed the three failing source boundaries and the mismatch between
      persisted intent and generated management files (2026-09-17 22:39 UTC).
- [x] Confirmed the September 7 clone was not valid end-to-end evidence: its job
      completed and NoDb state looked correct, but all generated MOFE management
      files matched baseline (2026-09-17 22:39 UTC).
- [x] Scaffolded this active work package and hard release gates
      (2026-09-17 22:39 UTC).
- [x] Validated the root tracker and all nine package Markdown files with
      `wctl doc-lint`; all ten passed with zero errors/warnings
      (2026-09-17 22:47 UTC).
- [x] Promoted the incident's general lesson into the canonical generated-
      artifact validation standard and wired it into root agent guidance, package
      templates, tracker checks, correctness review, observability, and hardening
      guidance (2026-09-17 22:55 UTC).

## Timeline

- **2026-09-07 20:06:16 UTC** - User-reported execution time for the cloned
  `aliquot-shoji` validation run (13:06:16 Pacific daylight time).
- **2026-09-07 20:07 UTC** - User reported to Abdisa that the MOFE problem was
  fixed; later artifact inspection invalidated that claim.
- **2026-09-17 22:39 UTC** - Production runs and prior clone inspected read-only;
  three defects isolated and no run data changed.
- **2026-09-17 22:39 UTC** - New incident/remediation package opened.
- **2026-09-17 22:55 UTC** - Durable generated-artifact validation and completion-
  claim guidance promoted outside the work package and made agent-discoverable.

## Decisions Log

### 2026-09-17 22:39 UTC: Completion requires generated artifacts

**Context**: The prior validation relied on passing tests, job completion, and
correct NoDb values while generated files remained identical to baseline.

**Options considered**:

1. Reuse job success and NoDb state as acceptance.
2. Require real project output readback at every generation boundary.

**Decision**: Use option 2. No fix claim is permitted without content-level
evidence from `landuse/hill_*.mofe.man`, `wepp/runs/*.man`, and completed outputs.

**Impact**: Mock-only or metadata-only checks cannot release the candidate.

### 2026-09-17 22:39 UTC: Forest is a hard deployment gate

**Context**: The operator requires actual Forest validation before deploying to
WEPPcloud.

**Decision**: Finish local work, deploy the exact candidate to Forest, exercise an
actual cloned/restored project, and stop after presenting retained evidence.
Roger owns the subsequent WEPPcloud deployment.

**Impact**: No production mutation or deployment is authorized in the first phase.

### 2026-09-17 22:39 UTC: The repair inventory is all eight named runs

**Context**: The user directed that all Abdisa runs be manually fixed after
deployment.

**Decision**: The production ledger contains the baseline plus seven scenarios;
none may be omitted. Preserve pre-repair evidence, then rebuild and rerun each
under the deployed accepted revision. The baseline remains the scientific control
but is processed so the comparison uses one generation revision.

**Impact**: Closure requires eight completed and verified ledger rows.

### 2026-09-17 22:39 UTC: Preserve parameterization

**Context**: The defect is propagation, not a request to choose new scientific
values.

**Decision**: Reuse classified severity, selected class, and stored cover values.
Initialize MOFE canopy synthesis from the existing summary override and preserve
RAP's current segment-specific replacement when RAP is active.

**Impact**: Formula, threshold, lookup, default, or RAP precedence changes require
a separate ADR and explicit operator decision.

### 2026-09-17 22:55 UTC: Promote the broader lesson into agent governance

**Context**: The prior false-positive fix resulted from treating persisted state,
job success, and a mismatched test double as proof of generated-output correctness.

**Decision**: Make the consumed artifact the executable truth. Require a staged
evidence chain and distinguish diagnosed, implemented, locally validated,
environment validated, deployed, repaired, and incident resolved.

**Impact**: Root `AGENTS.md`, work-package scaffolds, correctness review, artifact
observability, and hardening guidance now route agents to the canonical standard.
The rule survives this package's closure.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Tests repeat the old unrealistic SBS stub | High | Medium | Exercise real `SoilBurnSeverityMap.data`/`build_lcgrid` behavior and inspect files | Open |
| Successful rebuild leaves mixed generations after writer failure | High | Medium | Contract explicit failure/rollback semantics and inject a real writer failure | Open |
| Forest uses a different revision than the reviewed candidate | High | Low | Record host/container revision and source checksum before acceptance | Open |
| Production repair starts before deployment | High | Low | Hard block and explicit operator confirmation in the ledger | Open |
| Output equality is misread as either proof or failure | Medium | Medium | Verify input semantics first and explain any legitimate equal output | Open |
| Existing dirty worktree is overwritten | High | Low | Restrict edits to this package and a surgical root tracker addition | Mitigated |

## Hardening Signal Log

- **Baseline health signals**: low/moderate/prescribed management manifests are
  identical; 30%/50% manifests are identical; NoDb intent disagrees with files;
  the September 7 clone reproduced baseline files after a green job.
- **Post-change health signals**: pending local, Forest, and production evidence.
- **Danger signals observed**: the previous test double returned raw SBS values,
  unlike production's already-classified values; prior validation explicitly
  omitted a complete live landuse/WEPP replay.
- **Temporary callus register**: none.
- **Softening experiments**: not applicable.

## Verification Checklist

### Contract and Code Quality

- [ ] Contract decision records every affected current contract and state.
- [ ] Two independent read-only contract reviews are dispositioned.
- [ ] Standalone contract ancestor precedes implementation.
- [ ] Focused regressions fail before and pass after the correction.
- [ ] `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` passes.
- [ ] `wctl run-pytest tests --maxfail=1` passes or a concrete unrelated blocker is retained.

### Correctness and Security

- [ ] Correctness artifact passes with no unresolved high/medium findings.
- [ ] QA review passes with no unresolved high/medium findings.
- [ ] Existing authentication, path, locking, cache, and RQ status boundaries are
      preserved.
- [ ] Security impact remains low; any attack-surface expansion triggers a new
      security review.

### Documentation and Observability

- [ ] Canonical contract and affected operator/developer docs are updated.
- [ ] All changed Markdown passes `wctl doc-lint` and spelling preview.
- [ ] Working, failed, and completed generated artifacts remain browsable and
      archivable under the normal project boundary.
- [ ] No parameterization change occurred; otherwise an ADR exists first.

### Forest Acceptance

- [ ] Exact candidate revision and container checksums recorded.
- [ ] Actual project source and clone/restore provenance recorded.
- [ ] All scenario jobs and IDs recorded.
- [ ] `landuse` and `wepp/runs` management manifests and parsed values retained.
- [ ] Soil artifacts and SBS class distributions retained where applicable.
- [ ] WEPP outputs and refreshed hillslope summary compared.
- [ ] Rollback/retry behavior exercised without destroying failure evidence.

### Production Repair

- [ ] Roger's deployment confirmation and deployed revision recorded.
- [ ] wepp1 host/path/service preflight passed.
- [ ] Pre-repair snapshots and hashes retained for all eight runs.
- [ ] All eight runs rebuilt/rerun with exact job IDs and terminal states.
- [ ] Post-repair inputs, outputs, and summary comparison retained.
- [ ] No run was deleted, renamed, or silently partially repaired.

## Progress Notes

### 2026-09-17 22:39 UTC: Incident package scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Inspected the reporter CSV, current production artifacts, persisted NoDb state,
  the September 7 clone, and relevant source/test paths.
- Isolated three independent propagation defects.
- Defined Forest as a hard release gate and production repair as a separate,
  operator-triggered phase.
- Files added under
  `docs/work-packages/20260917_mofe_scenario_artifact_integrity/` and a discoverable
  root tracker entry.

**Blockers encountered**:

- No implementation blocker. Production mutation is intentionally gated on later
  Forest acceptance and explicit deployment confirmation.

**Next steps**:

1. Draft and independently review the canonical contract.
2. Commit the contract checkpoint before implementation.
3. Implement regressions and the bounded source correction.

**Test results**: Documentation-only scaffold. `wctl doc-lint` passed for the
root tracker and all nine package files (10 files, zero errors/warnings). The
spelling preview found no changes in the new package; it reported only preexisting
root tracker text outside this package.

### 2026-09-17 22:55 UTC: Durable validation guidance

**Agent/Contributor**: Codex

**Work completed**:

- Authored `docs/standards/generated-artifact-validation-standard.md`.
- Added first-hop links and required evidence/status fields to root guidance,
  work-package instructions, and review templates.
- Recorded the standard as canonical package guidance while leaving every runtime
  gate pending.

**Next steps**:

1. Lint and size-check the governance documentation.
2. Continue with the MOFE canonical contract checkpoint; do not begin source edits
   first.

**Test results**: all 14 changed governance/package Markdown files passed
`wctl doc-lint` with zero errors or warnings. Root onboarding remains exactly 160
lines and passed `tools/check_agents_size.sh AGENTS.md`. `wctl doc-refs` confirmed
inbound links from root agent guidance, correctness review, artifact observability,
hardening guidance, and work-package instructions. Spelling preview found only
preexisting differences in unrelated `docs/work-packages/README.md` text.

## Watch List

- **Selected-hillslope overlap**: reuse the explicit-assignment regeneration
  behavior without changing the separate selected-hillslope contract.
- **RAP precedence**: preserve current segment-specific cover behavior.
- **Soil behavior**: high severity and SBS may differ through soil generation;
  do not attribute all response differences to management files.
- **Production generations**: a failed rebuild can leave mixed files; the repair
  ledger must record failure and retry rather than infer success from existence.

## Communication Log

### 2026-09-17 22:39 UTC: Operator sequence and accountability

**Participants**: Roger and Codex
**Question/Topic**: The prior claimed fix did not survive actual artifact
inspection. Roger required a new work package, real Forest validation, operator-
owned WEPPcloud deployment, and subsequent manual repair of all Abdisa runs.
**Outcome**: The package uses exactly that sequence and does not authorize current
production mutation.
