# Tracker - wepppyo3 Repositioning

> Living document tracking scope, decisions, risks, validation, and handoffs for repositioning `/workdir/wepppyo3` as WEPPpy's native kernel and interchange substrate.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-28 17:33 UTC
**Current phase**: Done
**Last updated**: 2026-04-28 17:38 UTC
**Next milestone**: None; package closed
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
- [x] Reviewed `/workdir/wepppyo3` codebase shape, release package, tests, and WEPPpy callsites.
- [x] Determined initial posture and recorded evidence artifact.
- [x] Created package scaffold and active ExecPlan.
- [x] Registered package in `PROJECT_TRACKER.md` Backlog.
- [x] Milestone 1: Rewrote README front matter around native-substrate posture.
- [x] Milestone 2: Added canonical module registry with maturity/evidence labels.
- [x] Milestone 3: Added architecture/boundary doc differentiating `wepppyo3`, Peridot, `weppcloud-wbt`, and Python orchestration.
- [x] Milestone 4: Added release/provenance doc for `release/linux/py312/wepppyo3/`.
- [x] Milestone 5: Aligned WEPPpy references and claim wording where appropriate.
- [x] Milestone 6: Validated docs and closed package.

## Timeline

- **2026-04-28 17:20 UTC** - Codebase review completed and repositioning package prepared in Backlog.
- **2026-04-28 17:38 UTC** - Package executed and closed as docs-first repositioning.

## Decisions Log

### 2026-04-28 17:20 UTC: Position wepppyo3 as native substrate
**Context**: The repository README currently describes `wepppyo3` as Rust/PyO3 extension modules for WEPPpy, but the workspace now spans production climate, raster, WEPP/SWAT interchange, roads, MOFE, SBS, and visualization paths.

**Options considered**:
1. Keep positioning as a module catalog of Rust speedups.
2. Position `wepppyo3` as WEPPpy's native kernel and interchange substrate with explicit contracts and maturity labels.

**Decision**: Option 2.

**Impact**: The repositioning should emphasize owned-stack boundaries, release provenance, and evidence-backed claims instead of presenting each module as an isolated accelerator.

---

### 2026-04-28 17:20 UTC: Keep this package docs-first
**Context**: The request is to determine posture and prepare a repositioning package, not to refactor runtime behavior.

**Options considered**:
1. Include code/package restructuring in the repositioning package.
2. Keep runtime changes out of scope and limit execution to docs and reference alignment.

**Decision**: Option 2.

**Impact**: Any release automation, module moves, public API renames, or binary provenance enforcement should be separate follow-up packages.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Existing docs oversell speedups without bounded evidence | Medium | Medium | Require claim labels and link evidence artifacts | Mitigated by `docs/claim-discipline.md` |
| Module maturity labels imply operational policy without owner agreement | Medium | Medium | Use evidence labels first; mark policy decisions as follow-up | Mitigated by descriptive registry language |
| Repositioning blurs boundaries with Peridot or `weppcloud-wbt` | Medium | Low | Add explicit boundary doc | Closed |
| Release docs expose provenance gaps | Low | High | Record gaps as follow-up; do not change release mechanics in this package | Closed as documented follow-up |
| WEPPpy worktree has unrelated dirty changes | Low | High | Restrict edits to this package and a small `PROJECT_TRACKER.md` entry | Mitigated; unrelated files untouched |

## Verification Checklist

### Documentation
- [x] Initial posture artifact created.
- [x] Active ExecPlan created.
- [x] Package registered in root tracker.
- [x] README and docs updated during execution.
- [x] `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_wepppyo3_repositioning` passes.

### Testing
- [x] No runtime tests required for posture-only changes.
- [ ] If any code or release artifact changes enter scope, run targeted `cargo test`/pytest before closure.

### Security
- [x] Security impact triage recorded (`none`).
- [x] Dedicated security artifact not required for docs-only scope.

## Progress Notes

### 2026-04-28 17:20 UTC: Package scoping and posture review
**Agent/Contributor**: Codex

**Work completed**:
- Reviewed `/workdir/wepppyo3` README, workspace manifests, release package, docs, tests, and WEPPpy callsites.
- Recorded codebase posture in `artifacts/2026-04-28_codebase_posture_review.md`.
- Created package brief, tracker, active ExecPlan, and validation artifact.
- Registered package in `PROJECT_TRACKER.md` Backlog.

**Blockers encountered**:
- None.

**Next steps**:
1. Execute the active ExecPlan.
2. Update `/workdir/wepppyo3/README.md` with a strong front-matter posture.
3. Add canonical module registry and release/provenance docs.

**Test results**:
- Initial validation was deferred until execution.

### 2026-04-28 17:38 UTC: Execution and closure
**Agent/Contributor**: Codex

**Work completed**:
- Rewrote `/workdir/wepppyo3/README.md` around the native kernel and interchange substrate posture.
- Added canonical docs:
  - `/workdir/wepppyo3/docs/module-registry.md`
  - `/workdir/wepppyo3/docs/architecture-and-boundaries.md`
  - `/workdir/wepppyo3/docs/release-provenance.md`
  - `/workdir/wepppyo3/docs/claim-discipline.md`
- Aligned WEPPpy references in `ARCHITECTURE.md`, `readme.md`, `wepppy/README.md`, and `docs/standards/dependency-evaluation-standard.md`.
- Moved root tracker entry from Backlog to Done.
- Archived the ExecPlan under `prompts/completed/`.

**Blockers encountered**:
- None.

**Validation results**:
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260428_wepppyo3_repositioning`: passed.
- `git diff --check` in `/workdir/wepppy`: passed.
- `git diff --check` in `/workdir/wepppyo3`: passed.
- Manual relative-link validation for changed `wepppyo3` Markdown: passed.
- Runtime tests were not run because this package changed documentation only.

## Watch List

- **Release path**: `/workdir/wepppyo3/release/linux/py312/wepppyo3/` is canonical today; do not alter binaries in this package.
- **Version provenance**: package `__version__` and crate versions are not enough to identify source/build provenance for every `.so`.
- **Boundary clarity**: Peridot owns watershed graph abstraction; `wepppyo3.watershed_abstraction` currently owns specific Python-callable helper kernels such as MOFE map assignment.
- **Dirty WEPPpy tree**: unrelated RQ cache-guard work is already dirty; avoid staging or modifying those files.

## Communication Log

### 2026-04-28 17:20 UTC: User posture request
**Participants**: User, Codex
**Question/Topic**: Review `/workdir/wepppyo3` and prepare a repositioning work package.
**Outcome**: Determined native-substrate posture and scaffolded docs-first repositioning package.
