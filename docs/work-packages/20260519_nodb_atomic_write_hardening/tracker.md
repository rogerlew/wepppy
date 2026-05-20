# Tracker - NoDb Atomic Write Replace Hardening

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-05-20 03:42 UTC  
**Current phase**: Closed; accepted waiver documented  
**Last updated**: 2026-05-20 05:36 UTC  
**Next milestone**: Archive package in normal tracker hygiene cycle  
**Operational risk level**: `high`  
**Security impact**: `low`  
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
- [x] Work package scaffolded (`package.md`, `tracker.md`, active ExecPlan path planned) (2026-05-20 03:42 UTC).
- [x] Added package entry to `PROJECT_TRACKER.md` Backlog with scoped next steps (2026-05-20 03:42 UTC).
- [x] Authored active ExecPlan (`prompts/active/nodb_atomic_write_hardening_execplan.md`) (2026-05-20 03:42 UTC).
- [x] Dispatched `reviewer` sub-agent and integrated findings into package docs/tracker state (2026-05-20 03:48 UTC).
- [x] Published reviewer disposition artifact (`artifacts/20260520_reviewer_disposition.md`) (2026-05-20 03:48 UTC).
- [x] Moved package from Backlog to In Progress in `PROJECT_TRACKER.md` for lifecycle consistency (2026-05-20 03:48 UTC).
- [x] Added iterative review rollup artifact template (`artifacts/20260520_iterative_review_rollup.md`) (2026-05-20 04:30 UTC).
- [x] Re-ran doc lint after high-risk iterative-loop updates (`6 files validated, 0 errors, 0 warnings`) (2026-05-20 04:30 UTC).
- [x] Authored execution prompt with mandatory iterative review/disposition loop (`prompts/active/execute_nodb_atomic_write_hardening_prompt.md`) (2026-05-20 04:33 UTC).
- [x] Implemented atomic temp-file write + `os.replace` persistence path with parent-directory fsync warnings and signature-safe failure handling in `wepppy/nodb/base.py` (2026-05-20 05:05 UTC).
- [x] Added contention/failure-path regressions in `tests/nodb/test_base_boundary_characterization.py` (2026-05-20 05:11 UTC).
- [x] Completed iterative `reviewer` + `qa_reviewer` remediation loop to zero unresolved High/Medium findings (2026-05-20 05:19 UTC).
- [x] Ran targeted and broad NoDb validation; recorded unrelated baseline blocker (`tests/nodb/test_ron_fetch_dem_copernicus.py`) as waiver evidence (2026-05-20 05:20 UTC).

## Timeline

- **2026-05-20 03:42 UTC** - Package created from production incident follow-up focused on suggestion `1` (atomic NoDb writes only).
- **2026-05-20 03:42 UTC** - Scope and success criteria frozen; non-goals documented to prevent scope creep.
- **2026-05-20 03:48 UTC** - Reviewer findings integrated: lifecycle alignment, explicit hardening gates, and living-document freshness corrections.
- **2026-05-20 03:48 UTC** - Risk posture elevated to high; iterative review/disposition-until-verified loop mandated by operator direction.
- **2026-05-20 04:30 UTC** - Iterative review rollup artifact created and post-update doc lint gate passed clean.
- **2026-05-20 04:33 UTC** - Execution prompt authored to run the package with mandatory iterative reviewer/qa_reviewer closure loop.
- **2026-05-20 05:05 UTC** - Atomic write implementation landed with mode preservation and signature-safe replace-failure behavior.
- **2026-05-20 05:11 UTC** - Added regression coverage for atomic contention success path, legacy truncate deficiency, replace failure retry safety, mode semantics, and parent-dir fsync-failure commit semantics.
- **2026-05-20 05:19 UTC** - Final reviewer and qa_reviewer pass reported zero unresolved High/Medium findings.
- **2026-05-20 05:20 UTC** - Broad `tests/nodb` run confirmed unchanged unrelated baseline failure in `test_ron_fetch_dem_copernicus`; package-specific validations remain green.

## Decisions Log

### 2026-05-20 03:42 UTC: Scope this package to atomic write replacement only
**Context**: The user selected suggestion `1` from the hardening options after incident triage.

**Options considered**:
1. Bundle atomic write, decode retries, and Omni caller retries into one package.
2. Deliver atomic write hardening as a single focused package, defer retries to follow-ups.

**Decision**: Option 2.

**Impact**: Keeps this package small and verifiable while preserving flexibility for separate retry-layer design decisions.

### 2026-05-20 03:48 UTC: Treat package as high operational risk and require iterative review closure
**Context**: Operator direction is to treat this persistence-path change as high risk and require iterative review/disposition until fixes are verified.

**Options considered**:
1. Keep a single-pass review gate (`reviewer` once + `qa_reviewer` once).
2. Require repeated review/disposition/remediation cycles with rerun evidence until no unresolved High/Medium findings remain.

**Decision**: Option 2.

**Impact**: Increases implementation rigor for a production-shared persistence path and makes closure evidence stronger and auditable.

## Risks and Issues

| Risk | Severity | Likelihood | Owner | Mitigation | Status |
|------|----------|------------|-------|------------|--------|
| Atomic replace path accidentally weakens stale-write guards | High | Medium | Codex | Preserve and extend stale-writer boundary tests in `tests/nodb/test_base_boundary_characterization.py` plus iterative review closure | Mitigated |
| Directory fsync behavior diverges across filesystems and causes flaky tests | Medium | Medium | Codex | Keep tests contract-focused (no empty payload visibility) and avoid brittle timestamp assumptions; require rerun evidence each review round | Mitigated |
| Scope creep into retry layers slows delivery | Medium | Medium | Codex | Explicitly defer retry work to follow-up package(s) | Mitigated |
| Review loop exits with unresolved material findings | High | Low | Codex | Do not close package until both `reviewer` and `qa_reviewer` report zero unresolved High/Medium findings | Mitigated |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**:
  - Wepp1 incident shows transient `JSONDecodeError` in `getInstance()` during concurrent Omni contrast completion.
  - Current write path uses in-place truncate/write, exposing a reader race window.
- **Post-change health signals**:
  - No reader-visible empty/partial payload in targeted race regressions.
  - Existing lock/signature tests remain green.
- **Danger signals observed**:
  - Any new test that passes only by timing luck instead of contract invariants.
- **Temporary callus register**: none.
- **Softening experiments**: none yet.

## Verification Checklist

### Code Quality
- [x] `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1` passes.
- [x] Any newly added targeted NoDb race test module passes.
- [x] Pre-handoff sanity gate `wctl run-pytest tests --maxfail=1` passes, or blocker/waiver is explicitly documented.
- [x] No broad-exception regressions in touched files.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required.
- [x] Residual risks captured at closure.

### Documentation
- [x] Package docs initialized (`package.md`, `tracker.md`).
- [x] Active ExecPlan authored and maintained in `prompts/active/`.
- [x] Review disposition artifact(s) added under `artifacts/` (`reviewer` + `qa_reviewer`).
- [x] `PROJECT_TRACKER.md` synchronized at closure.

### Testing
- [x] Regression coverage includes atomic-write read-safety boundary.
- [x] Existing stale-writer signature tests still pass.
- [x] Focused validation commands/results recorded in tracker notes.
- [x] Independent `reviewer` and `qa_reviewer` findings are dispositioned with artifact links for each iteration round.
- [x] Final review round confirms zero unresolved High/Medium findings and verified fixes.

## Progress Notes

### 2026-05-20 03:42 UTC: Package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Created package scope docs for atomic write replacement hardening.
- Added backlog entry in `PROJECT_TRACKER.md`.
- Captured incident signature and explicit non-goals.

**Blockers encountered**:
- None.

**Next steps**:
- Begin Milestone 1 implementation in `wepppy/nodb/base.py`.
- Add/extend targeted boundary tests in `tests/nodb/test_base_boundary_characterization.py`.
- Run targeted + full-suite gates, then complete independent `qa_reviewer` pass and artifact updates.

**Test results**: Not run (docs-only session).

### 2026-05-20 03:48 UTC: Reviewer findings integrated
**Agent/Contributor**: Codex

**Work completed**:
- Dispatched `reviewer` sub-agent for package/ExecPlan critique.
- Integrated all medium and low documentation/process findings:
  - aligned lifecycle state by moving package entry to In Progress in `PROJECT_TRACKER.md`,
  - added required hardening gates (full-suite sanity + independent `qa_reviewer` gate),
  - refreshed stale living-document checklist and next-step entries,
  - added explicit risk ownership to the risk register,
  - tightened success-criterion verification language for fsync evidence.
- Recorded reviewer disposition artifact path for traceability.

**Blockers encountered**:
- None.

**Next steps**:
- Implement atomic write replacement in `NoDbBase.dump()`.
- Add/extend targeted NoDb boundary tests.
- Execute targeted and full-suite validations, then complete `qa_reviewer` disposition.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260519_nodb_atomic_write_hardening --path PROJECT_TRACKER.md` -> `4 files validated, 0 errors, 0 warnings`.

### 2026-05-20 04:30 UTC: High-risk iterative review mandate added
**Agent/Contributor**: Codex

**Work completed**:
- Updated package/tracker/ExecPlan and in-progress tracker summary to treat this package as high risk operationally.
- Added explicit iterative review loop requirements:
  - run `reviewer` and `qa_reviewer`,
  - disposition findings,
  - remediate,
  - rerun validation,
  - repeat until both reviewers report no unresolved High/Medium findings.

**Blockers encountered**:
- None.

**Next steps**:
- Proceed with implementation under iterative review gates.
- Capture each review/remediation round in artifact updates and tracker notes.

**Test results**:
- `wctl doc-lint --path docs/work-packages/20260519_nodb_atomic_write_hardening --path PROJECT_TRACKER.md` -> `6 files validated, 0 errors, 0 warnings`.

### 2026-05-20 04:33 UTC: Execution prompt authored
**Agent/Contributor**: Codex

**Work completed**:
- Added execution prompt:
  - `prompts/active/execute_nodb_atomic_write_hardening_prompt.md`
- Prompt includes:
  - strict scope boundary (atomic writes only),
  - mandatory iterative `reviewer` + `qa_reviewer` loop,
  - remediation and rerun-evidence requirement per round,
  - explicit validation gate commands and waiver policy.

**Blockers encountered**:
- None.

**Next steps**:
- Use the new execute prompt to drive implementation and iterative review rounds.

**Test results**:
- Docs-only gate pending rerun after prompt addition.

### 2026-05-20 05:20 UTC: Implementation, validation, and iterative review closure
**Agent/Contributor**: Codex

**Work completed**:
- Implemented atomic temp-file NoDb writes in `NoDbBase.dump()` with:
  - `os.replace` swap semantics,
  - parent directory fsync as warning-only durability signal post-commit,
  - pre-commit signature staging to avoid in-memory stale-signature poisoning on replace failure,
  - mode preservation for existing files and umask-derived mode for first-create writes.
- Added/updated boundary tests covering:
  - atomic-read contention safety,
  - legacy truncate race deficiency (`JSONDecodeError` characterization),
  - replace-failure cleanup + retry safety,
  - mode preservation and initial-create mode behavior,
  - post-replace parent-dir fsync failure semantics.
- Ran iterative review/disposition loops until both `reviewer` and `qa_reviewer` reported zero unresolved High/Medium findings.

**Blockers encountered**:
- Unrelated baseline failure outside this package scope:
  - `tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`
  - `AttributeError: 'Ron' object has no attribute '_cellsize'` in `wepppy/nodb/core/ron.py`.

**Next steps**:
- Track unrelated Ron baseline failure in a separate follow-up package if prioritised.

**Test results**:
- `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1` -> `22 passed`.
- `wctl run-pytest tests/nodb --maxfail=1` -> `1 failed, 1009 passed, 23 skipped`; failing test is unrelated Ron baseline listed above.
- `wctl run-pytest tests --maxfail=1` -> `1 failed, 2124 passed, 41 skipped`; failing test remains the same unrelated Ron baseline listed above.

### 2026-05-20 05:31 UTC: NFS context alignment refinement
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed `docs/infrastructure/ui-rcds-nfs-vs-dev-nfs.md` and aligned atomic-write characterization with documented NFS incident semantics.
- Updated `_read_process_umask()` fallback to avoid runtime umask toggling in concurrent worker processes.
- Tightened parent-dir fsync failure test to explicitly simulate `OSError(errno.ESTALE, "Stale file handle")` after replace commit.

**Blockers encountered**:
- None.

**Next steps**:
- Await operator merge/waiver decision for unrelated Ron baseline failure.

**Test results**:
- `wctl run-pytest tests/nodb/test_base_boundary_characterization.py --maxfail=1` -> `22 passed`.

### 2026-05-20 05:36 UTC: Operator close-out + waiver acceptance
**Agent/Contributor**: Codex

**Work completed**:
- Operator accepted waiver for unrelated baseline failure in:
  - `tests/nodb/test_ron_fetch_dem_copernicus.py::test_fetch_dem_uses_copernicus_backend_when_scheme_is_copernicus`
  - `AttributeError: 'Ron' object has no attribute '_cellsize'` (`wepppy/nodb/core/ron.py`)
- Marked package status closed and updated success criteria checkboxes in `package.md`.
- Prepared lifecycle transition in `PROJECT_TRACKER.md` from In Progress to Done with waiver context.

**Blockers encountered**:
- None (waiver accepted by operator).

**Next steps**:
- None for this package.

**Test results**:
- No new runtime tests required for close-out metadata update.
