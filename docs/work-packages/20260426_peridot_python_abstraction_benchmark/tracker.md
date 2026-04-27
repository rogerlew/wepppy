# Tracker - Peridot vs WEPPpy Python Abstraction Benchmark

> Living document tracking scope, decisions, risks, validation, and handoffs for benchmarking Peridot against the stale WEPPpy Python abstraction comparator.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-27 01:35 UTC
**Current phase**: Done
**Last updated**: 2026-04-27 02:21 UTC
**Next milestone**: Closed - use rough numbers only with the documented parity caveat
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
- [x] Package scaffold created with package brief, tracker, active ExecPlan, benchmark scope artifact, and package validation artifact (2026-04-27 01:26 UTC).
- [x] Milestone 1: Rediscovered the WEPPpy Python abstraction path and documented exact invocation settings.
- [x] Milestone 2: Selected the in-repo `feverish-lamp` TOPAZ fixture and copied inputs into isolated scratch directories.
- [x] Milestone 3: Documented reproducible Python and Peridot command transcripts.
- [x] Milestone 4: Ran smoke and parity validation; parity blocked by Python comparator failure.
- [x] Milestone 5: Closed without valid timing claims because the Python comparator failed before parity.
- [x] Milestone 6: Updated artifacts, tracker, archived ExecPlan, and root tracker with outcomes.
- [x] Post-close addendum: remediated `cummnorm_distance()` and channel GeoJSON serialization, then collected rough smoke benchmark numbers with exact parity out of scope.

## Timeline

- **2026-04-27 01:26 UTC** - Package prepared in Backlog after Peridot runtime-hardening loose ends were closed.
- **2026-04-27 01:35 UTC** - Package execution started; lifecycle moved to In Progress in the package tracker and root project tracker.
- **2026-04-27 01:39 UTC** - Package closed as Done with a Python comparator failure outcome and scoped remediation follow-up.
- **2026-04-27 02:21 UTC** - Post-close rough benchmark addendum recorded after narrow Python comparator remediation and relaxed parity requirement.

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

---

### 2026-04-27 01:39 UTC: Use lower-level Python comparator for health discovery
**Context**: The NoDb wrapper is deprecated and tied to persisted run state, while the benchmark package explicitly allowed either NoDb-level invocation or direct use of `WatershedAbstraction(topaz_wd, wat_dir)`.

**Options considered**:
1. Instantiate a copied NoDb run and force `abstraction_backend != "peridot"`.
2. Call the lower-level Python abstraction class on copied TOPAZ inputs.

**Decision**: Option 2.

**Impact**: The smoke test exercises the legacy Python abstraction code without mutating source fixtures or relying on stale NoDb paths.

---

### 2026-04-27 01:39 UTC: Close package without benchmark timing claims
**Context**: The Python comparator failed with a NumPy casting error before producing complete outputs.

**Options considered**:
1. Patch production Python abstraction code inside this benchmark package.
2. Record the failure as the package outcome and recommend a scoped remediation package.

**Decision**: Option 2.

**Impact**: The package closes with validated comparator-health evidence, but no Peridot-vs-Python performance claim.

---

### 2026-04-27 02:21 UTC: Allow rough benchmark numbers without exact parity
**Context**: The user explicitly requested `cummnorm_distance()` remediation to get rough benchmark numbers and said exact parity is not required.

**Options considered**:
1. Keep the original parity gate and refuse timing until exact output parity is established.
2. Collect rough timing after narrow comparator remediation, while labeling output differences and claim scope.

**Decision**: Option 2.

**Impact**: The rough benchmark artifact reports smoke-fixture timing ratios with explicit caveats. It does not replace a publication-grade benchmark or parity package.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Python abstraction no longer runs due to code drift or dependency drift | High | Medium | Smoke-test discovery recorded traceback; post-close remediation made the selected smoke fixture complete | Closed for smoke fixture |
| Benchmark mutates historical or production run directories | High | Low | Used copied fixture under `/tmp/peridot-python-benchmark-20260427-0138` | Closed |
| Timings are compared before output parity is checked | Medium | Medium | Parity gate blocked timing claims | Closed |
| Peridot release binaries have unclear provenance | Medium | Medium | Recorded binary path, source commit, dirty target binaries, and SHA256 values | Closed for smoke; follow-up for publication |
| In-repo fixtures are too small for meaningful performance claims | Medium | Medium | Labeled results as smoke-only; fixture-curation follow-up recommended | Closed |
| Rough numbers could be mistaken for exact parity evidence | Medium | Medium | Artifact labels exact parity as out of scope and records output-shape differences | Closed |

## Verification Checklist

### Code Quality
- [x] Any benchmark helper scripts are deterministic, isolated, and reviewed before use. No helper script was introduced.
- [x] `git diff --check` passes.
- [x] Targeted remediation regression tests pass.

### Security
- [x] Security impact triage recorded (`none`) with rationale.
- [x] Dedicated security review artifact not required unless package scope changes.
- [x] Benchmark commands do not mutate live run roots or expose secrets.

### Documentation
- [x] Package brief created.
- [x] ExecPlan created and archived under `prompts/completed/`.
- [x] Benchmark scope and hypotheses artifact created.
- [x] Package validation artifact created.
- [x] Tracker and ExecPlan progress updated during execution and archived at closure.
- [x] `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_python_abstraction_benchmark` passes.

### Testing and Benchmarking
- [x] Python comparator smoke-test result recorded.
- [x] Peridot comparator smoke-test result recorded.
- [x] Output parity artifact produced before timing claims.
- [x] Runtime/resource smoke results recorded with environment context; no valid benchmark timing claim was made.
- [x] All claims labeled as `confirmed`, `inference`, or `hypothesis`.
- [x] Rough post-remediation benchmark numbers recorded with exact parity explicitly out of scope.

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

### 2026-04-27 01:35 UTC: Execution start
**Agent/Contributor**: Codex

**Work completed**:
- Moved the package lifecycle to In Progress.
- Began Milestone 1 comparator rediscovery from the active ExecPlan.

**Blockers encountered**:
- None.

**Next steps**:
1. Inspect the legacy Python abstraction code path and Peridot wrapper contracts.
2. Search in-repo fixtures before considering copied run data.
3. Record exact invocation requirements in the discovery artifact.

**Test results**:
- Pending.

### 2026-04-27 01:39 UTC: Package closure
**Agent/Contributor**: Codex

**Work completed**:
- Rediscovered the legacy Python comparator path and Peridot TOPAZ comparator command.
- Selected and copied the in-repo `wepppy/_tests/feverish-lamp` fixture into isolated scratch directories.
- Smoke-tested Python and Peridot comparators on copied inputs.
- Recorded Python failure, Peridot smoke success, output parity blocker, and validation context in artifacts.
- Closed package without valid benchmark timing claims because the Python comparator failed before parity.
- Archived the completed ExecPlan under `prompts/completed/`.

**Blockers encountered**:
- Python comparator failure in `wepppy/topo/watershed_abstraction/support.py::cummnorm_distance()`:
  `numpy.core._exceptions._UFuncOutputCastingError: Cannot cast ufunc 'divide' output from dtype('float64') to dtype('int64') with casting rule 'same_kind'`.

**Next steps**:
1. Create a comparator-remediation work package for the NumPy casting failure and regression coverage.
2. After remediation, rerun parity before collecting benchmark timings.
3. Curate representative benchmark fixtures before publishing any broad performance claims.

**Test results**:
- Python smoke: exit `1`; traceback recorded.
- Peridot smoke: exit `0`; produced current watershed outputs.
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_python_abstraction_benchmark`: `10 files validated, 0 errors, 0 warnings`.
- `git diff --check`: passed.

### 2026-04-27 02:21 UTC: Post-close rough benchmark after remediation
**Agent/Contributor**: Codex

**Work completed**:
- Remediated the confirmed `cummnorm_distance()` NumPy casting failure by normalizing a `float64` cumulative-distance array.
- Remediated a second stale Python wrapper blocker by making channel-path coordinate transforms JSON-serializable.
- Added focused regression tests for integer distance normalization and GeoJSON coordinate list output.
- Re-ran the legacy Python comparator and Peridot comparator on fresh copied fixtures with `24` workers/threads.
- Recorded rough timing results in `artifacts/2026-04-27_rough_benchmark_after_cummnorm_remediation.md`.

**Blockers encountered**:
- Exact output parity remains out of scope for the rough benchmark. Python produced native slope files and 36 flowpath groups; Peridot produced parquet tables, slope bundles, and 614 flowpath rows.

**Next steps**:
1. Treat the rough `14.6x` smoke-fixture timing ratio as a directional signal only.
2. Build a fixture-curation/parity package before making publication-grade benchmark claims.
3. Consider a cleanup package for broader legacy Python abstraction output contract alignment if the comparator will remain supported.

**Test results**:
- `wctl run-pytest tests/topo/test_watershed_abstraction_support.py`: `2 passed, 2 warnings`.
- Rough benchmark repetitions: Python `5/5` exit `0`; Peridot `5/5` exit `0`.

## Watch List

- **Comparator health**: The Python abstraction path now completes the selected smoke fixture after two narrow fixes, but remains stale and only lightly covered.
- **Fixture provenance**: Prefer in-repo fixtures. If production-derived run data is needed, copy only minimal safe inputs into an isolated workspace and record provenance.
- **Peridot binaries**: `/home/workdir/peridot/target/release/abstract_watershed` and `wbt_abstract_watershed` are dirty in the local worktree; do not stage or rely on them without provenance notes.
- **Claim discipline**: Do not convert smoke-fixture observations into broad performance claims.

## Communication Log

### 2026-04-27 01:26 UTC: Benchmark package request
**Participants**: User, Codex
**Question/Topic**: Prepare a work package for attempting to benchmark Peridot against the WEPPpy Python-based abstraction path.
**Outcome**: Package scaffolded in Backlog with Python comparator rediscovery as the first milestone.

### 2026-04-27 02:21 UTC: Rough benchmark addendum
**Participants**: User, Codex
**Question/Topic**: Exact parity is not required; collect rough Python-vs-Peridot timing after narrow Python comparator remediation.
**Outcome**: Added `cummnorm_distance()` and channel GeoJSON serialization fixes, recorded 5-rep rough timing results, and closed the package with the smoke-fixture `14.6x` Peridot result.
