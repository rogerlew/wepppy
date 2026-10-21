# Investigate watershed channel routing closure without changing simulation

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md` in
WEPPpy. Maintain Progress, Surprises & Discoveries, Decision Log, Outcomes &
Retrospective, and the package tracker at each handoff.

## Purpose / Big Picture

Give Roger and Ayush reproducible evidence explaining whether unequal-area OFE
water reaches watershed channels and the outlet with correct volume accounting.
An OFE is one modeled section of a hillslope. Closure means that inputs minus
outputs minus storage increase equal zero within justified numerical uncertainty.
The outcome is an auditable diagnosis, including unresolved terms when necessary.

This is an investigation, not modernization or a simulation fix. The user asked
to scaffold it and allows observability instrumentation during later execution.
Execution explicitly authorized by Roger on 2026-10-21.

## Progress

- [x] (2026-10-21 16:42 UTC) Scaffold investigation and operator scope boundary.
- [x] (2026-10-21) M1: Retained provenance, source map, workbook audit,
  control-volume definitions, generated input decks and supported project forks.
- [x] (2026-10-21) M2: Added gated native probes; baseline/off/on runs complete.
  Five controlled cases, daily path, unequal tributaries, cascade and one real
  project completed full periods. Exact scientific parity passes in all nine successful cases.
- [x] (2026-10-21) M3: Final readback, 160,345 channel-day ledger records,
  diagnostic controls and malformed-record rejection complete.
- [x] (2026-10-21) M4: Correctness review and source QA pass; findings
  published and investigation closed with the model defect explicitly open.

## Surprises & Discoveries

Terminal lateral area conversion matches observations in the tested constant-width
cases. The schema-2 writer emits 366 slots every year; the reader consumes one
slot per actual routing day without matching dates. Controlled cases first diverge
on 1982-01-01. This is the first demonstrated failing boundary, independent of
OFE splitting. Channel publication residuals are partly balance identities and
cannot prove physical-domain conservation.

The workbook's original decks were not supplied by Ayush (operator confirmation).
The first real project rejects zero HMAX; the second completes after isolated
run-card migration to the canonical HBP prompt contract. The impoundment case
reports failure despite process return code zero. Full observation traces on NFS
were slow, so complete observation runs use local storage; overhead measurements
are not a controlled filesystem benchmark.

## Decision Log

2026-10-21 — Close as a successful observation-only investigation with a confirmed
calendar-selection defect, not a corrected model. Real-project full-period parity
and independent final review pass. Stop at the first reproduced failing boundary;
full soil/GW/domain ledgers and unsupported/failed cases remain unresolved rather
than expanding into simulation repair. Original decks were not supplied by Ayush.

2026-10-21 — Execute observation-only scope on explicit operator request. Retain
failed default-link build; supply existing zlib explicitly with `-lz`. Use existing
channel diagnostics before adding probes. Original workbook decks were not supplied; historical binary identity is unknown.

2026-10-21 16:42 UTC — Operator Roger permits observation but prohibits changes
to simulation code behavior. Add probes only; preserve equations, precision,
evaluation order, branch conditions, thresholds, state updates, defaults, and
existing scientific output formats. No numerical guards or closure corrections.
Any remedy needs a separate proposal and authorization. Native ablation policy
does not override this narrower scope.

## Outcomes & Retrospective

A reproducible PASS calendar-selection defect is identified without changing
simulation behavior. Original workbook attribution, physical-domain closure and
failed-case balances remain unresolved. All nine successful cases pass
exact baseline/off/on file parity and reviewed readback, including 28 hillslopes
over 43 years in a real project. The 160,345-record ledger supports publication
arithmetic only; no physical-domain closure is inferred. Detailed evidence is in
`artifacts/findings.md`; commands, failed attempts and external trace paths are
retained. No simulation correction, release, vendoring or deployment occurred.

## Context and Orientation

The coordination repository is `/workdir/wepppy`; native sources are in
`/workdir/wepp-forest`. Read each repository's nearest AGENTS before work.
Package artifacts belong under
`docs/work-packages/20261021_watershed_channel_routing_closure/artifacts/` in
WEPPpy. Preserve unrelated changes and do not switch branches.

In the native repository, start with `src/watbal.for` and
`src/watbal_hourly.for` for local water balances and receiving OFE area ratios;
`src/contin.for` for deep-percolation/groundwater volume accumulation;
`src/wshpas.f90` for terminal PASS quantities and event selection;
`fpm-src/hillslope_binary_pass_legacy_adapter.f90` and
`fpm-src/hillslope_binary_pass_reader.f90` for serialization and loaded values;
`src/wshdrv.f90` for routing orchestration; `src/wshcqi.f90`,
`src/wshchr.f90`, `src/wshiqi.f90`, and `src/wshimp.for` for channel and
impoundment transfers. Follow active calls into `fpm-src/watbal_route_kernels.f90`
and the associated types rather than assuming legacy expressions own writeback.
Locate actual output writers, groundwater routines, and geometry definitions in M1.

Physical terminal WAT runoff, threshold-filtered PASS delivery, and routed outlet
discharge are different boundaries. Local ET is Ep + Es + Er. Area-weight local
ET and deep percolation (Dp); do not average outlet volumes. Lateral depth at the
terminal OFE becomes volume using that OFE's area. Existing supported terminal
WAT Q has whole-hillslope normalization; do not apply the terminal area fraction
again. Validate these assumptions against the exact producer and geometry.

## Plan of Work

### M1 — Freeze baseline and define accounting

Capture source commits and dirty diffs in both repositories, executable hashes,
compiler and flags, runtime configuration, complete input decks and shared files,
OFE dimensions, connectivity, calendars, routing modes, and observation settings.
Read native `docs/ablation/protocol.md`, especially science-investigation lane
discipline. Use its baseline, hypothesis, parity, and symmetric-residual practices;
exclude behavioral mutation and promotion lanes. Locate the workbook and original
inputs if available. Record missing historical lineage rather than inventing it.

Create `artifacts/source_map.md`, `case_matrix.csv`, and `provenance.json`.
For every transfer identify the writer, reader, units, area basis, timestep,
owning state, and whether it crosses the selected physical boundary. Establish
separate soil-profile, groundwater, channel/impoundment, and combined-domain
balances. Dp may be a soil export but an internal groundwater recharge transfer;
do not also count it as external loss when counting later baseflow.

Select an isolated one-hillslope/one-channel case, then unequal tributaries and
a channel cascade. Compare single OFE, 50/50, 60/40, 40/60, and three unequal
OFEs with otherwise matched physical inputs. Include daily/hourly water balance,
dry and wet days, runoff near event thresholds, lateral-only delivery, tile and
groundwater contributions, and an impoundment where supported. Explicitly mark
unsupported combinations; a full Cartesian matrix is unnecessary. Include a
contour/variable-width case if runnable and never extrapolate constant-width proof.
Select one real project through the supported clone/archive workflow, retaining
all shared runtime context. Full configured-period completion is required for
decisive case conclusions; shorter windows support only exploratory localization.

M1 acceptance is a source-backed map, runnable case commands, and a declared
ledger/tolerance design. No assertion that splitting must yield identical runoff
is permitted: discretization can change behavior while each case still conserves.

### M2 — Observe without perturbing simulation

First use existing diagnostics. Where a necessary term is missing, add narrowly
gated observations through the existing `wepp_observe.on` mechanism. Record raw
values at existing assignment/call boundaries without reevaluating stateful
functions, changing numerical expressions, or writing to simulation arrays or
COMMON state. Diagnostic formatting can expose stored precision but cannot change
simulation precision. Reuse existing I/O conventions; do not alter PASS/WAT schemas.

Measure terminal hillslope quantities before filtering, selected event and omitted
volume, serialized and readback volumes, routing input volumes, local channel
inputs/losses, groundwater/tile exchanges, start/end storage, and downstream export.
Capture time interval, year/day, element/upstream IDs, units, area, and phase so
each transfer is counted exactly once. Identify whether each reported quantity is
an instantaneous rate, integrated volume, cumulative counter, or snapshot.

Create `instrumentation_design.md` and `parity.json`. Compare the unmodified
baseline with the instrumented build with observations off and on, using identical
inputs/compiler/flags. Require exact scientific payload parity for deterministic
same-build cases; enumerate only nonscientific metadata differences. Investigate
any scientific difference before interpreting diagnostics; do not relax parity
to accommodate an intrusive probe. Retain runtimes and log sizes as overhead evidence.
Apply native `.f90` review gates when relevant. M2 ends only when observations
are wired into actual replay execution and demonstrate noninterference.

### M3 — Build volume ledgers and test the diagnostic

Create an offline ledger from observed boundary values and independent raw-output
readback. Convert depth to volume exactly once: m times m2, or mm times m2 / 1000.
Integrate discharge using the actual time intervals, not an assumed daily or hourly
duration. Match internal outgoing and incoming volumes by connectivity and time.
Validate PASS values at the actual file opened by the reader, including event
omissions and numerical serialization precision. Compare loaded arrays and routed
transfers without reconstructing quantities from rounded text when native values
are available.

For each control volume compute residual = external inputs - external outputs -
(ending storage - starting storage). Include precipitation on the relevant area,
ET, infiltration/transmission losses, groundwater, tile drains, impoundments, and
other actual source/sink terms; label unavailable terms unknown, never zero.
Exclude internal transfers in the combined-domain balance. Keep physical export
and PASS-filtered export separate and report the gap explicitly. Do not treat a
large unexplained residual as a threshold omission without measured evidence.

Before grading cases, document absolute-volume and relative tolerances derived
from stored precision, serialization quantization, accumulation length, and any
rate-integration error. Report signed, absolute, normalized, and cumulative
residuals with explicit near-zero handling. Assess worst day/element and total
absolute error so positive and negative errors cannot cancel into an apparent pass.
Missing days, duplicate transfers, nonfinite values, incomplete runs, and missing
storage invalidate closure claims rather than silently passing.

Add offline positive controls: duplicate one inflow, drop one outflow, apply a
wrong area factor, and reverse one storage-change sign in copied ledger data.
The audit must detect each known error and its expected sign/magnitude. Include
a hand-computable zero-residual control. Never inject these changes into simulation
code. Keep a hypothesis/progress ledger and change one input factor at a time for
attribution. No requirement to explore unauthorized simulation mutation factors.

M3 delivers `volume_ledger.csv`, `residual_summary.csv`, `diagnostic_controls.json`,
`progress_ledger.csv`, and manifests pointing to retained replay artifacts.
Each conclusion is tied to exact cases and executable identities.

### M4 — Review and communicate findings

Publish `findings.md` with confirmed behavior, defects, invalid diagnostics,
unresolved evidence, and coverage limitations kept distinct. For each finding
name the first divergent boundary, expected and observed volumes, source path,
reproduction command, impact, and smallest proposed follow-up investigation or fix.
Review diagnostic correctness and parity using the repository correctness-review
template; close review findings about this investigation's validity. Model defects
remain explicitly open as separately authorized work, not silently corrected.

Update user/developer documentation only if evidence establishes a durable
interpretation clarification; do not generalize beyond tested paths. Close this
package as an investigation, move the completed plan, update the tracker and root
discovery links, and state that no simulation correction or deployment occurred.

## Concrete Steps

At execution start, from each repository record `git status --short` and
`git rev-parse HEAD`. From `/workdir/wepp-forest`, inspect tools before using them:

    python tools/inspect_hillslope_binary_pass.py --help
    python tools/compare_wepp_outputs.py --help
    python tools/compare_wepp_raw_outputs.py --help

Record exact replay working directories, stdin run cards, commands, and environment
in `artifacts/commands.md` after M1 selects cases. Build baseline and instrumented
versions in isolated source/build copies preserving tracked and relevant untracked
inputs; do not clean the shared checkout or overwrite a vendored binary. Follow
the native makefile build procedure (`make wepp` and `make wepp_hill` in each
isolated `src/`) with identical recorded compiler flags. Run each copied case with
its matching hillslope/PASS/watershed build; never mix release families.

Use native `pytest` and `fpm test` as applicable to the changed observations and
helpers, plus real replay comparisons. Record exact commands and results; unit
tests do not replace closure or parity evidence. WEPPpy production code is outside
scope, so no frontend or broad Python suite is required for this scaffold. If
execution proposes WEPPpy code changes, re-scope before editing.

From `/workdir/wepppy`, validate documentation with:

    wctl doc-lint --path docs/work-packages/20261021_watershed_channel_routing_closure
    tools/check_agents_size.sh AGENTS.md

## Validation and Acceptance

Accept the investigation when all executed decisive cases have full-period
provenance, unmocked writer/reader/routing evidence, validated diagnostics,
three-way scientific parity, explicit tolerance rationale, and reviewed outcomes.
Do not require all model cases to close: a reproducible defect is a valid research
result. Missing terms or incomplete runs require an unresolved disposition.
Never claim watershed-wide validity from a single case or a green test suite.

## Idempotence and Recovery

Use distinct visible attempt directories and manifests. Preserve failed attempts,
baseline files, and shared project context; do not overwrite live runs or historical
outputs. Turning observations off must restore ordinary output behavior. Keep
large traces outside git with retained paths/hashes; do not publish private project
payloads. If parity fails, isolate or remove only this package's probes and rerun
before interpreting the ledger. Preserve all unrelated repository changes.

## Interfaces and Dependencies

Reuse native observation helpers, PASS readers/inspectors, existing Python data
tools, and output comparators. No new runtime dependency or API is authorized.
Document ledger columns and units in `artifacts/ledger_schema.md` before writing
the parser, including provenance keys, storage interval, filtering disposition,
and unknown-value representation. Offline analysis never writes model inputs back.

## Revision Notes

2026-10-21 16:42 UTC — Initial scaffold records the operator's observability-only
scope and prevents investigation from turning into an implicit simulation fix.

2026-10-21 — Execution started; retained provenance and declared ledger design.

2026-10-21 — Completed M1–M4; final independent gate passed. Retained successful
and failed artifacts, explicit limitations, and separate remediation proposal.
