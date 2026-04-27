# Tracker - Peridot vs WEPPpy Python Abstraction Benchmark

> Living document tracking scope, decisions, risks, validation, and handoffs for benchmarking Peridot against the stale WEPPpy Python abstraction comparator.

## Quick Status

**Timezone**: UTC
**Started**: Not started; package scoped 2026-04-27 01:26 UTC
**Current phase**: Backlog
**Last updated**: 2026-04-27 01:26 UTC
**Next milestone**: Milestone 1 - rediscover and smoke-test the WEPPpy Python abstraction path
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Milestone 1: Rediscover the WEPPpy Python abstraction path and document exact invocation settings.
- [ ] Milestone 2: Select safe benchmark fixtures and copy inputs into isolated working directories.
- [ ] Milestone 3: Build or document a reproducible benchmark harness for Python and Peridot runs.
- [ ] Milestone 4: Run smoke/parity validation before timing comparisons.
- [ ] Milestone 5: Collect timing/resource measurements and classify claims.
- [ ] Milestone 6: Update artifacts, tracker, ExecPlan, and root tracker with outcomes.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Package scaffold created with package brief, tracker, active ExecPlan, benchmark scope artifact, and package validation artifact (2026-04-27 01:26 UTC).

## Timeline

- **2026-04-27 01:26 UTC** - Package prepared in Backlog after Peridot runtime-hardening loose ends were closed.

## Decisions Log

### 2026-04-27 01:26 UTC: Treat WEPPpy Python abstraction as a stale comparator, not a trusted oracle
**Context**: The requested benchmark target is the WEPPpy Python-based abstraction, and it has not been used in a while.

**Options considered**:
1. Benchmark Peridot timings immediately against whatever Python command can be made to run.
2. First rediscover and smoke-test the Python path, then use it as a comparator only after basic output checks pass.

**Decision**: Option 2.

**Impact**: The first milestone is health discovery. If Python fails, the package produces a failure artifact and remediation recommendation instead of invalid timing claims.

---

### 2026-04-27 01:26 UTC: Start with TOPAZ-derived abstraction
**Context**: The legacy Python path is `_topaz_abstract_watershed()`, which constructs `WatershedAbstraction` instances over TOPAZ outputs.

**Options considered**:
1. Compare WBT-derived Peridot outputs directly to the Python path.
2. Start with TOPAZ-derived abstraction where the Python comparator was originally designed to run.

**Decision**: Option 2.

**Impact**: WBT-derived benchmarking is a later extension unless a separate Python comparator for WBT is identified.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Python abstraction no longer runs due to code drift or dependency drift | High | Medium | Make smoke-test discovery Milestone 1 and record traceback before benchmarking | Open |
| Benchmark mutates historical or production run directories | High | Low | Require copied fixtures or isolated temp dirs before running either comparator | Open |
| Timings are compared before output parity is checked | Medium | Medium | Make parity checks a gate before performance claims | Open |
| Peridot release binaries have unclear provenance | Medium | Medium | Record binary path, source commit, and whether binaries are preexisting dirty artifacts | Open |
| In-repo fixtures are too small for meaningful performance claims | Medium | Medium | Label small-fixture results as smoke-only and create fixture-curation follow-up if needed | Open |

## Verification Checklist

### Code Quality
- [ ] Any benchmark helper scripts are deterministic, isolated, and reviewed before use.
- [ ] `git diff --check` passes.

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security review artifact not required unless package scope changes.
- [ ] Benchmark commands do not mutate live run roots or expose secrets.

### Documentation
- [x] Package brief created.
- [x] Active ExecPlan created.
- [x] Benchmark scope and hypotheses artifact created.
- [x] Package validation artifact created.
- [ ] Tracker and ExecPlan progress updated during execution.
- [ ] `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_python_abstraction_benchmark` passes.

### Testing and Benchmarking
- [ ] Python comparator smoke-test result recorded.
- [ ] Peridot comparator smoke-test result recorded.
- [ ] Output parity artifact produced before timing claims.
- [ ] Runtime/resource results recorded with environment context.
- [ ] All claims labeled as `confirmed`, `inference`, or `hypothesis`.

## Progress Notes

### 2026-04-27 01:26 UTC: Package scoping
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold under `docs/work-packages/20260426_peridot_python_abstraction_benchmark/`.
- Authored package brief, tracker, active ExecPlan, and benchmark scope/hypotheses artifact.
- Registered the package in `PROJECT_TRACKER.md` Backlog.
- Scoped the benchmark target as the WEPPpy Python abstraction path and recorded that it must be rediscovered before use.

**Blockers encountered**:
- None.

**Next steps**:
1. Read `wepppy/topo/watershed_abstraction/watershed_abstraction.py`, `wepppy/nodb/core/watershed.py`, and `wepppy/nodb/core/watershed_mixins.py` to identify the exact Python comparator path.
2. Locate or curate a safe small fixture that can run TOPAZ-derived Python abstraction without mutating source runs.
3. Run Python and Peridot smoke tests and record output parity before timing.

**Test results**:
- Pending package doc-lint after final root tracker update.

## Watch List

- **Comparator health**: The Python abstraction path may fail before benchmarking starts; treat that as a valid package outcome.
- **Fixture provenance**: Prefer in-repo fixtures. If production-derived run data is needed, copy only minimal safe inputs into an isolated workspace and record provenance.
- **Peridot binaries**: `/home/workdir/peridot/target/release/abstract_watershed` and `wbt_abstract_watershed` are dirty in the local worktree; do not stage or rely on them without provenance notes.
- **Claim discipline**: Do not convert smoke-fixture observations into broad performance claims.

## Communication Log

### 2026-04-27 01:26 UTC: Benchmark package request
**Participants**: User, Codex
**Question/Topic**: Prepare a work package for attempting to benchmark Peridot against the WEPPpy Python-based abstraction path.
**Outcome**: Package scaffolded in Backlog with Python comparator rediscovery as the first milestone.
