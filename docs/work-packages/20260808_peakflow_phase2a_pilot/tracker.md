# Tracker – Topanga Peak-Flow Phase 2A Pilot

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-08 22:59 UTC
**Current phase**: Pilot complete; local census released by design amendment
**Last updated**: 2026-08-09 04:22 UTC
**Next milestone**: Prepare the durable engine and freeze the Topanga matrix
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Complete the linked durable-engine preparation package.
- [ ] Create the separate execution package only after preparation GO.

### In Progress

- None.

### Blocked

- [ ] Canopy and LAI probes — blocked until initial probe mechanics pass.
- [ ] Cross-site, snow-site, and OFE phases — deferred under Gates 4 and 5.

### Deferred

- [ ] Repair sibling-channel isolation and channel-volume authority before any
  downstream-impact follow-up.

### Done

- [x] Gate 2.1 GO and Phase 2A authorization recorded (2026-08-08 22:59 UTC).
- [x] Phase 2A work package scaffolded (2026-08-08 22:59 UTC).
- [x] Completed 280 full-history observer baselines and froze 58,211 event
  records (2026-08-09 00:32 UTC).
- [x] Froze feasible maximum-coverage selection `3b5778d7c9171311`: Hills 106,
  84, 8, 35, 31, 91, 85, and 62 (2026-08-09 00:38 UTC).
- [x] Completed 64/64 mutation and 64/64 watershed-routing trials with exact
  one-target pass isolation (2026-08-09 00:43 UTC).
- [x] Validated real no-surplus packet and both production solver selections
  (2026-08-09 00:44 UTC).
- [x] Mechanism-traced the Hill 106 1986 day-46 `84.95×` response and stopped
  two incomplete HDRIVE replays (2026-08-09 00:45 UTC).
- [x] Published the ten-criterion exit report: seven pass, three fail; full
  census withheld (2026-08-09 00:49 UTC).
- [x] Verified byte counts and SHA-256 hashes for all 139 retained routing and
  hydrograph artifacts (18.23 GB), plus five focused tests (2026-08-09 01:11
  UTC).
- [x] Amended the study to cull per-mutation routing and release the local
  census without changing the failed pilot evidence (2026-08-09 02:38 UTC).
- [x] Scaffolded the durable-engine preparation successor and separated it from
  full-matrix execution (2026-08-09 04:22 UTC).

## Timeline

- **2026-08-08 22:59 UTC** – Package opened from the accepted Gate 2.1
  disposition; no pilot mutations executed.
- **2026-08-09 00:32 UTC** – Completed burned and undisturbed baseline census;
  both solver methods and real no-surplus events are represented.
- **2026-08-09 00:38 UTC** – Preserved a stopped preregistration after the
  no-clipping guard rejected Hill 1 at cover `1.00`; froze a corrected,
  baseline-feasible content-addressed selection without screening outcomes.
- **2026-08-09 00:43 UTC** – Completed the 64 mutation and routing matrices;
  all unmutated hillslope passes remained byte-identical.
- **2026-08-09 00:45 UTC** – Bracketed the Hill 106 discontinuity within
  `8.54e-5 mm/h` Ksat and traced the surplus assignment mode change.
- **2026-08-09 00:49 UTC** – Withheld the full census after deterministic
  off-path channel changes and interval/daily volume disagreement failed
  criteria 5–7.
- **2026-08-09 02:38 UTC** – Retired routing criteria 5–7 as gates for the local
  census and deferred downstream-impact claims to a separate follow-up.
- **2026-08-09 04:22 UTC** – Opened the preparation package; execution remains
  blocked until it freezes a validated matrix and publishes GO.

## Decisions Log

### 2026-08-09 02:38 UTC: Cull routing from the census critical path

**Decision**: Execute the full candidate census as hillslope-only observer,
event-pairing, screening, bracket, and replay work. Do not run the watershed
binary per mutation.

**Impact**: The local census is released immediately and avoids the projected
261.7 GB routing footprint. It may report local prevalence and mechanisms but
not downstream-channel or outlet consequences. The original routing failures
remain recorded and are not converted to passes.

### 2026-08-08 22:59 UTC: Pilot size and first probes

**Decision**: Freeze eight hillslopes, including Hill 106, and begin with Ksat
and paired-ground-cover probes in both scenario strata.

**Impact**: The initial matrix is bounded at 64 mutation runs before adaptive
bracketing: eight hillslopes × two strata × two parameter families × two
directions. Baseline and assurance runs are additional and tracked separately.

### 2026-08-08 22:59 UTC: Selection before outcomes

**Decision**: Select the seven non-control hillslopes from baseline covariates
and routing attributes before examining their mutation responses.

**Impact**: The pilot can exercise known mechanisms without selecting every
site because it already showed an anomaly.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Pilot selection misses required strata | High | Medium | Maximum-coverage selection plus frozen coverage table | Closed |
| Mutation pipeline contaminates other hillslope passes | High | Medium | Input checksums prove 139 unchanged passes per trial | Closed |
| Near-zero ratios create false candidates | Medium | Medium | ADR-0042 absolute floors plus protocol rules | Closed |
| HDRIVE replay is incomplete | High | Low | Two 0.531-fraction replays stopped and dispositioned | Closed |
| Artifact volume scales poorly | Medium | Medium | 261.7 GB projection within declared 300 GB bound | Closed |
| One target changes sibling channel routing | High | Confirmed | Defer routing claims; repair before sampled follow-up | Deferred |
| Interval and daily channel volumes disagree | High | Confirmed | Defer routing claims; reconcile before sampled follow-up | Deferred |

## Verification Checklist

### Documentation

- [x] Package, tracker, completed ExecPlan, and audit README are synchronized.
- [x] Documentation lint passes.

### Testing

- [x] Manifest and ledger schemas validate.
- [x] Mutation input-isolation checks pass.
- [x] Real no-surplus packet validates.
- [x] Outer-join absence/zero tests pass.
- [ ] Routing-closure invariants pass (34,899 off-path records).
- [ ] Hydrograph timestamps and volumes are consistent (timestamps pass;
  20/20 volume checks fail).
- [x] Known-positive adaptive bracket and frozen replay complete.
- [x] Exit report evaluates all ten criteria.
- [x] Focused Phase 2A pytest suite passes (5 tests).
- [x] External storage manifest validates 139 retained artifacts (18.23 GB).
- [ ] Repository-wide pytest sweep — environment-blocked because the existing
  `weppcloud` container has no available `/tmp` capacity; the first direct
  `/tmp/run` writer fails with `ENOSPC`.

## Progress Notes

### 2026-08-08 22:59 UTC: Package initialization

**Agent/Contributor**: Codex

**Work completed**:

- Converted the accepted Phase 2A scope and exit criteria into a work package.
- Bounded the first mutation matrix and preserved all deferred phases.

**Next steps**:

- Inventory the two frozen scenarios and produce a preregistration-only
  selection table before any mutation results are generated.

**Test results**: documentation scaffold only; no model runs performed.

### 2026-08-09 00:49 UTC: Pilot disposition

**Agent/Contributor**: Codex

**Work completed**:

- Executed the frozen observational, mutation, watershed-routing, interval,
  replay, and adaptive-bracket workflows.
- Published schemas, compact ledgers, external storage locators, measured cost,
  ADR-0042, and the machine-readable exit decision.

**Next steps**:

- Correct the two routing authority defects, then rerun criteria 5–7 without
  repeating immutable hillslope or solver evidence.

**Test results**: 64/64 mutations and routes complete; automatic exit report
is seven pass and three fail, with the full census withheld.

### 2026-08-09 01:11 UTC: Final validation

**Agent/Contributor**: Codex

**Work completed**:

- Added and verified a deterministic external routing-storage manifest for all
  retained daily, interval, repeat-baseline, and hydrograph outputs.
- Revalidated Phase 1 and Phase 2A schemas, compact artifacts, documentation,
  Python compilation, and focused behavior tests.

**Next steps**:

- Restore writable capacity in the development container's `/tmp`, then rerun
  `wctl run-pytest tests --maxfail=1` as a repository-level assurance check.

**Test results**: 5 focused tests pass; 139 external hashes pass. The broad
suite stops at an unrelated ash-upload test because `/tmp/run` cannot be
created on the full container filesystem.

### 2026-08-09 02:38 UTC: Local-census design amendment

**Agent/Contributor**: requesting operator and Codex

**Work completed**:

- Culled watershed routing from the census critical path.
- Preserved the original failed routing evidence while releasing a
  hillslope-only census with an explicit no-downstream-claims boundary.

**Next steps**:

- Freeze and execute the eligible local hillslope mutation matrix.

**Test results**: documentation-only contract amendment; documentation lint
passes.

## Watch List

- **Observer provenance**: all runs must pin WEPP-Forest `ea25ad79` and the
  accepted executable hash.
- **Immutable Gate 2.1 evidence**: do not rewrite the acceptance report.
- **Candidate language**: screening flags remain candidates until adjudicated.
