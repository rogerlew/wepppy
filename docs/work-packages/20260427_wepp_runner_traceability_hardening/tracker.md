# Tracker - WEPP Runner Traceability Hardening (Hillslope + Watershed)

> Living document tracking progress, decisions, risks, and validation for runner traceability hardening.

## Quick Status

**Timezone**: UTC
**Started**: 2026-04-27 19:15 UTC
**Current phase**: Done
**Last updated**: 2026-04-27 20:12 UTC
**Next milestone**: Observe production signal quality during the 14-day post-deploy window
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- None.

### In Progress
- None.

### Blocked
- None.

### Done
- [x] Work-package scaffold created (`package.md`, `tracker.md`, active ExecPlan directories) (2026-04-27 19:15 UTC).
- [x] Scope boundary documented: flowpath and single-storm methods explicitly excluded (2026-04-27 19:15 UTC).
- [x] Single-rollout decision recorded: instrumentation + watchdog ship together (2026-04-27 19:15 UTC).
- [x] Active ExecPlan authored at `prompts/active/wepp_runner_traceability_hardening_execplan.md` (2026-04-27 19:18 UTC).
- [x] Root tracker backlog entry added in `PROJECT_TRACKER.md` (2026-04-27 19:18 UTC).
- [x] Canonical watershed startup trace fields implemented (`runs_dir`, `run_file`, `err_file`, `cmd`, `attempt=1/1`) (2026-04-27 19:26 UTC).
- [x] Cached binary identity helper implemented and wired to `run_hillslope` + `run_watershed` (2026-04-27 19:26 UTC).
- [x] Linux best-effort bounded D-state watchdog implemented and wired to in-scope runners (2026-04-27 19:26 UTC).
- [x] Watershed close-path diagnostics classify stale-handle/IO close failures and preserve raised exceptions (2026-04-27 19:26 UTC).
- [x] Targeted `tests/wepp_runner/` regression coverage added for startup trace, provenance fields/fallbacks, watchdog behavior, and close diagnostics (2026-04-27 19:26 UTC).
- [x] Runner docs updated in `wepp_runner/AGENTS.md` with traceability fields and watchdog env vars (2026-04-27 19:27 UTC).
- [x] Root tracker moved package through lifecycle to Done (2026-04-27 19:27 UTC).
- [x] ExecPlan archived under `prompts/completed/` with closure outcome notes (2026-04-27 19:29 UTC).
- [x] Documentation lint passed for touched docs (2026-04-27 19:29 UTC).
- [x] Patch hygiene passed (`git diff --check`) (2026-04-27 19:29 UTC).
- [x] Post-closure `reviewer` + `qa_reviewer` findings dispositioned with regression coverage (2026-04-27 19:41 UTC).
- [x] Post-closure operator addendum completed: `wepp_260427` release build + vendoring + dirty include guidance docs (2026-04-27 20:07 UTC).
- [x] Dispatched `reviewer` + `qa_reviewer`; dispositioned findings for release addendum handoff (2026-04-27 20:12 UTC).

## Timeline

- **2026-04-27 19:15 UTC** - Package created and scoped from incident follow-up request.
- **2026-04-27 19:15 UTC** - Tracker and package brief drafted; active ExecPlan queued.
- **2026-04-27 19:18 UTC** - Active ExecPlan finalized and package registered in root backlog.
- **2026-04-27 19:26 UTC** - Runner instrumentation and targeted regression tests implemented.
- **2026-04-27 19:27 UTC** - Targeted and broader requested pytest gates passed; docs and lifecycle closure updated.
- **2026-04-27 19:29 UTC** - ExecPlan archived to `prompts/completed/`; doc-lint passed.
- **2026-04-27 19:41 UTC** - Code/QA review agents findings closed and revalidated.
- **2026-04-27 20:07 UTC** - Built and vendored `wepp_260427` + `wepp_260427_hill`; synced changelog and recorded dirty include-file guidance.
- **2026-04-27 20:12 UTC** - Review findings dispositioned: dirty-tree provenance explicitly recorded; concurrent RQ-route findings deferred to owning package scope.

## Decisions Log

### 2026-04-27 19:15 UTC: Ship both enhancement lanes in one rollout
**Context**: The user requested both phases together rather than a staged deployment.

**Options considered**:
1. Phase 1 instrumentation first, Phase 2 watchdog later.
2. Single rollout with both instrumentation and watchdog work together.

**Decision**: Option 2.

**Impact**: One integrated validation cycle and one release/deploy gate for all scoped enhancements.

---

### 2026-04-27 19:15 UTC: Keep scope limited to hillslope + continuous watershed
**Context**: Multiple runner methods exist, but user explicitly excluded flowpath and single-storm paths.

**Options considered**:
1. Apply to all runner methods.
2. Scope to `run_hillslope` + `run_watershed` only.

**Decision**: Option 2.

**Impact**: Smaller change surface and faster incident-focused delivery.

---

### 2026-04-27 19:26 UTC: Cache binary identity by resolved executable path
**Context**: Every in-scope run needs enough binary identity to correlate incidents with exact artifacts, but repeated hashing should not add avoidable overhead on worker processes.

**Options considered**:
1. Hash on every run invocation.
2. Cache identity by resolved executable path for the process lifetime and include safe fallback fields if metadata cannot be read.

**Decision**: Option 2.

**Impact**: Logs include deterministic `binary_path`, `binary_sha256`, size, mtime, status, and error fields while keeping repeated invocations bounded.

---

### 2026-04-27 19:26 UTC: Make watchdog Linux best-effort telemetry only
**Context**: D-state process telemetry is useful during stalls, but it must not change WEPP subprocess behavior or fail runs on unsupported systems.

**Options considered**:
1. Add watchdog as an enforcing timeout/kill path.
2. Add watchdog as bounded logging-only telemetry, default-enabled only when Linux `/proc` is available and controlled by env vars.

**Decision**: Option 2.

**Impact**: Operators get `dstate_watchdog` lines for prolonged D-state conditions without introducing new process-control behavior.

---

### 2026-04-27 19:26 UTC: Preserve watershed close-path exception behavior
**Context**: The production failure signature was an infrastructure close failure. The package needs explicit classification without hiding or translating the original failure.

**Options considered**:
1. Catch close failures and convert them to successful run completion when the WEPP success marker was present.
2. Log/classify close failures and re-raise the original `OSError`.

**Decision**: Option 2.

**Impact**: Existing failure propagation is preserved while run-local and worker stderr diagnostics identify stale handles and other close-path I/O errors.

---

### 2026-04-27 19:41 UTC: Update binary identity cache key and watershed exception precedence
**Context**: Post-closure code/QA review found two medium risks: binary identity cache staleness after in-place binary replacement and possible masking of a primary watershed failure by close-path `OSError`.

**Options considered**:
1. Accept as residual risk and document assumptions.
2. Fix both immediately with focused code changes and regression tests.

**Decision**: Option 2.

**Impact**: Binary identity cache now invalidates by stat signature (device/inode/size/mtime), unavailable identity is no longer cached indefinitely, and watershed cleanup raises close-path exceptions only when no primary exception is already active.

---

### 2026-04-27 20:07 UTC: Accept operator-requested release addendum in this package
**Context**: After closure of in-scope runner hardening, the operator requested a direct binary-release follow-up: keep the `-g` compiler traceability change permanent, build `wepp_260427` + `_hill`, vendor binaries/changelog into `wepppy`, and document dirty include-file guidance.

**Options considered**:
1. Reject as out-of-scope and spin a separate release package.
2. Record and execute as a post-closure addendum in this package for continuity.

**Decision**: Option 2.

**Impact**: Package artifacts now include the release cut (`wepp_260427`), vendored binaries/changelog, and explicit dirty include guidance in `wepp-forest` docs/changelog.

---

### 2026-04-27 20:12 UTC: Disposition code/QA review findings for addendum closure
**Context**: User requested dispatched code and QA agent review before handoff.

**Options considered**:
1. Block closure until all medium findings across the entire dirty workspace are fixed.
2. Resolve release-addendum findings in-scope, and explicitly classify concurrent RQ-route findings as out-of-scope to this package.

**Decision**: Option 2.

**Impact**: Release provenance finding was fixed by marking `wepp_260427` as built from `6bb872ca` dirty tree in both source and vendored changelogs. Concurrent RQ-route/schema findings were documented as deferred to their owning package and not modified under this addendum.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Binary hash logging adds avoidable overhead on NFS-backed paths | Medium | Medium | Hash once per resolved binary path and reuse cached identity during process lifetime, invalidating on stat signature changes | Mitigated |
| D-state watchdog emits noisy or low-signal logs | Medium | Medium | Add bounded interval/threshold/max-event controls and clear enable/disable semantics | Monitor |
| Watchdog implementation is Linux-specific | Low | High | Use best-effort Linux-only probes with explicit unsupported no-op behavior elsewhere | Mitigated |
| Close-path hardening changes existing failure signatures unexpectedly | Medium | Low | Preserve existing exception contract while appending structured context and targeted regression tests | Mitigated |
| Dirty capacity include edits are released without aligned documentation | Medium | Medium | Enforced dirty-cycle guidance across `pmxelm.inc`/`pmxhil.inc`/`pmxpln.inc`/`pntype.inc` in `wepp-forest` AGENTS + README + changelog entry | Mitigated |

## Hardening Signal Log (Required for incident/remediation packages)

- **Baseline health signals**:
  - `run_hillslope` has command/startup tracing; `run_watershed` does not.
  - Watershed close-path NFS failures can appear as generic job exceptions.
  - No watchdog signal exists for prolonged D-state process behavior.
- **Post-change health signals**:
  - In-scope runner logs include startup context and binary identity fields.
  - Close-path failures are explicitly classified with filesystem/infrastructure context.
  - Watchdog emits bounded signals only for prolonged D-state conditions.
- **Danger signals observed**: None in targeted validation.
- **Temporary callus register**:
  - D-state watchdog env toggle and thresholds (owner: package implementer; sunset/review: 14-day post-deploy).
- **Softening experiments**:
  - Hypothesis: default watchdog settings may be overly conservative or noisy.
  - Gate results: targeted tests confirm emit/no-emit thresholds and max-event bounding; production signal quality remains under observation.
  - Decision: retain conservative defaults for the 14-day observation window.

## Verification Checklist

### Code Quality
- [x] Targeted `wepp_runner` tests pass.
- [x] `git diff --check` is clean.

### Security
- [x] Security impact triage recorded (`low`) with rationale.
- [x] Dedicated security artifact not required by current scope.
- [x] Re-evaluated at closure; implementation remained observability-only within existing subprocess flows.

### Documentation
- [x] Runner traceability docs updated with field definitions and examples.
- [x] Work-package docs kept current during implementation.
- [x] `wctl doc-lint` passes for touched docs.

### Testing
- [x] Regression tests cover startup trace parity (`run_watershed`).
- [x] Regression tests cover binary provenance fields in in-scope runner logs.
- [x] Regression tests cover watchdog emit/no-emit behavior.
- [x] Targeted regression tests exercise both in-scope methods without invoking real WEPP binaries.

### Deployment
- [x] Deployment/release path remains operator-controlled after validation.
- [x] Observation-window checks documented for first 14 days after deploy.
- [x] Post-closure release addendum validated: wepp-forest smoke/watchlist/pytest/reconciled replay + wepppy provenance/smoke gates.

## Progress Notes

### 2026-04-27 19:15 UTC: Package setup
**Agent/Contributor**: Codex

**Work completed**:
- Created package scaffold at `docs/work-packages/20260427_wepp_runner_traceability_hardening/`.
- Drafted `package.md` and this tracker with incident-focused scope.
- Captured explicit user constraints:
  - flowpath out of scope
  - single-storm out of scope
  - both enhancement lanes ship in one rollout

**Blockers encountered**:
- None.

**Next steps**:
1. Start implementation in `wepp_runner/wepp_runner.py` using the active ExecPlan.
2. Add targeted `tests/wepp_runner/` coverage for startup trace/provenance/watchdog behavior.
3. Run validation commands and update tracker with outcomes.

**Test results**:
- Documentation scaffolding only; no code tests run yet.

### 2026-04-27 19:27 UTC: Implementation and targeted validation
**Agent/Contributor**: Codex

**Work completed**:
- Added cached binary identity logging for continuous `run_hillslope` and `run_watershed`.
- Added watershed startup trace parity with run directory, run file, err file, command text, and `attempt=1/1`.
- Added Linux best-effort D-state watchdog telemetry with env-configurable enablement, interval, threshold, and max-event bounds.
- Added watershed close-path diagnostics that classify `errno=116` as `stale_file_handle` and re-raise the original close failure.
- Added targeted regression tests in `tests/wepp_runner/test_traceability_hardening.py`.
- Updated `wepp_runner/AGENTS.md`, `package.md`, this tracker, and `PROJECT_TRACKER.md`.

**Blockers encountered**:
- None.

**Next steps**:
1. Monitor production logs for the 14-day observation window after operator deploy.

**Test results**:
- `wctl run-pytest tests/wepp_runner --maxfail=1` - `17 passed`, `2 warnings`.
- `wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1` - `18 passed`, `2 warnings`.
- `wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260427_wepp_runner_traceability_hardening --path wepp_runner/AGENTS.md` - `5 files validated`, `0 errors`, `0 warnings`.
- `git diff --check` - passed with no output.
- Post-disposition validation:
  - `wctl run-pytest tests/wepp_runner --maxfail=1` - `20 passed`, `2 warnings`.
  - `wctl run-pytest tests/wepp/test_wepp_runner_outputs.py tests/wepp_runner --maxfail=1` - `21 passed`, `2 warnings`.

### 2026-04-27 20:07 UTC: Post-closure release addendum execution
**Agent/Contributor**: Codex

**Work completed**:
- Built `/workdir/wepp-forest/release/wepp_260427` + `/workdir/wepp-forest/release/wepp_260427_hill` (`TARGET_TAG=260427`, `/usr/bin/gfortran`).
- Kept `src/makefile` `-g -fbacktrace` defaults and documented permanence as traceability enhancement.
- Added dirty include guidance for `src/pmxelm.inc`, `src/pmxhil.inc`, `src/pmxpln.inc`, `src/pntype.inc` in `wepp-forest/AGENTS.md`, `wepp-forest/src/AGENTS.md`, and `wepp-forest/README.md`.
- Updated `wepp-forest/change-log.md` with a new `wepp_260427` top entry.
- Vendored binaries and changelog copy into `wepppy`.

**Blockers encountered**:
- None.

**Next steps**:
1. Monitor runtime logs during the standard post-deploy window for `binary_identity` and watchdog signal quality.

**Test results**:
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/release/wepp_260427` - passed.
- `tools/smoke_wepp_binary_host.sh /workdir/wepp-forest/release/wepp_260427_hill` - passed.
- `python /workdir/wepp-forest/tools/run_hillslope_watchlist.py --binary /workdir/wepp-forest/release/wepp_260427_hill` - `12/12 passed`.
- `pytest` (`/workdir/wepp-forest`) - `53 passed`, `2 warnings`.
- Reconciled-condenser manual replay (`/workdir/wepp-forest/release/wepp_260427`) - success marker present, zero parse/runtime error signatures.
- `tools/check_wepp_binary_provenance.sh wepp_runner/bin/wepp_260427 wepp_runner/bin/wepp_260427_hill` - passed.
- `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260427` - passed.
- `tools/smoke_wepp_binary_host.sh wepp_runner/bin/wepp_260427_hill` - passed.

### 2026-04-27 20:12 UTC: Review and disposition pass
**Agent/Contributor**: Codex (`reviewer` + `qa_reviewer` dispatched)

**Work completed**:
- Ran parallel delegated reviews with `reviewer` and `qa_reviewer`.
- Fixed in-scope provenance finding by updating `wepp_260427` changelog entry to `6bb872ca (dirty tree)` and re-syncing vendored changelog copy.
- Classified RQ-route/schema findings as concurrent worktree scope outside this release addendum.

**Disposition summary**:
- Medium (release provenance clean-room ambiguity): **Resolved** (dirty-tree origin documented in canonical + vendored changelog).
- Medium (package scope mismatch due concurrent RQ files in dirty workspace): **Deferred/out-of-scope for this addendum**, tracked for owning package.
- Medium (RQ contract/behavior nuance around abstraction fast-fail exceptions): **Deferred/out-of-scope for this addendum**, tracked for owning package.
- Medium (possible `checkbox_wepp_watershed=false` regression): **Deferred/out-of-scope for this addendum**, tracked for owning package.

**Test results**:
- Re-used current addendum validation set plus subagent verification transcripts.
- No regression observed in release build/vendoring path after provenance-note update.

## Watch List

- **NFS-close failures**: verify whether enhanced watershed close-path logs cleanly distinguish infra vs model failures.
- **Binary identity stability**: ensure hash/provenance fields are deterministic and comparable across runs.
- **Watchdog signal quality**: track false-positive/noise rate during observation window.

## Communication Log

### 2026-04-27 19:15 UTC: Package request and rollout shape
**Participants**: User, Codex
**Question/Topic**: Create a work package for runner traceability enhancements and use one rollout for both lanes.
**Outcome**: Package initialized with single-rollout scope and explicit out-of-scope boundaries.
