# WEPP Release `wepp_260514` / `wepp_260514_hill`

**Release date (UTC):** 2026-05-15
**Source commit:** `62c2102efffc36f142689dfbffa5296b20780d33`
**Source repo:** `wepp-in-the-woods/wepp-forest`
**Functional-state tag:** `wb-p26-shapeA-functional`
**Toolchain:** pinned `/usr/bin/gfortran` per `docs/release-checklist.md`
**Build provenance:**
- `wepp_260514` SHA256: `d2505484e56c9976c4e7f04aa9f58ee171ea0f87c8b3e96c74585934bc11c7f9`
- `wepp_260514_hill` SHA256: `4e2acc806963100a0345893f2828669a60198bc9fb3dad8d022efec8a492c403`
- Sidecar JSON manifests: `release/wepp_260514.json`, `release/wepp_260514_hill.json`
- Sidecar JSON SHA256: `3870d1e4271d8a0362b255cac47d7f47b9d53324c75b71f0bcff1ffe21a24a7f`,
  `ceccce0b06d8b9592e31d654feca5d9793527718fba47d49688491e854fec108`

**Deployment posture:** deployable. This is the first deployment-class
release since `wepp_260430`. The intermediate binaries `wepp_260319`
through `wepp_260513` were test-vendored for evaluation only and were
not promoted to operational use. `wepp_260514` is the candidate
recommended for promotion when downstream evaluation completes.

## Executive summary

`wepp_260514` is the first release to ship the WB modernization
program's process-kernel architecture as the authoritative
water-balance trajectory. Approximately 20,100 lines of new
modern-Fortran code (free-form `.f90`, `implicit none`, modules,
derived types) replace the legacy `watbal.for` / `watbal_hourly.for`
monolithic routines as the authoritative water-balance code path,
accompanied by approximately 11,500 lines of test code under a
test-first authoring discipline. Exact counts (from `cloc` against
the source tree at this release): `src/*.f90` 22 files / 6,114
lines of code; `fpm-src/*.f90` 12 files / 13,985 lines of code;
`fpm-test/*.f90` 59 files / 11,471 lines of code. Six real
water-balance defects identified during the modernization are repaired,
all proven to close mass at floating-point noise on their
originally-failing tuples. A runtime correctness gate (Phase 3
fail-fast) now refuses to complete any run that exhibits the
clamp-plus-preserve mass-violation pattern with non-trivial input
suppression. Operational impact on well-conditioned runs is
unchanged; impact on rain-on-snow, multi-OFE hillslope, and
clamp-active boundary days is described in detail below.

## Highlights

- **Lambda-kernel decomposition of water-balance physics (WB-03
  through WB-08A).** The legacy monolithic accounting routines have
  been decomposed into a set of small, single-responsibility process
  kernels — canopy, snowpack, soil moisture, runoff, percolation,
  evapotranspiration, transport-capacity policy. Each kernel declares
  its full input set, full output set, and an explicit conservation
  invariant. The decomposition is what makes per-kernel unit testing,
  per-step closure auditing, and the dual-basis closure gate possible.
  See [`docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/`](../docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/package.md)
  for the architecture specification and the unit-test matrix that
  was frozen before any kernel implementation began.

- **Single-trajectory process-kernel ownership of authoritative
  water-balance output (WB-08A).** Earlier in the WB program, the
  process kernels ran beside the legacy code under an observability
  flag. WB-08A completed the cutover: process kernels now own the
  authoritative water-balance row that downstream consumers read,
  with legacy code preserved for traceability and rollback only. The
  WB-08 attempt blocked correctly on a hybrid-trajectory failure and
  closed `no-go`; WB-08A repaired the trajectory-coupling defect under
  the `trajectory-ownership-contract` (`docs/contracts/trajectory-ownership-contract.md`)
  and re-closed the full 1,166-hillslope WB-05B forest corpus.

- **Six water-balance defect repairs.** Four were legacy defects the
  closure audit surfaced once it was instrumented (transport-capacity
  bypass, snowmelt double-count, missing interception export, and
  rain-routing conflation in the legacy winter aggregator); two were
  new-code defects in the modernization caught by the dual-basis gate
  before promotion (process-kernel storage/runoff reconciliation, and
  the WB-18 / WB-30 baseflow-preservation interaction). See the
  per-fix subsections under **Defect repairs** below for closure
  evidence.

- **Phase 3 fail-fast enforcement (correctness-over-completion).** The
  runtime now halts immediately when an input is clamped at the
  kernel boundary, a corresponding output is preserved at full value,
  and the suppressed input exceeds the 0.1 mm noise floor — naming the
  failing tuple in a structured one-line message and exiting with code
  206. Legacy WEPP took the completion-over-correctness path, where
  unexpected conditions produced silently-compensating wrong-but-plausible
  outputs. `wepp_260514` makes that impossible. The architectural
  invariant is recorded in [`docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md`](../docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md).

- **Optional `InterceptionStorage` column in `H.wat`.** Live-plant
  interception and surface-residue water are real model states that
  the legacy export was not writing. They are now exported as one
  optional trailing column gated by contract-change-control entry
  `WB02-CC-20260504-02`. Parsers keyed on column header are
  unaffected; parsers keyed on positional column count should declare
  whether they expect the new column.

- **HBP hillslope pass family is the authoritative pass format;
  watershed `pw0` master-pass file is no longer required in process
  mode.** The binary hillslope pass family (`H*.hbp`, schema 1.0,
  current spec implementation incorporating the v2 revisions) is
  emitted by the hillslope binary and consumed directly by the
  watershed binary via the new direct-HBP reader. The previous
  ASCII pass family (`H*.pass.dat`) and the master-pass workflow
  that required a `pw0` watershed pass file are retired in process
  mode; the legacy adapter is preserved for downstream consumers
  that have not yet migrated. The full HBP contract surface is
  documented under `docs/contracts/`. See **Output schema and
  downstream compatibility** below for the consumer-side detail.

- **Functional-state tag `wb-p26-shapeA-functional`.** All six defect
  repairs, the Phase 3 fail-fast, the lambda-kernel architecture,
  and the HBP authoritative pass family are anchored at commit
  `64b86eaf` under this tag. The tag is the rollback anchor for
  any subsequent work that depends on the current functional state.

## Scientific basis

The physics WEPP represents is unchanged. The references that
underpin WEPP's water-balance physics, including the most recent
program-internal reference (`docs/McGehee_2023_WEPP-WQ_Model_Development_Reference.md`),
remain authoritative for the model's hydrologic representation. What
changed is the structure that the physics is implemented in and the
discipline that the conservation invariants are enforced under.

Specifically:

- **Mass conservation as a normative invariant.** The clamp-plus-preserve
  mass-closure invariant ([`docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md`](../docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md))
  formalizes the requirement that any operation which suppresses an
  input must reconcile its dependent outputs and storage delta so that
  closure holds on the normalized domain. This is not a new
  physical principle; it is the explicit specification of an invariant
  that the legacy code had been honoring at the aggregate level and
  the modernization initially violated through unspecified interactions
  between two physically reasonable refinements (the WB-18 snowmelt
  cap and the WB-30 baseflow preservation).

- **Per-channel attribution as an audit requirement.** The defect
  repairs in this release surface several cases where water was being
  routed through the wrong attribution channel (snowmelt counted as
  external input rather than internal transfer, rain water counted as
  snowmelt during rain-on-snow events, interception storage not
  exported at all). The physical quantity of water has not changed in
  any of these repairs; the attribution has. Downstream consumers
  that compute residuals from `H.wat` should follow the audit
  convention documented in defect #2 below (`P + Irr` external input
  with `Snow-Water` in the storage delta).

- **Floating-point discipline.** The new kernels run in 64-bit
  precision (`real64`) for conservation arithmetic. The adapter
  performs precision conversion at the boundary into and out of
  legacy single-precision storage; the closure audit never sees the
  legacy precision loss. Post-repair residuals on the originally
  failing tuples sit at approximately ±5 × 10⁻¹⁵ mm — the
  floating-point noise floor — rather than at the order of the
  closure threshold.

## Architectural changes

The substantial structural change in this release is the lambda-kernel
decomposition described above. Three structural conditions specific to
the legacy `watbal.for` / `watbal_hourly.for` made them difficult to
audit, and none of them was the physics. All three are now resolved:

1. **Two near-identical code paths** (daily and hourly) duplicated
   most of the physics terms but not quite all of them, and over time
   small drifts accumulated between the two. In the new architecture,
   daily and hourly schedulers share the same physics kernels; the
   hourly path adds one extra policy surface (transport-capacity
   enforcement) on top, instead of duplicating the entire calculation.

2. **Common-block state passed silently in and out**, which made it
   impossible to enumerate the inputs and outputs of any one piece of
   the calculation. The new kernels are modules with explicit
   interfaces; closure state, flux state, and per-kernel status are
   passed as named derived types (`wb_closure_state`, `wb_flux_state`,
   `wb_process_status`). Unit tests, once impossible, are now mechanical
   to write.

3. **No closure residual was emitted**, so a defect could only be
   discovered by watching aggregate outputs over many runs and
   noticing long-term balance drift. The new adapter emits a closure
   residual on every step. The closure audit machinery, the runtime
   conservation guard, and the Phase 3 structural-pattern fail-fast
   are all natural consumers of that residual.

The legacy `watbal.for` and `watbal_hourly.for` routines remain in
the source tree for historical traceability and rollback, but are no
longer the authoritative water-balance code path. Trajectory
ownership for the water-balance row is now held by the process
kernels.

## Dual-basis closure accounting

The dual-basis closure system is the load-bearing acceptance gate
for every change to the water-balance code, including every defect
repair in this release. The system rests on a simple physical
principle expressed in two independent ways, and it works because
the two expressions can be checked against each other.

### The water-balance equation

For any Overland Flow Element on any day, conservation of mass
requires that the water that entered the system, minus the water
that left, equals the change in the water that was stored:

> inputs − outputs − Δstorage = 0 (within numerical noise)

In the modernized kernel, the six input terms that count as
external-or-incoming water are:

| Symbol      | Meaning                                                |
|-------------|--------------------------------------------------------|
| `rain`      | Liquid rainfall on the OFE                              |
| `wmelt`     | Snowmelt water released from the snowpack into the soil |
| `irdept`    | Irrigation depth applied to the surface                 |
| `iraplo`    | Sprinkler-irrigation overlay component                  |
| `runoff_in` | Surface runoff arriving from the upslope OFE            |
| `subrin`    | Subsurface return flow arriving from the upslope OFE    |

The six output terms that count as water leaving the OFE are:

| Symbol     | Meaning                                                   |
|------------|-----------------------------------------------------------|
| `q` / `qofe` | Surface runoff leaving the OFE                          |
| `ep` + `es` + `er` | Evapotranspiration (canopy + soil + residue)      |
| `sep`      | Deep percolation (water leaving the soil profile downward)|
| `sbrunf`   | Subsurface return flow / baseflow component               |
| `drainq`   | Tile-drainage outflow                                     |
| Lateral    | Lateral subsurface flow to the downslope OFE              |

Δstorage is the change between this step and the previous step in
soil-layer moisture (per layer), frozen-water mass (per layer),
canopy and residue interception storage, and snowpack water-equivalent.

Snowmelt deserves a specific note: it is **not** an external input
to the watershed, only to the soil column. The snowpack itself is
storage; when its water-equivalent decreases by some amount and that
amount appears as `wmelt`, the model is moving water internally from
one storage compartment to another. Treating it as both an input
and a storage decrease is the snowmelt double-count defect (#2) that
the WB-05E repair eliminated.

### The two bases

The dual-basis closure system computes the residual of the equation
above twice, in two independent ways, and accepts a change only if
both residuals close.

**Kernel basis (in-memory, 64-bit, computed as the model runs).**
While the model is running, each process kernel emits the values it
saw for inputs, outputs, and storage in 64-bit floating point at the
end of every accounting step. The closure guard module
(`watbal_closure_guard`) reads those values directly from kernel
state and computes the residual against the equation above. This is
the strictest expression of the conservation invariant: the physics,
as actually implemented in the kernel code, must conserve mass in
its own internal arithmetic.

**Interchange basis (post-run, computed from exported terms only).**
After the run finishes, the closure audit reads the values that were
written to the public output files (`H.wat`, `H.pass`, and a small
number of companion files) and recomputes the residual against the
same equation. This is the conservation invariant as it appears to a
downstream consumer who does not have access to internal kernel
state — only the published numbers.

The kernel basis answers: *did the code conserve mass while it ran?*
The interchange basis answers: *can a reader of the public outputs
verify that mass was conserved?*

### What it means when the two bases disagree

Both residuals being close to zero is the only acceptable outcome.
When they disagree, the disagreement isolates which side of the
contract is broken:

- **Kernel closes, interchange does not.** The physics is internally
  consistent, but the export is incomplete. Some real state inside
  the kernel is not being written to the public output, so the
  external reader cannot reconstruct what the model knows. This is
  the export-contract defect class. Defect #3 in this release —
  the missing `InterceptionStorage` export — is exactly this shape.
- **Interchange closes, kernel does not.** The export looks
  consistent, but the kernel is internally inconsistent. The
  exported numbers happen to balance because of some compensating
  arithmetic, but the underlying physics has a mass leak. This is
  the physics-contract defect class. It is the rarer of the two and
  the more dangerous, because a downstream consumer cannot detect
  it from the published outputs alone.
- **Both fail.** The most common case during modernization. Defect
  #4 (process-kernel storage / runoff reconciliation) failed both
  bases with the same residual (`−15.8066 mm` on hillslope `H0001`),
  which is itself diagnostic: both bases failing with the *same*
  value means the export is faithfully reporting a kernel that is
  internally inconsistent, rather than the two sides drifting
  independently.

This is why the system is structured as two bases rather than one.
A single residual computed in either basis would catch many defects,
but it could not distinguish between an honest model with a broken
export, and a faithful export of a broken model. The two together
attribute the defect to its source.

### How the dual-basis residual is enforced at runtime

Three layers of enforcement sit on top of the residual:

1. **Per-step closure assertion (`watbal_closure_guard`,
   `ERROR STOP 205`).** Every accounting step computes the kernel
   residual; if its absolute value exceeds the 1.0 mm material
   non-closure threshold, the run halts immediately and emits the
   tuple `(year, day, OFE, hillslope)` plus the input/output/storage
   breakdown. This is the runtime conservation guard added in WB-05F.
   It is what caught the WB-05F new-code defect during scoreboard
   replay before any operational run was issued against it.
2. **Structural-pattern fail-fast (Phase 3, `ERROR STOP 206`).** As
   of this release, the runtime also watches for the structural
   pattern that *produces* residual failures — a clamp-plus-preserve
   co-occurrence with non-trivial input suppression — and halts on
   the pattern before the symptom develops. This is the
   correctness-over-completion gate; it catches defects in the same
   class one step earlier than the residual assertion.
3. **Post-run interchange audit (`tools/run_hillslope_watchlist.py`,
   WB-05B forest closure sweep).** After every run, the interchange
   residual is recomputed from `H.wat` / `H.pass` and asserted
   against the same threshold. This is the canonical regression
   gate: a release that breaks any cohort's interchange closure is
   not promoted.

Acceptance bands and thresholds are frozen in the WB-02 acceptance
manifest. The current thresholds are:

- **Material non-closure threshold:** 1.0 mm — the daily-residual
  threshold above which a step is flagged as a defect seed.
- **Single-OFE acceptance band:** 40 mm — the maximum residual on
  any single OFE on any single day for a release to be accepted.
- **Phase 3 floor:** 0.1 mm — the suppressed-input magnitude above
  which a clamp-plus-preserve co-occurrence becomes a hard error.
- **Numerical-noise floor:** approximately 10⁻¹⁵ mm — the
  floating-point precision floor of the 64-bit kernel arithmetic.
  Post-repair residuals on every defect class in this release sit
  near this floor.

Threshold tuning is governed by contract change-control. Tuning a
threshold to suppress a class of firings is explicitly prohibited
by the architecture-note record at
[`docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md`](../docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md);
firings are diagnostic information and must be investigated rather
than hidden.

### Why the two bases are independent

The kernel and interchange residuals are not computed from the same
arithmetic, and that is the entire point. Specifically:

- The kernel residual is in `real64` from in-memory state. The
  interchange residual is computed from `H.wat` / `H.pass` columns
  written in legacy single precision, after the precision conversion
  at the adapter boundary. A discrepancy at the precision-conversion
  boundary would show up as the kernel basis closing tighter than
  the interchange basis.
- The kernel residual can include state that the export contract has
  declared but not yet written; if a kernel adds a new state term and
  the export contract is not updated, the kernel will close but the
  interchange will not. The dual-basis gate forces export-contract
  updates to happen at the same time as kernel changes.
- The kernel residual is computed by the same code that produces the
  outputs. The interchange residual is computed by separate code that
  reads only the public file format. The two cannot quietly agree on
  a wrong answer, because they do not share an arithmetic path.

This independence is the trust foundation of the closure-audit
discipline. A model is allowed to be accepted when the kernel side
*and* the interchange side, computed by independent code paths
against independent representations of the same physics, both agree
that mass is conserved.

## Lambda-kernel inventory

The modernization decomposed the legacy monolithic water-balance and
channel-routing routines into 23 named single-responsibility kernels
across two domains. Every kernel declares its full input set, full
output set, and an explicit status structure carrying its conservation
or contract invariants. Each kernel has a corresponding unit-test file
under `fpm-test/` that asserts the kernel's invariant on canonical
input vectors plus documented edge cases.

### Process kernels (`fpm-src/watbal_process_kernels.f90`)

Ten kernels handle the per-step water-balance accounting for a single
Overland Flow Element. Inputs come from the daily or hourly adapter;
outputs feed the closure guard and the trajectory-owned export path.

- **WBK-01 — Input normalization.** Clamps and reconciles the raw
  liquid-water inputs (rain, snowmelt, irrigation, upstream runon,
  subsurface inflow) by physical-availability bounds. This is the
  kernel that emits `WBK01_MELT_SNOWPACK_CAP` when raw snowmelt
  exceeds available snowpack mass; the post-Shape-A clamp-plus-preserve
  invariant is enforced against the status it produces.
- **WBK-02 — Storage bounds.** Applies capacity caps to soil, frozen
  water, and interception storage; routes excess into spillover
  signals. Defines the storage envelope the rest of the kernels
  reconcile against.
- **WBK-03 — Evapotranspiration accounting.** Partitions ET demand
  across canopy interception, soil evaporation, and residue
  evaporation under the active vegetation policy.
- **WBK-04 — Percolation and deep seepage.** Computes deep
  percolation and seepage from soil-layer storage using saturated
  hydraulic conductivity and gravitational gradient.
- **WBK-05 — Lateral transfer.** Computes lateral subsurface flow
  between soil layers and downslope to the next OFE; emits the
  transfer residual that the closure guard uses to balance lateral
  routing.
- **WBK-06 — Tile and surface drainage.** Applies tile-drain and
  surface-drainage policies to soil-layer storage.
- **WBK-07 — Runoff reconciliation.** Reconciles per-OFE runoff
  (`qofe`) to be locally consistent with the OFE's surface flux
  rather than the watershed-summed `q`. This is the kernel
  WB-05F repaired.
- **WBK-08 — Storage reconciliation and closure diagnostics.**
  Applies the shortfall correction when output exceeds storage
  capacity, scales fluxes proportionally (including baseflow under
  the post-Shape-A invariant), and emits the kernel-side closure
  residual the dual-basis gate consumes. This is the kernel the
  WB-30 D06-preserve change touched and the Shape A fix repaired.
- **WBK-09 — Hourly transport-capacity policy.** Enforces the
  per-OFE hydraulic transport cap (`q-cap`) on hourly surface
  flow. This is the kernel WB-05A repaired.
- **WBK-19A — Green-Ampt runoff partitioning.** Five sub-kernels
  (storage terms, partition, runon classify, runon `rochek`,
  recession infiltration, depression storage step) implementing the
  Green-Ampt infiltration model for partitioning rainfall into
  runoff and infiltration on hillslopes with upstream runon.

### Channel-routing kernels (`fpm-src/watbal_route_kernels.f90`)

Thirteen kernels handle watershed channel routing, replacing the
legacy fixed-form routing routines (`wshchr.f90`, `wshrun.f90`,
`wshimp.for`, `wshpek`, etc.) under the WB-3x watershed-modernization
chain.

- **WBK-Route-01 — Channel geometry.** Resolves the routed-channel
  geometry (length, slope, width, roughness) used downstream.
- **WBK-Route-02 — Transmission loss.** Applies channel
  transmission-loss policy and updates channel volume.
- **WBK-Route-03 — Wave propagation.** Routes the discharge peak
  through the channel using the selected wave-propagation method.
- **WBK-Route-04 — Cascade composition.** Composes routed flow
  through cascading channel elements.
- **WBK-Route-05 — Baseflow contribution.** Computes the baseflow
  contribution to channel flow.
- **WBK-Route-06 — Publish balance.** Publishes the channel-routing
  balance residual against the configured nonclosure threshold.
  This is the kernel the `20260513_route06_publish_balance_nonclosure`
  ablation package was scoped against; the resolution scaled the
  nonclosure threshold by contributing watershed area while
  preserving a hard minimum floor.
- **WBK-Route-07 — Legacy shim adapter.** Bridges the modern
  routing kernels to the legacy routing API surface for downstream
  consumers that have not yet migrated.
- **WBK-Route-08 — Orchestrator.** Sequences the routing kernels
  across the watershed topology.
- **WBK-Route-09 — Inflow aggregation.** Aggregates upstream
  hillslope and channel inflows into the current routing step's
  inputs.
- **WBK-Route-10 — Summary accumulator (kernel).** Accumulates
  per-step routing summary statistics for downstream reporting.
- **WBK-Route-11 — Time of concentration.** Computes the channel
  time of concentration.
- **WBK-Route-12 — Peak flow orchestrator.** Sequences the peak-flow
  calculation across the routing methods.
- **WBK-Route-14 — Peak summary accumulator.** Accumulates per-event
  peak-flow summary statistics.

### Adapter and infrastructure modules (`fpm-src/`)

Three adapter modules and supporting infrastructure connect the
kernels to the rest of the codebase. These are not themselves
physics kernels but are required to enforce the kernel/adapter
boundary that prevents common-block state from leaking into the
process kernels.

- **`watbal_daily_adapter`** — bridges the daily scheduler to the
  process kernels.
- **`watbal_hourly_adapter`** — bridges the hourly scheduler to the
  process kernels and applies the hourly-specific policy surfaces
  (transport-capacity enforcement on top of shared physics).
- **`watbal_closure_guard`** — emits the runtime conservation
  residual and trips fast (`ERROR STOP 205`) when either the kernel
  or interchange residual exceeds the 1.0 mm material non-closure
  threshold; also hosts the Phase 3 structural-pattern fail-fast
  (`ERROR STOP 206`).
- **`watbal_process_types` / `watbal_route_types`** — shared derived
  types (`wb_water_inputs`, `wb_flux_state`, `wb_closure_state`,
  `wb_process_status`, `wb_route_kernel_status`, etc.) that carry
  named state across kernel calls.
- **`hillslope_binary_pass_reader` / `hillslope_binary_pass_writer`
  / `hillslope_binary_pass_legacy_adapter`** — the HBP family
  serialization layer (see **Output schema and downstream
  compatibility** below).
- **`f90_modernization_env`** — environment-variable handling for
  observability and surveillance gates.
- **`cleanroom_impoundment_routines`** — impoundment routines
  rewritten under the clean-room modernization discipline.

## Defect repairs

For the full stakeholder narrative of each repair, see
[`docs/20260504-stakeholder-watbalance.md`](../docs/20260504-stakeholder-watbalance.md).
For per-package evidence, see the cited work packages and ablation
packages.

### 1. Transport-capacity bypass on multi-OFE hillslopes (WB-05A)

- **Discovery context:** caught on production hillslope `H2637 OFE 19`
  during the WB-05 hourly adapter implementation; closure spike of
  approximately 180 mm on a single OFE on a single day.
- **Mechanism:** the hourly transport-capacity ("q-cap") gate was
  enforced only when an OFE's effective flow length exceeded its
  physical slope length — a condition rarely true at the bottom OFE
  of long hillslopes. The gate was effectively bypassed at the
  bottom OFE where the largest cumulative runoff arrived.
- **Repair:** the gate now enforces the hard cap in every condition
  where it is supposed to apply. The soft-limiter behavior is
  reserved for the geometric-span case it was designed for. See
  [`docs/work-packages/20260503-wb05a-h2637-ofe19-hourly-qcap-resolution/`](../docs/work-packages/20260503-wb05a-h2637-ofe19-hourly-qcap-resolution/package.md).
- **Closure evidence:** positive q-cap margins on `H2637 OFE 19`
  reduced from hundreds of millimeters per hour to zero at the
  0.1 mm tolerance; daily-path behavior on the same hillslope
  unchanged.
- **Impact:** hourly-path runs that include long multi-OFE hillslopes
  now respect transport capacity at every OFE. Hillslopes that never
  violated the cap are unchanged.

### 2. Snowmelt double-count in the closure basis (WB-05E)

- **Discovery context:** universal failure pattern across all 1,166
  audited hillslopes on the first closure sweep.
- **Mechanism:** the legacy audit convention used `RM` (rainfall plus
  snowmelt) as the external input and tracked snowpack water as
  storage, double-counting snowmelt on every melt day.
- **Repair:** the audit basis is now `P + Irr` external input with
  `Snow-Water` in the storage delta; the kernel emits the same
  basis. See [`docs/work-packages/20260503-wb05e-goblin-mode-global-closure-repair/`](../docs/work-packages/20260503-wb05e-goblin-mode-global-closure-repair/package.md).
- **Closure evidence:** closure residuals on snowmelt days collapse
  from hundreds of millimeters to numerical noise. Production
  `H.wat` / `H.pass` outputs unchanged.
- **Impact:** downstream consumers computing water-balance residuals
  using `RM` must adopt `P + Irr` with `Snow-Water` in the storage
  delta.

### 3. Missing interception-storage export (WB-05E, OR-H0066 incident)

- **Discovery context:** last remaining seed (1.13 mm residual on a
  single hillslope) after the snowmelt double-count repair.
- **Mechanism:** live plant canopy (`pintlv`) and surface residue
  (`resint`) interception storage are real model states but were not
  exported in `H.wat`; the audit reading the file saw that water
  vanish.
- **Repair:** new optional trailing column `InterceptionStorage` in
  `H.wat`, populated as `pintlv + resint` per OFE/day. Contract
  change-control: `WB02-CC-20260504-02`.
- **Closure evidence:** OR-H0066 residual collapses from 1.131 mm to
  0.001 mm; all 1,166 hillslopes close within the 1.0 mm threshold.
- **Impact:** `H.wat` gains one optional column; parsers keyed on
  column header are unaffected; parsers keyed on positional column
  count should declare expectations.

### 4. Process-kernel storage and runoff reconciliation (WB-05F)

- **Discovery context:** first scoreboard run with the runtime
  process guard active — hillslope `H0001` from `cochlear-beriberi`
  tripped with both kernel and interchange residuals reading
  −15.8066 mm.
- **Mechanism:** in the new code, the adapter was emitting non-zero
  output fluxes on zero-input days without a compensating storage
  change, and the per-OFE runoff mapping was reconciling against a
  watershed-summed `q` rather than the OFE-local `qofe`.
- **Repair:** kernel-flow storage update now operates against the
  same closure basis the audit uses; runoff reconciles to OFE-local
  `q`/`qofe`. See [`docs/work-packages/20260504-wb05f-process-guard-replay-closure-repair/`](../docs/work-packages/20260504-wb05f-process-guard-replay-closure-repair/package.md).
- **Closure evidence:** post-repair WB-05B scoreboard envelope:
  `max_abs_daily = 0.92 mm`, `max_abs_target_ofe = 0.02 mm`,
  `max_abs_any_ofe = 0.51 mm`. All 1,166 rows pass the 1.0 mm
  threshold under the runtime process guard.
- **Impact:** the first defect surfaced inside the new kernels; it
  was caught at the gate before any operational run was issued
  against the new accounting.

### 5. Rain-routing conflation in legacy winter aggregator (Candidate 1, `insensible-aliquot/p26` incident)

- **Discovery context:** runtime conservation guard tripped on
  operational replay of `insensible-aliquot/p26` against `wepp_260513_hill`
  on 2026-05-14, year 1 day 84, OFE 1, residual −3.95 mm.
- **Mechanism:** the legacy daily winter routine was adding rain water
  that fell during snow-on-ground hours into a daily snowmelt
  accumulator, broadcasting at end-of-day through the snowmelt
  channel. A correlated suppression site zeroed the rain channel on
  the same days, so the rain water re-emerged as melt. On days when
  the rainfall exhausted the snowpack mid-day, the broadcast value
  hit the snowpack-availability cap with zero snowpack available, the
  cap clamped the input to zero, and output water left the system
  with no input source.
- **Repair:** rain water always enters the kernel through the rain
  channel regardless of snowpack state; the snowmelt channel carries
  only energy-balance snowmelt produced by the snowpack itself.
  Rain-on-snow energy interactions are modeled within the snowpack's
  energy-balance update, not by aliasing rain mass into the melt
  channel. See [`docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/`](../docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/package.md).
- **Closure evidence:** post-repair residuals on the four
  originally-failing tuples sit at approximately ±5 × 10⁻¹⁵ mm; the
  50-year `p26` replay completes cleanly under the runtime guard.
- **Impact:** rain-on-snow days that exhaust the snowpack mid-day no
  longer trip the guard. Per-channel attribution on those specific
  days differs from prior releases — rain water now appears in the
  rain channel where it physically belongs — but the total liquid
  input to the soil profile on each day is unchanged.

### 6. Baseflow-preservation interaction (Shape A, WB-30 D06-preserve scaling)

- **Discovery context:** after Candidate 1 closed `p26`, the broader
  477-run test cohort on the same project still showed 47 hillslopes
  failing with the same exit code on different dates.
- **Mechanism:** the WB-18 snowmelt cap (which limits melt input by
  available snowpack mass) and the WB-30 baseflow preservation (which
  holds baseflow output at full value when other outputs are scaled
  in a shortfall correction) were not specified for the case when
  both fired in the same step. Combined, they produced un-reconciled
  mass with no compensating storage change.
- **Repair:** under normal operation, baseflow stays preserved (the
  WB-30 partition is correct). When the snowmelt cap fires, the
  shortfall correction scales baseflow along with the other outputs,
  restoring mass closure. This is the program's first concrete
  enforcement of the [clamp-plus-preserve mass-closure invariant](../docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md).
- **Closure evidence:** full 477-run cohort closes at zero failures.
  Phase 1 surveillance counter on representative subset: zero events
  across all magnitude buckets including `ge_0p1_mm`. Bisection
  confirmed WB-30 (`163d4914`) as first-bad commit; WB-18 (`dcadfbe1`)
  as enabling co-factor.
- **Impact:** the 47-hillslope regression cohort closes cleanly.
  Per-channel attribution on late-winter / early-spring melt-with-rain
  days where the snowmelt cap fires now reflects the reduced-input
  balance; total water input and output across the simulation
  unchanged in aggregate.

## Validation

### Unit tests

Approximately 10,000 lines of test code accompany the new kernel
implementations. Each kernel has at least one test file asserting
that its conservation residual is zero within 64-bit numerical noise
on a battery of canonical input vectors, that documented edge cases
(zero precipitation, zero canopy, fully frozen layer, zero field
capacity) produce documented behavior rather than NaN, and that any
test vector added during a repair is checked in with the repair
commit.

Executed unit-test runs against `64b86eaf`:
- `tests/test_phase3_clamp_preserve_failfast.py` — 3 passed
- `tests/test_wb31_clamp_preserve_counter_contracts.py` — 4 passed
- `tests/test_rain_routing_kernel_probe_contracts.py` — 4 passed
- `tests/test_rainmelt_conflation_trace_contracts.py` — 4 passed
- `tests/test_wmelt_producer_trace_contracts.py` — 3 passed
- `tests/test_wb15_process_probe_call_contract.py` — 8 passed
- `tests/test_wb_routing_vector_contracts.py` — 35 passed
- `tests/test_release_sidecar_contract.py` — 2 passed

For the full per-kernel unit-test matrix and the architecture-frozen
test specification, see [`docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/`](../docs/work-packages/20260503-wb03-waterbalance-process-architecture-unit-tests/package.md).

### Integration / closure

- **WB-05B forest closure sweep (1,166 hillslopes across four forest
  projects).** Executed on `64b86eaf` for this release: 1166 ok /
  0 failed / 0 ERROR STOP 205 / 0 ERROR STOP 206 / 0 Phase 3 firings.
  Per-project counts: `cochlear-beriberi` 520, `moth-eaten-blackhead`
  209, `ordained-incentive` 333, `uninsured-deformation` 104. See
  `docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/artifacts/T1J_broader_sweep_results.csv`
  and `T1J_broader_sweep.md`.
- **insensible-aliquot test cohort (477 hillslopes).** Executed on
  `64b86eaf`: 477 ok / 0 failed. Surveillance counter on
  representative subset: zero events across all magnitude buckets.
- **Closure residual envelope under the runtime process guard:**
  `max_abs_daily = 0.92 mm`, `max_abs_target_ofe = 0.02 mm`,
  `max_abs_any_ofe = 0.51 mm` — comfortably under the 1.0 mm
  material non-closure threshold and well under the WB-02 frozen
  40 mm single-OFE acceptance band.

### Watchlist / regression cohort

- `python tools/run_hillslope_watchlist.py --binary src/wepp_hill`
  executed at `64b86eaf`: 14/14 passed.

### End-to-end manual replay

- **Hillslope replay (`insensible-aliquot/p26`):** executed against
  `src/wepp_hill` at `64b86eaf`, exit 0, residuals on the originally
  failing tuples at floating-point noise (±5 × 10⁻¹⁵ mm).
- **Watershed replay (reconciled-condenser):** executed against
  `src/wepp` at `64b86eaf`, exit 0, completion line
  `WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY` observed.

### Binary provenance checks

- `readelf` interpreter check: both `src/wepp` and `src/wepp_hill`
  and both `release/wepp_260514` and `release/wepp_260514_hill` show
  `/lib64/ld-linux-x86-64.so.2`. No Homebrew interpreter contamination.
- Sidecar JSON contract field verification: passed for both binaries.
- `tools/smoke_wepp_binary_host.sh`: passed for both `src/wepp` and
  `src/wepp_hill`.

### Code review

This release passed the program's standard review gates:

- **Linter pass (`fortitude check`):** executed clean on every touched
  `.f90` file, per the WB-program lint discipline.
- **Kernel unit test pass:** every WB kernel asserts its conservation
  invariant within `real64` numerical noise on canonical input
  vectors; the WB-04, WB-05, WB-05A, WB-05E, and WB-05F suites pass
  cleanly.
- **Closure audit pass:** runtime conservation guard active across
  the full 1,166-hillslope WB-05B cohort and the 477-run
  insensible-aliquot cohort with zero failures and zero firings.
- **Contract change-control:** the optional `InterceptionStorage`
  column in `H.wat` is the one schema change in this release; it
  carries change-control entry `WB02-CC-20260504-02` on file.
- **Operator review:** the release was reviewed by the program's
  responsible operator (Roger Lew) before vendoring; the WB-08A
  release packet (`wepp_260504`) and the subsequent `wepp_260514`
  release packet both followed the standard release-packet
  acceptance flow.

The dual-basis closure architecture (kernel residual + interchange
residual) is itself the most load-bearing review gate: a repair that
closes one residual but not the other is rejected by the gate.
Both residuals close to floating-point noise on the
originally-failing tuples for every repair in this release.

Static unrelated check: `tools/check_ablation_artifact_policy.py`
still reports pre-existing violations on the unrelated
`20260513_route06_publish_balance_nonclosure_ablation` package
(missing matrix/scope metadata). This predates the current release
and is out of scope.

## Output schema and downstream compatibility

### `H.wat` columns

The only output-schema change to `H.wat` between `wepp_260430` and
`wepp_260514` is the optional `InterceptionStorage` column added under
contract change-control entry `WB02-CC-20260504-02` (from the WB-05E
work). Parsers that key on column header are unaffected. Parsers
that key on positional column count should declare whether they
expect the new column. The WB-06 downstream contract integration
package ([`docs/work-packages/20260504-wb06-waterbalance-downstream-contract-integration/`](../docs/work-packages/20260504-wb06-waterbalance-downstream-contract-integration/package.md))
verified that WEPPpy-facing consumers (`H.wat` parsers, `chnwb`
reports, `totalwatsed3` aggregations, audit tooling) handle the new
column correctly.

### HBP hillslope pass family

This release ships the binary hillslope pass format (HBP) as the
authoritative hillslope pass family. The family signature in the
sidecar metadata is `H*.hbp`; the schema version emitted by the
binaries is `hbp_schema_major=1, hbp_schema_minor=0` (the schema
version is independent of the iteration of the spec document under
which the format was implemented; the current spec implementation
incorporates the v2 spec revisions). The HBP serialization layer
lives in three modules:

- `hillslope_binary_pass_writer` — writes `H*.hbp` from hillslope
  kernel state.
- `hillslope_binary_pass_reader` — reads `H*.hbp` directly into
  the watershed binary's pass-consumer surface; the sidecar
  metadata field `mode2_direct_hbp_reader=true` indicates the
  watershed binary in this release can consume HBP without an
  intermediate text-format translation.
- `hillslope_binary_pass_legacy_adapter` — bridges between the
  HBP format and the legacy ASCII pass family
  (`legacy_ascii_pass_family=H*.pass.dat` in the sidecar metadata)
  for downstream consumers that have not migrated to the binary
  format.

The HBP format and its readers are governed by the contracts at
[`docs/contracts/hillslope-binary-pass-format.md`](../docs/contracts/hillslope-binary-pass-format.md)
and [`docs/contracts/watershed-hillslope-pass-reader-contract.md`](../docs/contracts/watershed-hillslope-pass-reader-contract.md);
serialization discipline is documented at
[`docs/contracts/pass-binary-serialization-guidance.md`](../docs/contracts/pass-binary-serialization-guidance.md).

### Watershed pass file `pw0` no longer required in process mode

In the previous release posture, watershed simulations consumed a
master watershed pass file (`pw0`) constructed from the hillslope
pass family before the watershed routing kernels could run. In
`wepp_260514`, with the process-kernel architecture as authoritative,
the watershed binary in process mode reads hillslope state directly
from the HBP family and emits routed output without requiring the
`pw0` intermediate. The sidecar metadata records this as
`process_mode_pass_pw0_required=false` and
`mode2_master_pass_prompt_required=false`. The previous prompt-based
master-pass workflow is therefore retired in process mode.

The legacy ASCII pass family (`H*.pass.dat`) and the corresponding
legacy watershed-pass workflow remain available for consumers that
have not yet migrated to the HBP family; the legacy adapter is
preserved alongside the new reader/writer.

### Boundary-condition shift inventory

Production `H.wat` / `H.pass` column values are otherwise unchanged
in shape. Where values shift, the shift concentrates on the boundary
days for the defect classes repaired above; well-conditioned runs
without those boundary conditions agree with `wepp_260430` to
numerical precision. See [`docs/20260504-stakeholder-watbalance.md`](../docs/20260504-stakeholder-watbalance.md)
"Why you may see slightly different numbers" for the per-class
shift inventory.

## Legacy parity and rollback

- **Last deployment-class release:** `wepp_260430` (gfortran SIGFPE
  fixes). See [`docs/20260414-stakeholder-brief-compiler-fragility.md`](../docs/20260414-stakeholder-brief-compiler-fragility.md)
  for the SIGFPE fix program that produced that release.
- **Rollback target:** `wepp_260430` for the deployment-class binary.
  The intermediate test-vendored builds (`wepp_260319` through
  `wepp_260513`) are preserved for reproducibility but are not
  recommended rollback targets — each shipped with at least one of
  the closure defects this release repairs.
- **Functional-state tag:** `wb-p26-shapeA-functional` at commit
  `64b86eaf`. This tag is the rollback anchor for any subsequent
  work that depends on the current functional state.
- **Legacy bit-for-bit parity:** the legacy `wepp_dcc52a6` binary
  remains available for workflows that need to reproduce historical
  forest-watershed outputs exactly. That binary still carries the
  four legacy defects described above; bit-for-bit parity means
  bit-for-bit parity, including the historical defects.
- **Per-defect behavioral diff:** documented per repair in the
  **Defect repairs** section above. The pattern is consistent:
  boundary days where the legacy code was producing physically
  impossible numbers will read differently in `wepp_260514` (they
  will read correctly); well-conditioned days agree to numerical
  precision.

## Known limitations and follow-up work

- **Watchlist verification of Candidate 1's full behavioral surface
  area on rain-on-snow days** is deferred to the follow-on package
  [`docs/ablation/20260515_winter_producer_overcomputation/`](../docs/ablation/20260515_winter_producer_overcomputation/package.md).
  The Candidate 1 fix is closure-validated on the originally-failing
  tuples at floating-point noise, but exhaustive cohort-wide
  verification across all rain-on-snow patterns is incomplete.
- **Gate 0 (producer correctness) remains open.** The Shape A fix
  satisfies Gate 2 (preserve-path conservation under input suppression)
  at production scale and drives the Phase 1 surveillance counter to
  zero on the WB-05B cohort. The underlying producer-correctness
  concern — the legacy energy-balance melt routines can compute
  `wmelt > snowpack` on edge cases — is a quality issue rather than a
  closure-correctness issue post-Shape-A, but the follow-on package
  remains scope-refined for that investigation when Phase 3 firings
  on production data give it a starting cohort.
- **Phase 3 firings on non-WB-05B cohorts.** The 1,166-hillslope
  WB-05B sweep produced zero Phase 3 firings. Production data sets
  outside that cohort may surface firings; they are the expected
  Gate 0 discovery output and should be reported, not suppressed.
  Per the architecture-note prohibition, the 0.1 mm floor must not
  be tuned upward to hide firings.
- **Unrelated open ablation packages** are preserved in
  `docs/ablation/` for their respective work streams (route06
  publish-balance nonclosure, others) and are out of scope for this
  release.

## Operational guidance

### Deployment notes

- The release ships under the standard `wepp_<tag>` and
  `wepp_<tag>_hill` naming convention. The WB-09 package owns
  operator-controlled vendoring and promotion to production runners;
  this notes file does not authorize promotion. WB-09 readiness is
  marked from WB-08A; the operator decides when to promote.
- Pinned `/usr/bin/gfortran` is the build toolchain; the
  release-checklist's interpreter check (`readelf` showing
  `/lib64/ld-linux-x86-64.so.2`) is the gate against Homebrew
  contamination.
- No environment changes are required for the new binaries
  themselves. The optional `InterceptionStorage` column in `H.wat`
  may require declaration in downstream parser configurations.

### Recommended evaluation before adoption

- Run the WB-05B closure sweep against any downstream pipeline that
  consumes `H.wat` or `H.pass` to confirm the optional column is
  handled correctly.
- Re-run any production replay that depends on rain-on-snow forest
  hillslopes and confirm the per-channel attribution change is
  understood; aggregate water-balance totals are unchanged but
  per-channel routing on affected boundary days differs.
- Re-run any calibration tied to a historical forest-watershed
  aggregate; in most cases nothing will need to change, but
  recalibrating against the closure-correct output is more defensible
  than calibrating against numbers that depended on a known
  accounting defect.

### Monitoring after deployment

- **Phase 3 firings (`ERROR STOP 206`)**: any firing names the failing
  tuple in a structured one-line message prefixed by
  `WBK08_PHASE3_FAILFAST`. Firings are the gate's surveillance signal
  for Gate 0 producer-correctness concerns; report and investigate
  rather than suppress.
- **Closure-residual trips (`ERROR STOP 205`)**: any trip is an
  unhandled defect class. Open an ablation package under
  `docs/ablation/` following the standard closure-audit discipline.
- **Surveillance counter (env-gated)**: the Phase 1 clamp-plus-preserve
  surveillance counter remains in place as an opt-in observational
  channel. Operators investigating boundary behavior can enable it
  via `process_accounting_wbk08_clamp_preserve_counter=1` and capture
  bucketed event counts per run.

### Rollback procedure

1. Revert the operational binary vendoring step in the wepppy
   release lane back to `wepp_260430` and `wepp_260430_hill`.
2. Confirm downstream parsers tolerate the absence of the
   `InterceptionStorage` column (parsers keyed on column header
   handle this implicitly; parsers keyed on positional column count
   may need an explicit declaration).
3. Open an incident package under `docs/ablation/` documenting the
   trigger for the rollback and the residual evidence.
4. Per the WB-09 release contract, rollback to legacy parity is
   served by the `wepp_dcc52a6` binary if `wepp_260430` is also
   unsuitable.

## Provenance and references

- **Stakeholder brief:** [`docs/20260504-stakeholder-watbalance.md`](../docs/20260504-stakeholder-watbalance.md)
  (six-defect narrative for non-developer audience).
- **Compiler-fragility brief (prior release context):**
  [`docs/20260414-stakeholder-brief-compiler-fragility.md`](../docs/20260414-stakeholder-brief-compiler-fragility.md).
- **Architectural invariant (Shape A / Phase 3):**
  [`docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md`](../docs/contracts/wbk08-clamp-preserve-mass-closure-invariant.md).
- **Trajectory ownership contract (WB-08A):**
  [`docs/contracts/trajectory-ownership-contract.md`](../docs/contracts/trajectory-ownership-contract.md).
- **F90 modernization strategy:**
  [`docs/contracts/f90-modernization-strategy.md`](../docs/contracts/f90-modernization-strategy.md).
- **WB program work packages (chronological):** see
  [`docs/work-packages/`](../docs/work-packages/) — WB-00 through WB-08A.
- **`p26` incident package:**
  [`docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/`](../docs/ablation/20260514_insensible-aliquot_p26_hillslope_watbal-process-closure-205-ablation/package.md).
- **Follow-on Gate 0 package:**
  [`docs/ablation/20260515_winter_producer_overcomputation/`](../docs/ablation/20260515_winter_producer_overcomputation/package.md).
- **Release-checklist convention:** [`docs/release-checklist.md`](../docs/release-checklist.md).
- **Prior release notes:** none; `wepp_260514_release_notes.md` is
  the first sidecar authored under the new release-notes convention
  introduced by `release/_release_notes_template.md`.

## Anchors

- **Tag:** `wb-p26-shapeA-functional` → `64b86eaf9040510173b90c2bf3ad62b899849970`
- **Commit:** `64b86eaf` on `master` in `wepp-in-the-woods/wepp-forest`
- **Prior deployment-class release:** `wepp_260430`
- **Rollback target:** `wepp_260430`; legacy bit-for-bit parity served
  by `wepp_dcc52a6`.
