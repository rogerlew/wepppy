# Topanga CLIGEN seed anomaly recurrence

Status: Closed 2026-10-06. Scientific owner: WEPPpy. Operator: Roger Lew.

## Objective and authority

Execute the approved five-seed pilot followed, after validation, by 100 randomly
selected seeds. Estimate recurrence of paired Hill 106 peak-flow anomalies on
their original dates and throughout the 1980–2024 observed climate history.
The user authorized execution on 2026-10-06 after reviewing the design.

## Scope and complexity budget

Reuse frozen Topanga fixtures, CLIGEN observed mode, the pinned ea25ad79 observer,
existing isolated replay and census analysis tools, and existing openwepp compute
capacity. Forest supplies archives and compilation. New study scripts, manifests,
and outputs are permitted in isolated study directories. No runtime deployment,
model repair, queue topology, production project mutation, watershed routing,
or new dependency is included. Preserve all existing dirty work.

## Design

Start with the frozen 1980 Ksat20/Ksat35 pair and 1986 baseline/lower-ground-cover
pair; the dense-management lane is a secondary diagnostic, not a canopy-only
mutation. Separate these broad known-positive fixtures from ±1% Ksat/±0.01
cover census probes if those are subsequently evaluated. Use the identical
seeded climate in all members of each pair. Preserve observed daily inputs and
spatial corrections; inspect every generated field. Run complete histories.

Pilot seeds: 0, 1, 12345, 54321, 99999; repeat seed 12345 independently.
The inference sample is 100 seeds drawn without replacement with
Python random.Random(20261006), excluding pilot seeds. Publish this list before
execution. Original archived climate is a separate acceptance control.

Use the existing candidate screen and floors (runoff 1e-5 m, peak 1e-7 m/s,
surplus rate 1e-8 m/s). Preserve all flags, raw values, absent events, failed
runs, and evidence states. Report date-specific screened recurrence and
mechanism-specific recurrence separately, with Wilson 95% intervals, plus
any-event recurrence over the fixed history. Seeds, not dates, are sampling
units. Probabilities are conditional on this site, history, input pair, and
seed sampling design. Selected cases receive isolated replay and manual review.

## Validation and acceptance

Recover/rebuild observer and replay with recorded hashes and pass original
acceptance fixtures including active/inactive output parity and negative control.
Verify input hashes and climate date/daily-value invariants at the consumed
input. Repeated seed must reproduce. Pilot must finish and pass invariants before
100-seed execution. Reconcile every terminal and recompute summaries from raw
results. Publish scientific conclusions and limitations in WEPPpy.

## Impact, recovery, and security

Bounded background compute and additive retained study files only. No quorum or
storage availability changes. Stop on invariant failures, unintended writes,
repeated execution failure or capacity pressure; retain diagnostics and cancel
only study processes/jobs. No automatic deletion of archives or source runs.
Security: low; no new attack surface or privileges. Study subprocess invocations
use fixed validated paths/arguments, not arbitrary external requests. Review the
exact runner before execution. No default/formula changes; no ADR required.

## Dependencies and evidence

Forest evidence root:
/home/workdir/peakflow-topanga-census-evidence/b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de.
All 704 files per archived stratum and the three principal ledgers were hash
verified during planning. Source project hand-to-mouth-drought is read-only.
The old observer path hash changed; rebuild from pinned source before use.
The climate header says 100 years but actual dates cover 45 years (1980–2024).

## Deliverables

Active execution plan and tracker, immutable seed/input/build manifests,
acceptance and pilot reports, full event comparisons, manual mechanism review,
probabilities with uncertainty, and a public WEPPpy investigation README.

## Closure

Delivered the [scientific report](../../investigations/2026-10-06-topanga-cligen-seed-recurrence/README.md),
scripts, 100-seed probabilities, compact manual packets, validation reports and
internal storage hash index. Pilot and full sample completed; source-checked
replay matched all 20 reviewed lane cases. Quality-warning refinements and
historical replay failures are retained explicitly. No production behavior
changed; dedicated production correctness/security review is not applicable
to this isolated low-impact scientific execution. Follow-ups are targeted
bracketing and an actual-solver-operand observer/replay contract, not more
authorized execution in this closed package.
