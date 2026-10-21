# Audit physical water from each OFE through watershed routing

This living plan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective,
and update the package tracker at handoff.

## Purpose / Big Picture

Establish whether current hydrology is sensible and conserves water from soil
profiles through hillslope PASS files to channels and the watershed outlet.
An OFE is a modeled hillslope segment. Dp is drainage below its soil profile;
ET is plant, soil and residue evaporation combined. Q and QOFE are differently
normalized surface runoff outputs; lateral flow transfers water between soil
profiles and leaves at the last OFE. These distinctions must be verified against
the actual executable, not inferred from column names or earlier branch behavior.
The operator explicitly excludes Ash. Calendar repair does not prove conservation.

## Progress

- [x] (2026-10-21) Reviewed predecessor scopes and exact release writer paths.
- [x] (2026-10-21) M1: Freeze source identities, control volumes, inputs and coverage matrix.
- [x] (2026-10-21) M2: Execute paired single/multiple-OFE daily/hourly cases and source audit.
- [x] (2026-10-21) M3: Independent OFE/PASS, groundwater-recurrence and channel ledgers; unmeasured initial/interception stores explicitly retained as limits.
- [x] (2026-10-21) M4: Validate diagnostic sensitivity, investigate failures, report conclusions.

## Surprises & Discoveries

Release 261021 ordinary daily/hourly QOFE is runoff * effective_length /
local_length, whereas Q uses cumulative_length. Earlier HBP development writers
used aliases. Use release sources in `/workdir/wepp-forest-release-20261009`, not
the dirty `/workdir/wepp-forest` HBP checkout, for every scientific assertion.

Read-only probes independently locate missing water, rather than adding a
balancing residual to ET, Dp or exported flow. Printed channel balance is an
identity; native-rate integration differs substantially. Nonzero groundwater
initialization exposes a last-OFE area defect hidden by zero initial storage.
Audit-tool development failures are retained in `artifacts/commands.md`.

## Decision Log

2026-10-21: Start a separate physical audit. The prior channel investigation
stopped at a calendar defect and explicitly did not establish conservation.
Preserve that history. Scope includes complete current-model tracing and fresh
controlled replays, excludes Ash and unrequested model corrections.

2026-10-21: Complete as a diagnostic audit with four unresolved native defects.
Do not certify watershed correctness or silently repair formulas. Keep tested
ordinary geometry separate from untested contour/tile/impoundment conditions.

## Outcomes & Retrospective

Diagnostic audit complete. Eighteen watershed configurations complete 44 years;
three nonzero-groundwater hill variants and ten compiled CHRQIN probes complete.
OFE transfer and selected PASS checks pass. Four native defects are reproduced:
missing channel-local rate contributions, flat-hydrograph volume loss, discarded
hourly infiltration remainder and terminal-area groundwater initialization.
Read-only channel observations pass comprehensive scientific parity in ten
configurations; hourly probes pass H1 output parity in three layouts. Five
corruption controls pass. No model repair, deployment or correctness certification.
See `artifacts/findings.md` and the tracker for exact claims and limitations.

## Context and Orientation

WEPPpy is `/workdir/wepppy`. Released paired binaries are
`wepp_runner/bin/wepp_261021` and `wepp_261021_hill`. Source commit is
`a87925df9ffe6ebb928e126395dd159d484285fa`; artifact commit is
`6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb`. Inspect `src/watbal.for`,
`watbal_hourly.for`, `contin.for`, `wshpas.for`, `wshred.for`, `wshcqi.for`,
`wshchr.for`, groundwater routines and their active callers in that source tree.
The older package `20261021_watershed_channel_routing_closure` retains controlled
input generation and workbook accounting, but its HBP observations are not direct
proof for this ASCII release. Ayush did not provide original input decks.

## Plan of Work

### M1 — Freeze inputs and define control volumes

Record binary hashes, source identity, run cards, shared inputs, dimensions,
climate dates and actual execution mode. Reuse controlled generators with an
explicit ASCII run-card conversion. Retain copied decks outside git and manifests
inside artifacts. Use 100 m by 100 m homogeneous hillslopes split into one OFE,
50/50, 60/40, 40/60 and 20/30/50 lengths, then unequal tributaries and a cascade.
Compare each case against its own water balance; splitting need not preserve
hydrology because discretization affects process calculations. Run both daily and
hourly execution for full configured periods. Mark positive tile, contour and
variable-width coverage explicitly; do not infer their correctness from zero flux.

Define separate soil, whole-hillslope, groundwater, channel and combined-domain
ledgers. Internal surface and lateral transfers cancel by volume. Dp is a soil
export but can recharge groundwater: do not count it as an external domain loss
alongside subsequent groundwater discharge. Include interception, snow, frozen
and liquid soil water, channel storage and other active stores. Unknown is not zero.

### M2 — Trace and execute

Read exact producer and consumer code and bind quantities to units, geometry,
time interval and branch. Rebuild only isolated source copies if observations
are needed. Use existing diagnostics first; add read-only probes without changing
expressions, precision, thresholds, state updates or output schemas. Compare
baseline with observation build off and on using exact scientific output hashes.
Record fresh paired hill/PASS/watershed success and complete calendars; failed
cases remain failures even when the process returns zero. Keep release files fixed.

### M3 — Build independent ledgers

Read WAT rows per OFE and day, actual serialized ASCII PASS records, loaded
routing arrays, channel transfers and final outlet. Verify local ET/Dp by area,
terminal lateral by terminal area, and surface runoff by producer-specific
normalization. Quantify event-filter gaps separately from routing losses.
Integrate hydrographs using actual timestamps independently of published daily
volume. Evaluate input minus output minus storage increase for each boundary,
and compare signed, absolute, worst-day and cumulative residuals. Derive
bounds from printed precision, native floating-point representation and measured
integration errors. Never fit tolerances to a failing residual.

### M4 — Validate and report

Inject duplicated/missing transfers, wrong area factors, one-day shifts and
reversed storage signs only into copied offline ledgers; ensure each is detected
with expected magnitude. Include a hand-computable balanced control. For every
failure identify the first divergent boundary and smallest reproducible case.
Report source correctness, empirical accounting and physical plausibility as
separate claims. Preserve unresolved stores and failed coverage; do not claim
universal conservation. Close only after requested cases are dispositioned with
actual accounting evidence, not solely dates or aggregate publication identities.

## Concrete Steps

From `/workdir/wepppy`, run the case-generation and audit scripts retained in this
package’s artifacts with `/workdir/wepppy/.venv/bin/python` and
`PYTHONPATH=/workdir/wepppy`. Record exact commands and output roots in
`artifacts/commands.md` when scripts exist. Run
`wctl doc-lint --path docs/work-packages/20261021_watershed_physical_water_audit`
and `tools/check_agents_size.sh AGENTS.md` before handoff. Native compilation,
when needed, uses `/usr/bin/gfortran` and the existing sequential make targets
in isolated copies. No branch switching or live-output overwrite.

## Validation and Acceptance

Acceptance requires complete per-case input/output provenance, calendar matching,
source-backed per-OFE normalization, explicit physical versus delivered PASS
quantities, independently measured channel transport, justified residual bounds
and successful corruption controls. If observations are added, three-way parity
is mandatory. A reproducible defect is a valid finding but not proof of repaired
routing. No production application changes are planned, so application test
suites cannot substitute for model accounting and are not required for this audit.

## Idempotence and Recovery

Use new attempt directories under `/workdir/watershed-physical-water-audit-20261021`.
Never overwrite live projects or earlier artifacts. Retain failures and large
traces outside git with hashes. No dependency, runtime API or persisted schema
changes. Unknown scientific terms remain explicit until measured.

## Artifacts and Notes

Store source map, case matrix, commands, manifests, ledger schema, audit scripts,
summary receipts and findings under this package’s artifacts directory.

## Interfaces and Dependencies

Reuse installed Python/numpy/pandas and existing native output readers. Offline
ledger rows need case, date, element/OFE, boundary, flux/storage name, units,
value, normalization and source identity. No new runtime dependency is needed.

## Revision Notes

2026-10-21: Initial executable scope records the operator’s emphasis on Dp,
lateral flow, ET and QOFE through the terminal OFE, with Ash excluded.

2026-10-21: Completed generated-output audit and controls; retained four defect reproductions and explicit non-certification.
