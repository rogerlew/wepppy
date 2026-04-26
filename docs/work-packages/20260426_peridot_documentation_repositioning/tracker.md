# Tracker - Peridot Documentation Repositioning and Adoption Visibility

> Living document tracking progress, decisions, risks, and evidence for the Peridot documentation revision package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-26 21:20 UTC
**Current phase**: Complete
**Last updated**: 2026-04-26 22:36 UTC
**Next milestone**: Handoff
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] None.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-26 21:20 UTC).
- [x] Authored package brief with scope, success criteria, dependencies, and references (2026-04-26 21:20 UTC).
- [x] Authored active ExecPlan for implementation sequencing and validation gates (2026-04-26 21:23 UTC).
- [x] Registered package in root `PROJECT_TRACKER.md` backlog (2026-04-26 21:24 UTC).
- [x] Incorporated user directional guidance for GPT-5.5 into package/ExecPlan plus notes artifact (2026-04-26 21:27 UTC).
- [x] Audited Peridot runtime anchors for outputs, flags, schemas, representative-flowpath behavior, and CLI error boundaries (2026-04-26 21:42 UTC).
- [x] Rewrote Peridot `README.md` front matter around category-shift framing, replacement scope, canonical links, and communication kit (2026-04-26 21:44 UTC).
- [x] Added Peridot canonical docs for output contract, benchmarks, migration, and operations (2026-04-26 21:44 UTC).
- [x] Updated WEPPpy references to point to canonical Peridot docs and apply benchmark claim discipline (2026-04-26 21:45 UTC).
- [x] Added package claim-provenance and validation-summary artifacts (2026-04-26 21:45 UTC).
- [x] Updated `PROJECT_TRACKER.md` lifecycle from Backlog to Done (2026-04-26 21:45 UTC).
- [x] Ran requested WEPPpy doc-lint and Peridot manual link/path validation (2026-04-26 21:49 UTC).
- [x] Ran additional changed-doc lint for WEPPpy Peridot reference updates and fixed a dead `API_REFERENCE.md` link in touched `wepppy/README.md` (2026-04-26 21:50 UTC).
- [x] Addressed post-implementation review findings for sub-field inputs, historical culvert CSV wording, and `discha.vrt` README coverage (2026-04-26 22:36 UTC).

## Timeline

- **2026-04-26 21:20 UTC** - Package initialized and scoped from user request.
- **2026-04-26 21:23 UTC** - Active ExecPlan created and linked.
- **2026-04-26 21:24 UTC** - Root tracker entry added.
- **2026-04-26 21:27 UTC** - Directional messaging guidance codified into package objectives and ExecPlan acceptance.
- **2026-04-26 21:42 UTC** - Execution resumed; Peridot source/runtime anchors audited.
- **2026-04-26 21:44 UTC** - Peridot README and four canonical docs authored.
- **2026-04-26 21:45 UTC** - WEPPpy cross-references aligned and package closure docs updated.
- **2026-04-26 21:49 UTC** - Validation completed and recorded in package artifact.
- **2026-04-26 21:50 UTC** - Additional changed-doc lint completed; dead `API_REFERENCE.md` link removed from touched `wepppy/README.md`.
- **2026-04-26 22:36 UTC** - Review findings remediated and recorded in review-remediation artifact.

## Decisions Log

### 2026-04-26 21:20 UTC: Treat this as a cross-repo documentation package anchored in WEPPpy tracking
**Context**: User requested a work package for Peridot documentation revision while active workspace context is WEPPpy.

**Options considered**:
1. Create planning docs only in `/home/workdir/peridot`.
2. Create and track the package under WEPPpy `docs/work-packages/` and execute docs edits in Peridot as a linked external repo.

**Decision**: Option 2.

**Impact**: Planning/coordination artifacts stay discoverable for WEPPpy agents while implementation edits target Peridot documentation files.

---

### 2026-04-26 21:20 UTC: Focus first on positioning and contract clarity before deep architecture narrative
**Context**: Current gap is under-advertising production relevance and incomplete contract-level guidance.

**Options considered**:
1. Lead with deep internal architecture documentation.
2. Lead with adoption-facing docs: value proposition, contracts, migration, operations, benchmark method.

**Decision**: Option 2.

**Impact**: Early milestones prioritize high-leverage docs that improve onboarding and external/internal perception fastest.

---

### 2026-04-26 21:27 UTC: Treat messaging as mental-model migration, not cosmetic copy refresh
**Context**: User provided directional guidance that Peridot is being misclassified as a modernized replacement rather than an abstraction-layer shift.

**Options considered**:
1. Keep existing package framing and only adjust prose tone.
2. Update package scope/acceptance criteria so docs must explicitly reset legacy TOPAZ/TOP2WEPP mental models and include communication kit artifacts.

**Decision**: Option 2.

**Impact**: Execution requires explicit category-shift framing, legacy-vs-current paradigm comparison, and claim-discipline evidence notes.

---

### 2026-04-26 21:44 UTC: Correct the README CSV mismatch as documentation, not runtime behavior
**Context**: Peridot source audit showed current watershed CLI paths write Parquet tables and generated manifests, while the old README still advertised watershed CSV compatibility outputs.

**Options considered**:
1. Change runtime to emit CSV files again.
2. Document the current Parquet-first CLI contract and record CSV expectations as historical/compatibility behavior.

**Decision**: Option 2.

**Impact**: Scope remains docs-first. The output contract and migration guide now tell downstream readers to treat watershed CSV requirements as historical or WEPPpy compatibility behavior, not current direct Peridot CLI output.

---

### 2026-04-26 21:44 UTC: Document CLI error-boundary risk as an operations gate and follow-up package
**Context**: `abstract_watershed` and `wbt_abstract_watershed` entrypoints currently discard the underlying abstraction `Result`, so some write-stage failures may not propagate through process exit status.

**Options considered**:
1. Modify CLI runtime behavior inside this package.
2. Keep this package documentation-only and require post-run output validation in operations docs.

**Decision**: Option 2.

**Impact**: Operations docs now state that required outputs and the generated manifest are authoritative success evidence. Runtime hardening is recorded as a follow-up recommendation.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Docs claims diverge from runtime behavior | High | Medium | Validated claims against Rust source and recorded provenance artifact | Mitigated |
| Performance claims asserted without reproducible methodology | Medium | Medium | Added benchmark discipline doc and softened WEPPpy speedup language | Mitigated |
| Cross-repo edits drift between Peridot and WEPPpy references | Medium | Medium | Updated both repos in one execution window and linked canonical docs | Mitigated |
| Watershed CLI may return success despite some write-stage errors | Medium | Medium | Documented output validation requirement and follow-up runtime hardening | Follow-up recommended |
| Sub-field `field_flowpaths.csv` has duplicate `topaz_id` header | Low | Medium | Documented current behavior and recommended schema cleanup follow-up | Follow-up recommended |

## Verification Checklist

### Documentation
- [x] Peridot README front section rewritten with clear production-role statement.
- [x] New contract/benchmark/migration/operations docs added and linked.
- [x] WEPPpy-facing references updated to canonical Peridot docs where appropriate.
- [x] Markdown lint/check pass for changed docs.

### Consistency
- [x] Documented outputs/flags validated against current Peridot code.
- [x] Known behavior/docs mismatch corrected or explicitly marked with follow-up note.
- [x] Performance claims include source and method context.

### Security
- [x] Security impact triage recorded (`none`).
- [x] Dedicated security artifact requirement assessed (`no`).

## Progress Notes

### 2026-04-26 21:20 UTC: Package creation and initial scoping
**Agent/Contributor**: Codex

**Work completed**:
- Created new work package `20260426_peridot_documentation_repositioning`.
- Authored `package.md` with objectives and scoped deliverables focused on Peridot documentation relevance and contract clarity.
- Authored this tracker with task board, decisions, and risk model.
- Authored active ExecPlan for milestone-by-milestone execution.
- Added package entry to root `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Confirm package title/scope wording with user.
2. Execute Milestone 1 and Milestone 2 documentation edits in `/home/workdir/peridot`.
3. Capture claim evidence artifacts as changes are made.

**Test results**:
- Planning/docs scaffolding only; runtime tests not applicable yet.

### 2026-04-26 21:24 UTC: ExecPlan and root tracker registration completion
**Agent/Contributor**: Codex

**Work completed**:
- Added active execution plan at `prompts/active/peridot_documentation_repositioning_execplan.md`.
- Registered this package in root `PROJECT_TRACKER.md` backlog.
- Updated tracker timestamps/status to match completed planning state.

**Blockers encountered**:
- None.

**Next steps**:
1. Start Milestone 1 Peridot README restructuring.
2. Author contract, benchmark, migration, and operations docs in Peridot.
3. Align WEPPpy cross-references to canonical Peridot docs.

**Test results**:
- Planning/docs updates only; runtime tests not applicable.

### 2026-04-26 21:27 UTC: Directional guidance integration
**Agent/Contributor**: Codex

**Work completed**:
- Updated `package.md` objectives/success criteria to encode category-shift framing requirements.
- Updated active ExecPlan to require legacy-vs-current paradigm framing, communication kit outputs, and claim discipline.
- Added notes artifact: `notes/2026-04-26_gpt55_directional_guidance.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute Peridot README rewrite using new framing constraints.
2. Build contract/migration/operations/benchmark docs aligned to communication kit.
3. Capture `confirmed`/`inference`/`hypothesis` evidence labeling in artifacts.

**Test results**:
- Planning/docs updates only; runtime tests not applicable.

### 2026-04-26 21:45 UTC: Documentation implementation and closure prep
**Agent/Contributor**: Codex

**Work completed**:
- Rewrote `/home/workdir/peridot/README.md` to foreground why Peridot matters, category-shift framing, replacement boundaries, canonical docs, and the communication kit.
- Added `/home/workdir/peridot/docs/contracts/watershed-output-contract.md` with Parquet-first watershed outputs, schemas, flag behavior, sub-field outputs, and current error-boundary notes.
- Added `/home/workdir/peridot/docs/benchmarks.md` with claim labels, benchmark methodology, figure specification, and metric definitions.
- Added `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md` with migration scope, parity expectations, intentional differences, and evidence notes.
- Added `/home/workdir/peridot/docs/operations.md` with preflight, commands, post-run validation, failure signatures, and follow-up escalation boundaries.
- Updated WEPPpy Peridot references in `wepppy/README.md`, St. Joe procurement docs, query/data-table notes, output-scope contract, dependency standard, and culvert integration docs.
- Created package artifacts for claim provenance and validation summary.
- Updated `PROJECT_TRACKER.md` lifecycle to Done.

**Blockers encountered**:
- None.

**Next steps**:
1. Run requested `wctl doc-lint` validation.
2. Perform Peridot manual link/path validation because no Peridot markdown tooling is present.
3. Update validation artifact with final command results.

**Test results**:
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning` pending at this checkpoint.

### 2026-04-26 21:49 UTC: Validation completion
**Agent/Contributor**: Codex

**Work completed**:
- Ran requested WEPPpy package/root tracker doc-lint.
- Ran manual Peridot documentation path and local-link validation because no Peridot markdown/doc tooling exists.
- Ran additional changed-file doc-lint for WEPPpy Peridot reference updates.
- Removed a pre-existing dead `API_REFERENCE.md` link from touched `wepppy/README.md`.
- Ran `uk2us` spelling-normalization preview for changed WEPPpy package docs; no diff was produced.
- Updated validation artifact with command results.

**Blockers encountered**:
- None.

**Next steps**:
1. Handoff package with residual runtime/schema follow-up recommendations.

**Test results**:
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning` -> `7 files validated, 0 errors, 0 warnings`.
- Additional changed-doc lint for seven WEPPpy docs -> `7 files validated, 0 errors, 0 warnings` after dead-link fix.
- Peridot manual path/local-link validation -> pass.

### 2026-04-26 22:36 UTC: Review remediation
**Agent/Contributor**: Codex

**Work completed**:
- Corrected Peridot output contract so `sub_fields_abstraction` input requirements do not imply `netw.tsv` is required.
- Updated Peridot README to state representative-flowpath mode accepts `discha.tif` or `discha.vrt`.
- Added historical-contract notes to the completed culvert integration plan where older `flowpaths.csv` wording remains as historical implementation context.
- Added review remediation artifact at `artifacts/2026-04-26_review_remediation.md`.
- Reran package doc-lint, culvert plan doc-lint, and Peridot manual path/local-link validation after remediation.

**Blockers encountered**:
- None.

**Next steps**:
1. Handoff.

**Test results**:
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning` -> `8 files validated, 0 errors, 0 warnings`.
- `wctl doc-lint --path docs/culvert-at-risk-integration/weppcloud-integration.plan.md` -> `1 files validated, 0 errors, 0 warnings`.
- Peridot manual path/local-link validation -> pass.

## Communication Log

### 2026-04-26 21:20 UTC: User request intake
**Participants**: User, Codex
**Question/Topic**: "Put together a work-package to revise peridot documentation."
**Outcome**: Work package scaffolded with package brief, tracker, active ExecPlan, and root tracker registration.

### 2026-04-26 21:27 UTC: Directional guidance update
**Participants**: User, Codex
**Question/Topic**: "Please incorporate this directional guidance for GPT 5.5."
**Outcome**: Category-shift framing and communication-kit requirements were codified in package/ExecPlan/tracker and linked note artifact.
