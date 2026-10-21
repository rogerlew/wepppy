# Watershed channel routing closure findings

## Confirmed defect: schema-2 calendar selection

The captured native build consumes schema-2 PASS slots on the wrong routing
dates after the first non-leap year. This is a generated-artifact diagnosis,
not a simulation correction or a claim about every deployed binary.

Source identity: `wepp-forest` HEAD
`04f1c4d26bcef217009c124151f877dcbf3985cb`, with baseline provenance and
observation patch retained in this package. Exact replay binary hashes are in
`parity.json` and each retained `execution.json`.

The writer's `densify_records_schema2` in
`fpm-src/hillslope_binary_pass_legacy_adapter.f90` creates 366 slots per year,
including synthetic day 366 in non-leap years. The reader's
`hbp_reader_load_next_day` in `fpm-src/hillslope_binary_pass_reader.f90` advances
one slot per call without matching the routing date. `src/wshdrv.f90` advances
through actual represented calendar days. Calendar keys exist in the reader,
but are not used to select the requested day.

All five controlled 1980–2023 cases completed 44 configured years. The first
divergent boundary is PASS-to-loaded-array date selection on **1982-01-01**,
when routing consumes synthetic **1981-366**. Every observed loaded volume
matches the sequential serialized slot exactly after native real conversion.
Date-keyed comparisons fail. Writer-to-payload quantization and terminal lateral
area conversion pass their declared precision checks.

For the 60/40 case, intended lateral inflow on 1982-01-01 is
**45.785182953 m3**, but the loaded value is **0 m3**. In the single-OFE case,
the corresponding intended value is **40.665725708 m3**; it appears in the
loaded array one day later. Splitting into OFEs is not necessary to trigger
the calendar defect.

The controlled watershed consumes 16,071 real days from a 16,104-slot payload,
ending at serialized 2023-333 and leaving 33 slots unread. For 60/40, that gross
tail contains **2,224.182955741 m3 surface runoff** and
**1,919.952960972 m3 lateral flow**. These are already selected PASS deliveries,
separate from measured event-filter omissions of **319.754887953 m3 surface**
and **0.199968196 m3 lateral** over the configured period.

Synthetic slots can retain copied groundwater flux. Therefore unread-tail
baseflow is not automatically net missing baseflow. The audit reports physical
calendar totals, consumed synthetic volumes, and gross unread-tail volumes
separately. Do not sum them as independent losses.

## Full-period replay and parity results

Nine successful cases have exact baseline/off/on scientific-file parity: five
OFE configurations (35 files each), daily water balance (34), unequal tributaries
(59), two-channel cascade (59), and the 28-hillslope `tight-orthodontist` project
(388). Controlled/topology cases complete 44 years; the real project completes
all 43 years, 1983–2025. The failed impoundment has exact file parity but is not
counted as a completed simulation.

All 28 real-project hillslopes show the first calendar mismatch on **1984-01-01**,
consuming synthetic **1983-366**. Every audited hillslope in all nine successful
cases matches sequential payload readback exactly; terminal lateral-area checks
and writer quantization checks pass. This establishes the defect beyond the
single-channel synthetic setup, without establishing deployed-binary prevalence.

The retained ledger has 160,345 channel-day records. All fit the declared
publication-arithmetic bound. The real outlet's maximum absolute residual is
0.0244827271 m3, with total absolute residual 3.2201020345 m3; signed totals alone
would conceal cancellation. Exact values and worst records are retained in
`residual_summary.json`. Independent correctness review passes investigation
closure; COR-01 remains an open model defect. See `correctness_review.md`.

## Channel arithmetic is not a domain conservation proof

The controlled channel residuals fit the declared single-precision arithmetic
screen, including both signs and accumulated absolute error. However,
`src/wshdrv.f90` sometimes derives transmission loss from inflow minus routed
outflow, and `src/wshchr.f90` derives discharge and storage through balance
identities. Many published loss values are negative; counts are retained in
`residual_summary.csv`. A near-zero published residual does not independently
validate infiltration physics, hydrograph integration or complete watershed
water conservation, and it does not detect the upstream date-selection defect.

The real-project channel trace covers the configured outlet element 39; it is
not an all-channel network ledger. The controlled cascade traces both channels.
The retained `volume_ledger.csv` is a channel publication ledger, not a complete
soil/groundwater/impoundment/domain ledger. Unmeasured initial soil/interception
stores and independent channel source/loss terms remain unresolved. No missing
term was assigned zero to obtain a passing balance.

## Workbook accounting findings

Roger confirmed that Ayush did not supply the input decks. The workbook is
retained and hashed, but its executable and original input provenance are
unknown. Its contents cannot establish which native defect affected that run.

Raw daily areas are 1,690.50 and 1,120.88 m2. Summary formulas use rounded
60/40 fractions and some averages of internal flows; summary single-OFE geometry
also differs from daily Area. With local ET/Dp weighted by actual area, terminal
Q used once, and terminal lateral depth multiplied by terminal/total area, the
annual P-minus-ET-minus-Dp-minus-exports screen is **−1.2834 mm/year** for two
OFEs and **−1.3425 mm/year** for one OFE. Initial storage is unavailable, so these
screens must not be labeled closed balances. `workbook_audit.json` retains raw
counts, areas, annual values and exact workbook formulas.

## Reproduction and retained evidence

Use `/workdir/wepppy/.venv/bin/python` with `PYTHONPATH=/workdir/wepppy`.
`replay_controlled.py`, `replay_project.py` and `replay_extensions.py` retain
complete input manifests and process results. They create new attempt roots;
do not point preparation at an existing attempt. `audit_replays.py` reads actual
HBP files through the installed native interchange reader and joins native
observations. `finalize_evidence.py` regenerates aggregate receipts and ledgers.

The principal reproduction for the wrong-date boundary is:

    PYTHONPATH=/workdir/wepppy /workdir/wepppy/.venv/bin/python \
      docs/work-packages/20261021_watershed_channel_routing_closure/artifacts/audit_replays.py \
      --root /workdir/watershed-channel-routing-closure-20261021/controlled-on \
      --output /workdir/watershed-channel-routing-closure-20261021/audit

Evidence locations and hashes are in `provenance.json`, `parity.json`,
`case_matrix.csv`, `retained_ledgers.json`, and the per-attempt input/execution
manifests. Baseline/off/on comparisons include scientific files written under
both `output/` and `runs/`. Only opt-in observation files are excluded.

## Coverage limits and separate follow-up

The six-year `up-pedantry` replay traps in `evappm.for:195` during year six;
it does not produce a complete PASS trajectory. The impoundment fixture stops
at `WB36 M3A route04 m4_status_ok=false`; its balance is unresolved. The first
real-project selection has a zero-HMAX channel management record rejected by
the captured binary. Failed attempts and legacy run-card prompt errors are
retained. None was repaired by changing simulation equations or parameters.

Positive tile drainage, contour/variable-width geometry, schema-1 delivery,
centurial calendars, independently integrated channel hydrographs, and complete
domain storage remain outside demonstrated coverage. Original workbook inputs
are unavailable. The defect finding does not establish historical prevalence.

The smallest separately authorized remediation would make schema-2 day
selection honor the actual calendar key while preserving the fixed-slot file
contract. Acceptance should test non-leap transitions, all flux components,
final-day consumption, schema-1 compatibility, and affected project artifacts.
Historical impact assessment must first identify deployed binary/source
lineages. No remediation, release, vendoring, deployment or live-run mutation
was performed by this investigation.
