# Watershed channel routing closure investigation

**Status**: Scaffolded; investigation not started
**Created**: 2026-10-21 16:42 UTC
**Owner**: Roger Lew; scientific context from Ayush Poudel

## Purpose

Determine whether hillslope water delivered through PASS is conserved through
watershed channels, and explain apparent closure errors for unequal-area
multiple overland flow elements (OFEs). Separate area conversion, event filtering,
groundwater accounting, channel storage/losses, and reporting discrepancies.
The deliverable is a reproducible diagnosis, not a corrected simulation.

## Authority and scope

The operator requested scaffolding on 2026-10-21 and explicitly allowed
wepp-forest observability instrumentation while prohibiting simulation changes.
This turn creates the plan only. Execution may add gated diagnostic observations,
offline accounting tools, fixtures, and evidence. It must not change equations,
thresholds, routing branches, numerical precision of simulation variables,
state updates, solver ordering, defaults, guards, or production output schemas.
No clamps, balancing corrections, replacement routing, or mutation lanes are
authorized. Confirmed defects become separately scoped remediation proposals.

Scope follows OFE transfers through terminal hillslope fluxes, PASS writer and
reader, channel/impoundment routing, groundwater and tile contributions, and
outlet summaries. ET and deep percolation are included where needed to define
the control volume (the physical domain whose inflows, outflows, and storage are
balanced). Neither binary release/vendoring nor deployment, live-run mutation,
historical regeneration, or consumer behavior changes are included.

## Execution and deliverables

Follow the [active ExecPlan](prompts/active/watershed_channel_routing_closure_execplan.md)
and maintain the [tracker](tracker.md). Retain source/provenance mapping,
instrumentation design and parity results, case matrix, volume ledgers,
signed/absolute residual summaries, diagnostic controls, and a findings report
with exact reproductions and remaining coverage limits in `artifacts/`.

## Complexity budget

Reuse `wepp_observe.on`, existing observation helpers, native PASS inspectors,
output comparators, build tools, and isolated replay directories. Permit bounded
diagnostic fields and offline scripts using existing dependencies. Start with
source tracing and existing diagnostics. If insufficient, document the missing
measurement before adding a probe. No services, queues, stores, dependencies,
privileges, public routes, or new deployment mechanisms are permitted.

## Acceptance and evidence gate

- Exact source revision, dirty patch, compiler/flags, binary hashes, complete
  input manifests, PASS family, calendars, and geometry identify every replay.
- Original baseline, instrumented-observation-off, and observation-on runs
  preserve scientific outputs. Diagnostic files are the only intended additions.
- Direct readback joins the actual hillslope writer, consumed PASS file,
  loaded watershed values, channel transfers, and outlet result by hill/element
  and time. File existence and successful termination alone are insufficient.
- Per-element and domain ledgers account for local inputs, boundary exports,
  groundwater, storage changes, and threshold omissions without double counting.
- Both signs of residual, accumulated drift, worst events, and missing/nonfinite
  records are assessed using tolerances justified before evaluating candidates.
- Diagnostic positive controls detect deliberately injected offline accounting
  mistakes; the simulator is never modified to create those mistakes.
- Controlled unequal-area cases and at least one representative real-project
  replay complete their configured periods. Shortened runs are exploratory.
- Findings distinguish supported closure, identified defect, reporting-only
  discrepancy, filtered delivery, invalid diagnostic, and unresolved evidence.
  A demonstrated defect may complete the investigation; it does not mean fixed.

Use supported project clone/archive workflows for real-project isolation and
retain shared runtime context. Generated artifact validation applies during
execution; this documentation-only scaffold generates no simulation evidence.
Large payloads remain in visible, retained replay directories with manifests
and hashes in the package. No new WEPPcloud artifact workflow is introduced.

## Review and policy gates

Security impact: **none** for the scoped offline investigation; no dedicated
security artifact is required. Re-triage if execution proposes an attack-surface
change. Parameterization changes: **none permitted**; no parameterization ADR is
needed for observation alone. Require a correctness review of diagnostic validity,
parity, control-volume definitions, and findings before closeout. Follow native
AGENTS review requirements if instrumentation edits `.f90` files.

The native ablation protocol supplies baseline and science-investigation
discipline, but its optional simulation mutation/promotion lanes are outside this
operator authorization. Do not use that protocol to expand scope.

## References

- [Physical water decision](../../adrs/ADR-0099-mofe-physical-water-consumers.md)
- [Hillslope accounting contract](../../schemas/hillslope-water-aggregation-contract.md)
- [Generated artifact validation](../../standards/generated-artifact-validation-standard.md)
- [Artifact observability](../../standards/artifact-observability-standard.md)
- Native repository: `/workdir/wepp-forest/AGENTS.md`,
  `docs/ablation/protocol.md`, `docs/contracts/pass-and-output-contracts.md`,
  `docs/contracts/watershed-hillslope-pass-reader-contract.md`.

## Risks and dependencies

Ayush's workbook `/tmp/Water_Balance_S_Shape_0.6_0.4_Corrected.xlsx` is a lead,
not executable provenance. Verify availability and retain its hash if used;
missing original decks limits claims about that exact example without blocking
independent controlled cases. Current `.hbp` and historical text PASS paths must
not be conflated. Contour/variable-width geometry and the previously reported
six-year replay failure remain coverage questions, not established routing defects.
