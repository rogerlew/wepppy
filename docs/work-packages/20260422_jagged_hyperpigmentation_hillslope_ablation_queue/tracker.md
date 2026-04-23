# Tracker - Jagged Hyperpigmentation Hillslope Ablation Queue (`H3507`, `H1271`)

> Living document tracking progress, decisions, risks, and communication for the queued two-hillslope ablation follow-up.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-04-22 20:35 UTC  
**Current phase**: Observe-only + first hypothesis lanes complete; Windows comparator baseline established  
**Last updated**: 2026-04-22 22:05 UTC  
**Next milestone**: Execute next one-change hypothesis lane group using Windows comparator baseline  
**Security impact**: `low`  
**Dedicated security review**: `no`  
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog
- [ ] Finalize incident package recommendation after causal attribution evidence is captured.

### In Progress
- [ ] None.

### Blocked
- [ ] None.

### Done
- [x] Captured user-reported anomaly context and target hillslope IDs (`H3507`, `H1271`) from run `jagged-hyperpigmentation/disturbed9002-10-mofe` (2026-04-22 20:35 UTC).
- [x] Corrected and confirmed source evidence root on wepp1 as `/geodata/wc1/runs/ja/jagged-hyperpigmentation` (2026-04-22 20:39 UTC).
- [x] Created work-package scaffold (`package.md`, `tracker.md`, `prompts/active`, `prompts/completed`, `notes`, `artifacts`) (2026-04-22 20:35 UTC).
- [x] Authored active ExecPlan for queued execution handoff (2026-04-22 20:35 UTC).
- [x] Registered package in `PROJECT_TRACKER.md` and promoted to `In Progress` after staging (2026-04-22 20:48 UTC).
- [x] Initialized ablation incident package `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/` (2026-04-22 20:41 UTC).
- [x] Staged two-hillslope source artifacts from wepp1 and built runnable local replay workspace (2026-04-22 20:43 UTC).
- [x] Executed baseline local hillslope replays (`p1271.run`, `p3507.run`) and captured logs (2026-04-22 20:43 UTC).
- [x] Captured source-vs-staged signature scan evidence (`C099`, `C100`) and finalized incident manifest/checksums (2026-04-22 20:47 UTC).
- [x] Verified `blarhg` Windows comparator binary (`wepppy-win-bootstrap.exe`) presence, SHA256, and UTC timestamp; logged inventory under incident `artifacts/env/` (2026-04-22 21:59 UTC).
- [x] Executed observe-only and first hypothesis lane cycle (`C101-C106`) including Windows replay runs, signature census, and strict Linux-vs-Windows raw compare artifacts (2026-04-22 22:00 UTC).
- [x] Recorded decision to use Windows bootstrap as parity baseline comparator for this incident (2026-04-22 22:00 UTC).

## Timeline

- **2026-04-22 20:35 UTC** - Package created and queued from Marta intake.
- **2026-04-22 20:39 UTC** - Source root corrected to `/geodata/wc1/runs/ja/jagged-hyperpigmentation`.
- **2026-04-22 20:41 UTC** - wepp-forest incident package initialized.
- **2026-04-22 20:43 UTC** - Staging and baseline local replays complete.
- **2026-04-22 20:47 UTC** - Signature scans + manifest/checksum finalization complete.
- **2026-04-22 21:59 UTC** - Windows comparator inventory captured on `blarhg`; staged Windows target replays executed.
- **2026-04-22 22:00 UTC** - Observe-only + first hypothesis lanes recorded (`C101-C106`); Windows comparator adopted as parity baseline.

## Decisions Log

### 2026-04-22 20:35 UTC: Queue package in `wepppy` while targeting execution in `/workdir/wepp-forest`
**Context**: Request arrived in `wepppy` workflow, but ablation protocol and campaign tooling live in `wepp-forest`.

**Options considered**:
1. Create no package until campaign slot opens.
2. Create queue package now with explicit handoff into `wepp-forest` ablation protocol.

**Decision**: Option 2.

**Impact**: Campaign can start immediately at slot availability without re-scoping.

---

### 2026-04-22 20:35 UTC: Restrict initial scope to two reported hillslopes only
**Context**: User reported anomalous behavior specifically on `H3507` and `H1271`.

**Options considered**:
1. Expand immediately to all hillslopes in the run.
2. Start with the two reported hillslopes and only broaden if evidence requires.

**Decision**: Option 2.

**Impact**: Preserves attribution clarity and keeps first ablation cycle small and deterministic.

---

### 2026-04-22 20:41 UTC: Stage immediately rather than waiting for queue slot
**Context**: User requested immediate staging so the package is ready to run next.

**Options considered**:
1. Leave package queued only (docs without artifacts).
2. Perform incident init + artifact staging + baseline replay now.

**Decision**: Option 2.

**Impact**: Incident is now execution-ready with reproducible artifacts and baseline logs.

---

### 2026-04-22 22:00 UTC: Use `wepppy-win-bootstrap.exe` on `blarhg` as parity comparator baseline
**Context**: New requirement from Anurag requested explicit Windows comparator verification and use as parity baseline if stable for target hillslopes.

**Options considered**:
1. Keep Linux staged replay as sole comparator lane.
2. Verify Windows bootstrap binary identity and stability on staged `p1271/p3507`, then promote it to parity baseline for subsequent lanes if star-free.

**Decision**: Option 2.

**Impact**: Comparator baseline is now explicitly pinned (`sha256=07d348d5f9ebff607b6f8e15bea8647410a080c8451b9017f74a9475f39c569d`) with auditable Windows replay evidence (`C101-C104`).

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Source run artifacts are only available on wepp1 and not mirrored locally | High | Medium | Source snapshot copied into incident `artifacts/repro/source_wepp1` and checksummed | Mitigated |
| Anomaly is non-deterministic across replays | High | Medium | Source-vs-Linux-vs-Windows signature census captured (`C105`); baseline comparator pinned (`C101-C104`) for subsequent lanes | Open |
| Lane scope creep bundles multiple changes and breaks attribution | Medium | Medium | Enforce one behavioral change group per lane using protocol checklist | Open |
| Queue delay causes context drift | Medium | Medium | Package converted from queued-only to staged-ready with concrete first commands | Closed |
| Windows comparator provenance drift over time | Medium | Low | Pinned SHA/timestamp captured in incident env artifact (`C101`) and referenced in decision log | Mitigated |

## Verification Checklist

### Documentation
- [x] `package.md` scoped with objectives, boundaries, and references.
- [x] `tracker.md` initialized with queue state and decision log.
- [x] Active ExecPlan authored in `prompts/active`.
- [x] `PROJECT_TRACKER.md` updated with active in-progress entry.

### Execution Readiness
- [x] wepp1 source path confirmed and staging command tested.
- [x] Incident directory initialized in `/workdir/wepp-forest/docs/ablation/`.
- [x] Baseline command transcript captured.
- [x] Observability lane transcript captured.
- [x] First hypothesis lane matrix rows recorded.

## Progress Notes

### 2026-04-22 20:35 UTC: Queue package initialization
**Agent/Contributor**: Codex

**Work completed**:
- Converted Marta intake into a scoped work package for the next ablation queue slot.
- Documented specific targets (`H3507`, `H1271`) and the reported `element.dat` anomaly signature.
- Authored queue-focused package/tracker docs and initial ExecPlan.
- Updated `PROJECT_TRACKER.md` backlog with package pointer.

**Blockers encountered**:
- Initial source-path ambiguity (`/geodata/wc1/ja/...` vs actual `/geodata/wc1/runs/ja/...`).

**Next steps**:
1. Confirm exact source root on wepp1.
2. Stage artifacts and prep runnable replay workspace.
3. Capture baseline logs.

**Test results**:
- Docs-only session; no model execution lanes run yet.

### 2026-04-22 20:48 UTC: Staging and baseline replay complete
**Agent/Contributor**: Codex

**Work completed**:
- Confirmed source root: `/geodata/wc1/runs/ja/jagged-hyperpigmentation` on wepp1.
- Initialized incident package: `/workdir/wepp-forest/docs/ablation/20260422_jagged-hyperpigmentation_hillslope_elementdat-stars/`.
- Copied 29 source artifacts (target run inputs/outputs for `H1271` and `H3507`) into incident repro snapshot.
- Built runnable staging layout under `artifacts/repro/staged/{runs,output,logs}`.
- Executed local baseline replays for `p1271.run` and `p3507.run` with `/workdir/wepp-forest/src/wepp_hill`.
- Captured source-vs-staged signature scans and finalized incident `manifest.csv` + `checksums.sha256`.

**Blockers encountered**:
- None (staging complete).

**Next steps**:
1. Add observe-only lane instrumentation around source-signature windows.
2. Execute first hypothesis lane set.
3. Update matrix with keep/rollback decisions.

**Test results**:
- `p1271.run` baseline replay: success marker present; stderr empty.
- `p3507.run` baseline replay: success marker present; stderr empty.
- Source signature scan (`C099`): starred tokens present.
- Staged output signature scan (`C100`): no starred tokens found.

### 2026-04-22 22:05 UTC: Windows parity baseline verification complete
**Agent/Contributor**: Codex

**Work completed**:
- Verified `C:\src\wepppy-win-bootstrap\bin\wepppy-win-bootstrap.exe` on `blarhg`; captured size/hash/timestamp inventory in incident env artifacts.
- Staged target hillslope run inputs on `blarhg` and executed Windows comparator replays for `p1271` (`C102`) and `p3507` (`C103`).
- Captured Windows logs and output artifacts back into incident package (`artifacts/repro/windows_bootstrap`).
- Completed signature scan + census + strict raw compare cases (`C104-C106`).
- Updated incident decision record to adopt Windows bootstrap as parity comparator baseline for this incident.

**Blockers encountered**:
- None.

**Next steps**:
1. Run next one-change hypothesis lane group with Windows comparator as reference lane.
2. Continue attribution work toward minimal causal explanation for source-only starred signatures.
3. Finalize keep/rollback recommendation once a causal lane is proven.

**Test results**:
- `C102`: PASS (`p1271` Windows replay success marker; no stderr).
- `C103`: PASS (`p3507` Windows replay success marker; no stderr).
- `C104`: PASS (no starred signatures in Windows target `element.dat` files).
- `C105`: FAIL by design (source-only stars remain; Linux/Windows lanes star-free).
- `C106`: FAIL strict `tol=0` raw parity between Linux staged and Windows comparator (numeric differences present across `.dat` outputs).

## Communication Log

### 2026-04-22 20:35 UTC: Marta intake queued
**Participants**: Marta (via user), Codex  
**Question/Topic**: Queue two hillslopes (`H3507`, `H1271`) from `jagged-hyperpigmentation/disturbed9002-10-mofe` for next ablation campaign slice.  
**Outcome**: Created queued work package with active ExecPlan and tracker for campaign handoff.

### 2026-04-22 20:36 UTC: source path correction
**Participants**: User, Codex  
**Question/Topic**: Confirm exact source location for run artifacts.  
**Outcome**: Finalized source root as `/geodata/wc1/runs/ja/jagged-hyperpigmentation` and updated package docs.

### 2026-04-22 20:40 UTC: immediate staging request
**Participants**: User, Codex  
**Question/Topic**: Stage hillslopes now so the campaign is ready to run.  
**Outcome**: Incident initialized, artifacts staged, baseline replay logs captured, and manifest/checksum finalized.

### 2026-04-22 21:50 UTC: Windows parity baseline requirement
**Participants**: User (relayed from Anurag), Codex  
**Question/Topic**: Verify `wepppy-win-bootstrap.exe` stability on `blarhg` and use it as comparator if star-free on target cases.  
**Outcome**: Verified binary identity + stability for staged `p1271/p3507`; comparator baseline decision recorded and synced into incident docs.
