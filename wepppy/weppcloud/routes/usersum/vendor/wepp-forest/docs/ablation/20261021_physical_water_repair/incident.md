# Incident: Physical water allocation and routing

- `incident_id`: `20261021_physical_water_repair`
- `status`: `active`
- `scope`: `mixed`
- `author`: `Codex`
- `date_utc`: `2026-10-21`
- `host_scope`: `dev`
- `contract_refs`: `model_gap`

## Summary and baseline

261021 source `6a6621e4` reproduces four native failures: terminal-OFE initial
groundwater area, lost hourly infiltration remainder, underfilled flat source
hydrographs and missing channel-local rates. Portable tests initially produce
15 failures/six controls; 88 existing source/state/calendar tests pass.
See `tests/test_physical_water.py`, `tests/fixtures/physical_water`, and
`tools/physical_water_case.py`. No private inputs are required by these tests.

## Contracts and narrow corrections

The [physical water contract](../../contracts/physical-water-routing-contract.md)
and WEPPpy ADR-0101 document reviewed groundwater, signed allocation and source
cell contracts. Independent reviews caught feasible-withdrawal exhaustion,
binary32 near-capacity artifacts, invalid source durations and fine-grid overlap
cancellation. Those rejected variants are retained in the external lane trees.
The final candidate uses original represented liquid inventory and binary64
working allocation, explicit infeasibility errors and binary64 flat overlap.

No channel source/sink or routing solver correction is promoted. The isolated
positive-local experiment improves input delivery but leaves rate/storage/output
disagreement. Four strict expected-failure channel tests retain that open defect;
they are not counted as repaired. A zero printed balance is not acceptance.

## Evidence and experiments

Large traces/builds: `/workdir/watershed-physical-water-repair-20261021`.
Compact cross-repository evidence and independent reviews:
WEPPpy `docs/work-packages/20261021_watershed_physical_water_repair/artifacts/`.
`matrix.csv` records lane dispositions. No production run or dated binary changed.
The 44-year diagnostic comparisons distinguish observation parity from
expected baseline/candidate physics changes. Full-date output checks remain
required even when process success is reported.

## Remaining model gap and stop condition

Preserve MC dynamics and numerical storage authority per operator decision.
Source quadrature, signed soil/routing exchange, clipping and adaptive
no-history degenerate-reference propagation remain open. Reviewed source/publication corrections
are a separate narrow checkpoint, described below. Geometric-volume mismatch alone is not an MC water-loss finding. Do not derive storage or outflow
from the same balance being tested, widen tolerances or normalize the outlet.
Do not mark this incident resolved or release-ready while that gap remains.
Candidate rollback is the untouched 261021 pair; regenerate contributing
hillslope/PASS/watershed outputs together in isolated directories for comparison.

## MC-preserving continuation

Actual per-cell MC4/5 observations and WSHCQI/WSHCHR cascade controls establish
separate coefficient revaluation and publication/rate-transfer disagreement.
A dry-boundary guard also skips live interior states. Six seeded controls fail
on the old guard; two empty controls pass. Adding the nonzero-interior eligibility
condition makes all eight pass while preserving equations and storage meanings.
See `tools/mc_continuity_probe.py`, `tools/mc_cascade_probe.py`,
`tools/mc_interior_state_probe.py` and `tests/test_channel_state.py`.

## Reviewed interface continuation

Corrected local-source eligibility excludes positive side-impoundment transfer.
Deferred groundwater enters qin once; remove its redundant initial-outlet term.
MC publication uses accepted outlet integration including q0, with independently
calculated geometry. KW3 shares the source correction but not MC publication.
All 29 fresh paired replays pass dates/transfer checks and independent QA's 108
executions validate threshold admission and cascades. Portable regressions include
every-day source arrays and midnight carry; mutation review closes initial gaps.
Full native gates are recorded separately upon completion.

Fixed positive-coefficient controls expose a signed-coupling discrepancy: a
prescribed 50 m³ daily soil loss from 100 m³ input produces about 91.519 m³
accepted early-pulse export; late forcing skips 47.396 m³ of requested loss.
These controls prescribe the post-soil identity and do not execute WATBAL.
The actual 44-year raw/export observer preserves scientific output parity.
A coupled repair must reconcile accepted withdrawal with the soil calculation,
not reduce rtrans after soil credit. See retained scientific/QA reviews in
`artifacts/logs/` and the active WEPPpy work package. Incident remains active.

V2 required full gate: 409 passed, one failed, two warnings. Explicit candidate
upstream-scheme 100-year execution timed out after 900 s at year 16/day 81.
V2 promotion was blocked, irrespective of successful narrow controls and 29 replays.
Live interior with zero-reference K=0 flips signs every step in MC4 rather
than propagating. The bounded v5 correction below addresses retained-reference cases.


## MC4 reference and fixed-point continuation

V5 preserves the last valid MC4 reference only for degenerate boundary-derived
estimates with nonzero retained interior. CHRSTATE_LIVE is readonly, and reference
history resets per channel at simulation initialization. No-history cases, MC5
and KW3 remain unchanged. The 100 m³ late-pulse control now recedes; a newly
constructed interior reference was rejected because it changes the coefficient
coordinate and exported volume more broadly.

At 60-second steps, finite-precision subnormal profiles can repeat exactly.
V5 copies only a bitwise repeated full raw profile and accepted outlet under
bitwise unchanged future forcing. Numeric equality alone was rejected after a
signed-zero counterexample in v4. No represented water is removed by a cutoff.

The exact failed gate now passes in 580.64 seconds, with the original 900-second
timeout and final observed year100/day365/channel31. Both builds, 29 paired
replays, 12 watchlist cases, both profile host smokes, 16 continuity and eight
cascade controls pass. Ninety-two final portable reference tests pass, including
60 complete raw-array pairs across both modes. Diagnostic builds explicitly
disable the shortcut, retain complete recurrence records, and are tied to the
production calculation by those bitwise parity tests. The full native gate passes
490 tests with two existing warnings in 592.55 seconds. The expanded 92-test
targeted suite covers 30 mode cases added after full collection; final collection
contains 520 tests, all covered.
Signed soil/routing acceptance and clipping remain open; no release authorized.


## Channel plane/element working-flux alias

After native checkpoint e6dc19008, actual two-channel WATBAL/WSHDRV/WSHCHR
controls identify inherited runoff entering a receiving channel's dry hourly
soil calculation. WSHDRV's completed-channel element slot can equal the next
channel's plane slot. WSHIRS resets runoff only when called and assigns chnrun
only for local rainfall excess; daily-global initialization cannot protect
later channels from same-day element writes.

The bounded candidate initializes both current-plane fields after WSHCQI,
before optional WSHIRS. No source timing, event gate, soil store or MC rule
changes. A read-only trace attributes 1.54834 m³ of a receiving-channel
infiltration request to the inherited runoff depth. Three-channel wet controls
also expose 26.91–26.99 m³ of false local rainfall runoff in a receiving channel
with no local excess; its rtrans error cancels in net routing forcing but makes
component accounting wrong.

Scientific ablations compare baseline, each reset alone and both. All 96
full two-year executions complete: 48 observed and 48 observer-off siblings,
with 1800 exact native-output file pairs. All 12 scenarios preserve upstream
channel output across lanes. Genuine local runoff remains produced by the
normal routines. Full native suite passes 520 tests (two existing warnings) in
618.33 seconds, including year100/day365 within the unchanged 900-second gate.
All 29 paired replays, 12 watchlist cases, both host smokes and system ELF
loaders pass. Seven final portable integration tests pass in 115.93 seconds, independently
reviewed with no blocking findings; all 527 collected tests are covered. Accepted clipping remains after the correction, so neither
this alias repair nor the earlier MC checkpoint closes signed soil/routing
acceptance. Retain the active WEPPpy package and ADR-0101.
