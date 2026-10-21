# Repair physical water allocation and watershed routing

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes &
Retrospective, plus this package’s tracker, at every handoff.

## Purpose / Big Picture


Make the current model account for water consistently from each hillslope OFE
(a modeled soil/slope segment), through PASS transfer files, into channel rate
routing and final watershed output. Address Ayush’s Dp (deep percolation), ET
(evapotranspiration), lateral flow and Q/QOFE concerns without counting internal
transfers twice. The four demonstrated defects are missing channel-local rate
contributions, under-delivery by flat source hydrographs, discarded hourly
infiltration remainders and initial groundwater scaled by terminal OFE area.

The operator requested committing the audit and scaffolding this package on
2026-10-21. This turn creates the plan only. Execution remains pending. Once
execution is requested, proceed through the milestones without routine additional
confirmation, within the defined source-repair scope. Ash, dated release
publication, production deployment and original-project repair are excluded.

## Progress


- [x] (2026-10-21 21:53 UTC) Commit predecessor audit at `e85d582ed`.
- [x] (2026-10-21) Scaffold scope, acceptance matrix and execution milestones.
- [ ] M1: freeze baseline; portable failing tests; proposed contracts/ADR and scientific review.
- [ ] M2a: repair WPA-04 groundwater initialization in an isolated lane.
- [ ] M2b: repair WPA-03 hourly infiltration allocation in an isolated lane.
- [ ] M2c: repair WPA-02 flat source reconstruction in an isolated lane.
- [ ] M2d: repair WPA-01 channel-local rate assembly in an isolated lane.
- [ ] M3: combined paired runs and independently closed transfer/storage ledgers.
- [ ] M4: native gates, independent correctness/QA reviews and release-readiness documentation.

## Surprises & Discoveries


The predecessor audit passes OFE transfer conversions and selected PASS delivery
checks but fails channel rate-versus-volume agreement. Published channel outflow
is calculated from a balance identity, so a reported zero balance cannot validate
transport. Hourly WAT is daily output from an hourly seepage calculation. Current
ASCII QOFE has local-area normalization; earlier HBP aliases are not its contract.
Zero initial groundwater hides the terminal-area initialization defect.

Ten source/mode cases plus eight network/placement variants completed 44 years.
Observed candidate-off/on outputs must remain identical, but repaired outputs
are expected to change where a defect acts. Keep these different parity claims
separate. The prior audit identified, rather than repaired, four mechanisms;
additional storage/routing residuals may remain after their correction.

## Decision Log


2026-10-21 — Scaffold only on explicit operator request. Preserve the audit as
committed history. The repair baseline is native remote-default ASCII release
261021, not the dirty HBP development checkout. No implicit branch switching.

2026-10-21 — Use one behavioral change per lane, then a combined candidate.
Resolve scientific authority and write an ADR before promoting formulas or area
conversions. Do not prescribe unreviewed peak/duration or channel-sink behavior
by hiding a choice inside implementation.

2026-10-21 — Require independent transfer, rate and storage closure. A remaining
unexplained discrepancy blocks repaired-routing acceptance; four narrow fixes
are necessary but not assumed sufficient. Do not compensate through ET/Dp,
report-only balancing terms, wider tolerances or post-hoc outlet normalization.

## Outcomes & Retrospective


Scaffold complete; all implementation, review and repaired-model claims remain
pending. The concrete next milestone is portable defect reproduction and a
reviewed scientific contract. No native sources or vendored binaries changed.

## Context and Orientation


The coordination repository is `/workdir/wepppy` (also `/home/workdir/wepppy`).
Native default checkout is `/workdir/wepp-forest-release-20261009`; resolve
`origin/HEAD` again at execution rather than trusting a directory name. At the
audit, the branch was `wepp_260430_negmeltfix_comparator`, source commit
`a87925df9ffe6ebb928e126395dd159d484285fa`, artifact commit
`6a6621e4db9aff1cdf6fa9cd0cb02b00e82182eb`. The other checkout at
`/workdir/wepp-forest` contains unrelated HBP development work; leave it intact.

Frozen WEPPpy baseline binaries are `wepp_runner/bin/wepp_261021` and
`wepp_261021_hill`, with SHA256 respectively
`fe7a8d7b93deb2329536b9cc937b9f51a5c747b19fd3b95584347639046fa385` and
`6e4ec397551175ffd71337eeea04f5b3150a544f247382c863956fb50d7e59d1`.
They use ASCII PASS component schema 3. Read root and nearest native AGENTS,
`docs/ablation/protocol.md`, and the WEPPpy artifact/ADR standards before edits.

The committed predecessor is
`docs/work-packages/20261021_watershed_physical_water_audit/` at `e85d582ed`.
Its `artifacts/findings.md`, `source-map.md`, `commands.md`, case matrix and JSON
receipts retain the diagnosis. Large raw outputs and observer source copies
are under `/workdir/watershed-physical-water-audit-20261021`. These are available
supplementary evidence, not portable CI dependencies. The original Ayush decks
and executable were never supplied; historical attribution remains unavailable.

Native routines to inspect are `src/contin.for` (groundwater initialization and
Dp recharge), `src/watbal_hourly.for` (hourly infiltration distribution),
`src/chrqin.for` (source rates), `src/wshchr.for` (channel rates/volumes/storage),
`src/wshcqi.for` and `src/wshdrv.for` (incoming transfer/soil accounting), and
`src/wshpas.for`/`src/wshred.for` (serialized and loaded PASS). Existing tests
`tests/test_component_reconstruction.py` and `tests/test_channel_state.py`
provide real native harnesses. Preserve `docs/contracts/execution-calendar-contract.md`.

## Plan of Work


### M1 — Establish portable failures and ratify the repair contracts

Read the committed audit; record source status, diffs, compiler/flags, binary
hashes and all shared run inputs in `artifacts/baseline-provenance.json` here.
Create a native incident record under `docs/ablation/` using its existing protocol.
Use isolated source/build copies with explicit commits and patches for experiments;
apply accepted fixes to the default branch first. Do not switch shared branches.

Add bounded regressions to the native repository using real Fortran routines.
Retain portable inputs or deterministic generators under native test fixtures.
Start with the existing CHRQIN harness, then cover groundwater initialization,
hourly soil allocation and channel-local rates. A fresh checkout must reproduce
all four failures without `/wc1` donor directories. Create combined deterministic
wet/dry/snow climate and complete hillslope/channel decks, including run-shared
files and explicit daily/hourly selection. Keep the prior private cases optional.

Draft a parameterization ADR in WEPPpy using the next available identifier and
amend/create the native contract `docs/contracts/physical-water-routing-contract.md`.
Record why volume, timing support, storage and local normalization take their
chosen roles. Specify treatment when requested volume, peak and duration cannot
all be satisfied; compare alternatives explicitly. Specify positive/negative
channel-local exchange, available-water constraints, infiltration residual
allocation, and groundwater initialization/withdrawal timing. Preserve event
selection thresholds and existing public formats. A negative net transmission
term is not automatically an invalid loss: trace its physical source.

Obtain independent scientific/correctness and regression QA reviews of the
contracts and proposed cases. Future execution may delegate these review tasks;
reviewers must not substitute arithmetic identity for physical validity. Resolve
medium/high findings and retain `artifacts/contract-review.md`. M1 ends with
all four portable tests failing for the intended reasons on baseline, positive
controls passing, and an explicit contract/ADR checkpoint before model edits.

### M2 — Repair and measure each mechanism separately

Maintain `artifacts/lane-results.csv` with source hash, parent, intended change,
inputs, outputs, failures and decision. Begin each lane from the pinned baseline
or a recorded dependency, without contaminating it with other unmeasured fixes.
Changes are local corrections, not a general numerical rewrite.

For WPA-04, initialize groundwater from total hillslope area once at simulation
start, retaining the established daily recurrence’s withdrawal timing. With
10,000 m², 100 mm initial groundwater and 0.04/day baseflow coefficient, verify
40 m³ first-day baseflow for every layout when recharge is zero. Include zero
initial storage, nonzero deep seepage, varying area, subsequent years and multiple
hillslopes so no COMMON-state initialization leaks across boundaries. Preserve
per-OFE Dp volume accumulation and unaffected WAT payloads.

For WPA-03, account for every hourly infiltration remainder in an actual store
or flux, including signed inputs and finite available water. Do not simply
remove the loop cutoff without testing termination, layer boundaries and soil
constraints. Test below/at/above the old 0.00001 m threshold, one/multiple layers,
frozen/saturated/dry profiles and unequal OFEs. Native high-precision observations
must show input allocation closing; dropping a printed residual from a report is
not a repair. Confirm the unrelated daily path stays unchanged.

For WPA-02, implement the ratified flat-source discretization. The actual native
routine must deliver 900 m³ for the 900 s/600 s-step control and 1,000 m³ for the
incompatible-peak control under the explicit volume/support policy. Retain the
aligned 1,200 m³ positive control. Test durations shorter than a step, fractional
last steps, zero/tiny volumes, initial/continuing days, point/cell-average modes,
exponential sources and mixed/return-flow components. Check peaks, timing and
boundary continuity as well as total volume; no unauthorized support extension.

For WPA-01, represent channel-local net exchanges independently of the existence
of side hillslope surface runoff. Test absent side hills, zero-flow side hills,
positive and negative net exchange, lateral-only/baseflow-only inputs, side/top
placement, tributaries and cascades. Preserve the distinct support of each
source rather than scaling an unrelated hill hydrograph. Losses must respect
available water and cannot silently manufacture negative discharge or missing
storage. Compare integrated native rates to physical sources and sinks before
accepting the lane.

Each lane needs its failing test now passing, unchanged controls, source review,
full-period applicable replay and an explanation of changed outputs. Reject
no-effect changes. If implementing a guard or alternative process is necessary,
record the demonstrated failure of the simpler correction and its science contract.
Do not promote the combined candidate until the four lanes have individual evidence.

### M3 — Validate combined physical accounting

Build one combined candidate pair with the system compiler. Regenerate all
contributing hill outputs, PASS and watershed results together in new directories.
Execute the acceptance matrix in `artifacts/acceptance-matrix.md`: single,
50/50, 60/40, 40/60 and 20/30/50 OFEs in both water-balance modes; short and longer
channels; top/side placement; unequal tributaries; two-channel cascades; nonzero
groundwater controls; and calendar boundaries through year 400. Complete every
configured period for decisive conclusions. Review impacts on common contour,
variable-width, tile, impoundment and routing-algorithm paths; add bounded tests
where affected and retain explicit unsupported conditions.

Define `artifacts/ledger-schema.md` before extending parsers. Include actual
initial and final stores and their time convention, field units/area basis,
connectivity, source provenance and unknown-term representation. Observe each
OFE’s surface/lateral inputs and exports, local ET/Dp, interception/snow/frozen/
liquid stores, groundwater recharge/discharge, PASS selection omissions, channel
local exchanges and downstream storage/transfers. Dp is internal recharge in a
combined soil+groundwater budget; it is not an additional external loss there.

Reuse the predecessor independent readers and corruption controls after reviewing
them against current source. Retain full native rate arrays including time zero;
use the actual solver quadrature and report sensitivity to alternate integration.
State absolute/relative/rounding bounds before comparing results. Report signed,
absolute, maximum and cumulative residuals so cancellation is visible. Treat
missing days, duplicate transfers, nonfinite data and unobserved stores as failures
or unresolved evidence, never zero. Do not derive a missing flux from the same
balance being tested.

Candidate-off/on observations must preserve scientific outputs. Baseline/candidate
changes must be attributed to the individual lanes. Compare internal ledgers to
fresh published WAT/PASS/EBE/channel artifacts and existing downstream readback;
no report-only fix. Replay the available eighteen audit configurations in full
as supplementary evidence. Full routing acceptance remains blocked if the
independent rate/volume/storage discrepancy survives; locate the next failing
boundary and propose the smallest evidence-supported correction within scope,
or record the needed scope decision rather than declaring the incident resolved.

### M4 — Complete regression, review and handoff

Run required native tests, watchlist, smoke and artifact-policy gates using
committed resources. Run existing calendar, component, source/state and applicable
fuzzy regression cases; retain known failures and their exact dispositions.
Use `artifacts/correctness-review.md` following the repository template plus a
separate QA review. Review conservation, peak/timing behavior, storage, geometry,
compatibility and the completeness of generated evidence. Close all medium/high
findings. Passing tests do not prove field calibration; explicitly assess and
retain the daily/hourly partitioning differences as a scientific limit.

Update native README, the current scientific contract, an unreleased changelog
entry and user/operator regeneration guidance alongside accepted production code.
Update the ADR with actual decisions and evidence. Summarize supported cases,
changes, limits and rollback in `artifacts/repair-handoff.md`. The target completion
claim is locally validated source repair and release readiness, not deployment.
Dated release/vendoring requires its own authorized action and full native/WEPPpy
binary-lifecycle gates; never overwrite 261021 or silently switch defaults.

Only after acceptance and review pass, update this package/tracker and project
board, remove its active-plan pointer from root AGENTS, and archive this plan
using `wctl doc-mv --force`. If blocked by a real scientific or external dependency,
retain the active plan and precise evidence; do not mark completed to end a turn.

## Concrete Steps


At execution start inspect both repositories’ status and native default branch:

    git -C /workdir/wepppy status --short
    git -C /workdir/wepp-forest-release-20261009 status --short
    git -C /workdir/wepp-forest-release-20261009 symbolic-ref refs/remotes/origin/HEAD
    git -C /workdir/wepp-forest-release-20261009 rev-parse HEAD

From the native repository, inspect `tools/ablation_protocol.py --help` and use
its existing incident layout. Run current relevant tests as a baseline:

    /workdir/wepppy/.venv/bin/python -m pytest -q tests/test_component_reconstruction.py tests/test_channel_state.py tests/test_execution_calendar.py

Add exact new-test and replay commands to `artifacts/commands.md` as M1 fixes
the portable fixture design. Record expected baseline failure magnitudes and
candidate acceptance before editing source. Build isolated candidates sequentially
with `/usr/bin/gfortran`, `make -B wepp` and `make -B wepp_hill`, retaining logs,
include profiles and hashes. Do not use disabled `make all` or parallel profile
builds. Native pre-handoff commands include:

    /workdir/wepppy/.venv/bin/python -m pytest -q
    python tools/run_hillslope_watchlist.py --binary /absolute/candidate/wepp_hill
    tools/smoke_wepp_binary_host.sh /absolute/candidate/wepp
    tools/smoke_wepp_binary_host.sh /absolute/candidate/wepp_hill
    python tools/check_ablation_artifact_policy.py

Select candidate binary environment variables according to existing test helpers
so fixtures actually exercise the candidate, not a stale vendored executable.
No application code is presently planned; if WEPPpy behavior is changed, apply
its scoped tests and required substantive-change sanity gate. For documents:

    wctl doc-lint --path docs/work-packages/20261021_watershed_physical_water_repair
    tools/check_agents_size.sh AGENTS.md
    git diff --check

## Validation and Acceptance


Require all four actual failure boundaries to pass portable regressions, all
impacted combined control volumes to close within predeclared physically justified
bounds, and published/routed quantities to agree. Preserve calendar correctness,
event-selection semantics and unaffected source behavior. No missing remainder,
last-OFE initial storage scaling, or unrepresented channel/source volume may be
hidden by balancing output fields. The acceptance matrix defines required edge
cases; reviews and generated-output evidence are mandatory, not deferred promises.

## Idempotence and Recovery


Use numbered isolated attempts under `/workdir/watershed-physical-water-repair-20261021`.
Never overwrite prior cases or live outputs. Capture source patches per lane
and recover by discarding only that lane’s isolated tree; preserve unrelated dirty
files and branches. Keep large traces outside git with hashes. Maintain 261021
as the rollback comparator. Temporary observations stay opt-in and must not alter
scientific payloads; no silent fallback, clamp or guard may replace a real repair.

## Artifacts and Notes


The predecessor package is the immutable baseline; keep all new evidence here
and in the native incident record. Expected deliverables are baseline provenance,
portable repro references, ADR/contract review, lane results, complete ledgers,
corruption controls, correctness/QA reviews and the repair handoff. Current files
are a scaffold only; no execution receipts or review approvals are asserted.

## Interfaces and Dependencies


Use owned Fortran kernels, existing pytest/native harnesses, PASS readers and
Python analysis tools. Do not introduce a general aggregation framework or change
PASS/WAT public schemas. Existing consumer accounting remains the contract for
local ET/Dp and terminal exports. If a new source semantic is unavoidable, write
a compatibility and downstream artifact-regeneration plan before changing it.

## Revision Notes


2026-10-21 21:53 UTC — Initial scaffold on operator request, linked to audit commit
`e85d582ed`. Defines four repair lanes, independent physical acceptance and explicit
scaffold/release boundaries; execution has not started.
