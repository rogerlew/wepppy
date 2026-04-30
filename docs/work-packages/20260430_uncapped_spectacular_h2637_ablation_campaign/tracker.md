# Tracker - Uncapped-Spectacular H2637 Ablation Campaign

> Living execution log for preparing and running the `H2637` closure-anomaly ablation campaign.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-30 19:10 UTC  
**Current phase**: Completed (attribution lanes executed; evidence captured)  
**Last updated**: 2026-04-30 19:41 UTC  
**Next milestone**: Open focused routine-level follow-up package in `wepp-forest` for `wepp_260429_hill` day-44/OFE19 root cause isolation  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Follow-up package: isolate routine-level cause in `wepp_260429_hill` for the reproduced day-44 spike.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Created package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-30 19:10 UTC).
- [x] Pulled source run inputs from `wepp1` into `artifacts/repro/source_wepp1/runs/` (2026-04-30 19:10 UTC).
- [x] Pulled source hillslope outputs from `wepp1` into `artifacts/repro/source_wepp1/output/` (2026-04-30 19:10 UTC).
- [x] Generated staged integrity artifacts (`manifest.csv`, `checksums.sha256`) (2026-04-30 19:10 UTC).
- [x] Authored active ablation ExecPlan with `blarhg` comparator requirement (2026-04-30 19:10 UTC).
- [x] Ran documentation lint on package docs and `PROJECT_TRACKER.md` (2026-04-30 19:15 UTC).
- [x] Initialized incident package in `/workdir/wepp-forest/docs/ablation/20260430_uncapped-spectacular_h2637_hillslope_closure-spike/` (2026-04-30 19:27 UTC).
- [x] Executed Linux baseline replay lane (`C000`, production binary `wepp_260429_hill`) (2026-04-30 19:29 UTC).
- [x] Executed Linux comparator lane (`C010`, `wepp_dcc52a6_hill`) (2026-04-30 19:29 UTC).
- [x] Executed required Windows comparator lane on `blarhg` (`C020`, `wepppy-win-bootstrap.exe`) (2026-04-30 19:31 UTC).
- [x] Generated lane diagnostics + closure summaries and finalized incident manifest/checksums (2026-04-30 19:41 UTC).
- [x] Synced incident evidence snapshot into this package under `artifacts/incident_snapshot/` and published package `artifacts/evaluation_summary.md` (2026-04-30 19:44 UTC).

## Timeline

- **2026-04-30 19:10 UTC** - Package initialized and staged from `wepp1`.
- **2026-04-30 19:15 UTC** - Documentation lint validated for package docs and `PROJECT_TRACKER.md`.
- **2026-04-30 19:27 UTC** - Incident package initialized in `wepp-forest/docs/ablation`.
- **2026-04-30 19:29 UTC** - `C000` and `C010` Linux lanes executed successfully.
- **2026-04-30 19:31 UTC** - `C020` Windows comparator lane executed successfully on `blarhg`.
- **2026-04-30 19:41 UTC** - Incident finalized (`manifest_rows=88`, `checksummed_files=93`) after compacting redundant repro payloads to satisfy artifact-budget policy, attribution evidence complete.
- **2026-04-30 19:44 UTC** - Evidence synchronized into package artifacts; package marked complete.

## Decisions Log

### 2026-04-30 19:10 UTC: Stage both run inputs and hillslope outputs at intake
**Context**: User requested campaign prep and immediate hillslope input pull.

**Options considered**:
1. Pull only `p2637.*` run inputs.
2. Pull `p2637.*` plus `H2637.*.dat` outputs used by anomaly analysis.

**Decision**: Option 2.

**Impact**: Campaign can start without another production fetch cycle.

---

### 2026-04-30 19:10 UTC: Treat Windows comparator lane as first-class acceptance gate
**Context**: User explicitly requested parity testing against `wepppy-win-bootstrap.exe` on `blarhg`.

**Decision**: Include `blarhg` comparator lane in baseline lane sequence, not as optional follow-up.

**Impact**: Campaign outcomes include Linux-vs-Windows comparator evidence by default.

---

### 2026-04-30 19:41 UTC: Close package as attribution-complete, root-cause-follow-up-open
**Context**: Lane matrix isolated behavior to production binary lineage but did not isolate routine-level causal code.

**Decision**: Mark this package complete for attribution scope and carry routine-level isolation as explicit follow-up work.

**Impact**: Clear closure for this package without conflating attribution and remediation scopes.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Anomaly cannot be reproduced from staged snapshot | High | Medium | Source snapshot + copied production binary replay lane (`C000`) | Mitigated |
| Lane scope creep breaks attribution | Medium | Medium | One-change-per-lane matrix discipline (`C000`/`C010`/`C020`) | Mitigated |
| Windows comparator drift on `blarhg` | Medium | Low | Captured `wepppy-win-bootstrap.exe` env/hash metadata | Mitigated |
| Routine-level causality still unresolved | Medium | Medium | Open explicit follow-up package in `wepp-forest` | Open |

## Verification Checklist

### Documentation
- [x] `package.md` scoped with objectives and boundaries.
- [x] `tracker.md` maintained with decisions/progress.
- [x] Active ExecPlan maintained and closed with outcomes.
- [x] `PROJECT_TRACKER.md` lifecycle updated.

### Staging
- [x] `wepp1` source path verified.
- [x] `p2637` input bundle copied locally.
- [x] `H2637` output bundle copied locally.
- [x] `manifest.csv` and `checksums.sha256` generated.

### Execution and Evidence
- [x] Incident package initialized in `wepp-forest/docs/ablation`.
- [x] Linux baseline replay lane executed (`C000`).
- [x] Linux historical comparator lane executed (`C010`).
- [x] `blarhg` Windows comparator lane executed (`C020`).
- [x] Lane summary artifacts generated and incident finalized.

## Progress Notes

### 2026-04-30 19:44 UTC: Campaign closure
**Agent/Contributor**: Codex

**Work completed**:
- Executed and documented the required lane matrix in incident package `20260430_uncapped-spectacular_h2637_hillslope_closure-spike`.
- Confirmed source day-44 legacy closure spike reproduces in `C000` (`wepp_260429_hill`) and is absent in comparator lanes `C010` (`wepp_dcc52a6_hill`) and `C020` (`wepppy-win-bootstrap.exe` on `blarhg`).
- Finalized incident artifacts (`manifest.csv`, `checksums.sha256`) and synchronized a compact evidence snapshot into this package.
- Published package-level `artifacts/evaluation_summary.md` with findings and residual risks.

**Blockers encountered**:
- None for attribution scope.

**Next steps**:
1. Open a focused routine-level ablation package in `wepp-forest` for the `wepp_260429_hill` day-44/OFE19 spike.
2. Expand replay coverage to adjacent hillslopes if recurrence assessment is needed.

**Test results**:
- Replay execution lanes (`C000`, `C010`, `C020`) all completed with success markers.
- Incident package finalized via `python tools/ablation_protocol.py finalize`.
